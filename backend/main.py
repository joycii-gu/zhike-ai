"""FastAPI application for the ECS-deployed ZhiKe AI workspace."""

from __future__ import annotations

import re
import os
from contextlib import asynccontextmanager
from typing import Any, Literal

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.security import (
    COOKIE_NAME,
    MAX_AGE_SECONDS,
    create_session_token,
    is_production,
    session_secret_configured,
    verify_session_token,
)
from src.agent import business_agent_with_trace, has_api_provider, runtime_mode
from src.storage import (
    authenticate_user,
    create_customer,
    create_task,
    create_user,
    dashboard_snapshot,
    get_customer,
    initialize_database,
    list_customers,
    list_tasks,
    record_feedback_event,
    revert_feedback_event,
    save_report,
    update_task_status,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if is_production() and not session_secret_configured():
        raise RuntimeError("生产环境必须配置 ZHIKE_SESSION_SECRET")
    initialize_database()
    yield


app = FastAPI(title="ZhiKe AI API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RegisterPayload(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    display_name: str = Field(min_length=2, max_length=40)
    password: str = Field(min_length=8, max_length=128)


class LoginPayload(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class AnalysisPayload(BaseModel):
    raw_note: str = Field(min_length=8, max_length=20000)
    customer_name: str = Field(default="", max_length=80)
    force_mock: bool = False


class TaskPayload(BaseModel):
    customer_id: str
    title: str = Field(min_length=1, max_length=300)
    due_at: str = Field(default="", max_length=50)


class TaskStatusPayload(BaseModel):
    status: Literal["待办", "已完成", "已延期", "已取消"]


class FeedbackPayload(BaseModel):
    customer_id: str
    event_type: Literal["need_confirmed", "effective_communication", "solution_meeting", "priority_advanced"]
    note: str = Field(default="", max_length=500)


def _validate_email(email: str) -> str:
    normalized = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", normalized):
        raise HTTPException(status_code=422, detail="请输入有效邮箱")
    return normalized


def _user_id(zhike_session: str | None = Cookie(default=None)) -> str:
    user_id = verify_session_token(zhike_session)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录后继续")
    return user_id


def _metadata(text: str, name: str) -> dict[str, str]:
    """Deterministic metadata only for lists; the Agent report remains authoritative."""
    inferred_name = name.strip()
    if not inferred_name:
        match = re.search(r"([\u4e00-\u9fff]{1,3}(?:总|老师|经理|校长|主任|先生|女士))", text)
        inferred_name = match.group(1) if match else "待确认客户"
    industry = next((label for key, label in (("培训", "企业培训"), ("教育", "职业教育"), ("软件", "企业软件"), ("财税", "企业服务"), ("房产", "房产服务")) if key in text), "待确认")
    stage = "需求确认"
    if any(key in text for key in ("演示", "沟通", "会议")):
        stage = "沟通/演示准备"
    if any(key in text for key in ("方案", "对比", "报价")):
        stage = "方案评估"
    priority = "高" if any(key in text for key in ("本周", "下周", "尽快", "演示", "报价")) else "中"
    risk = "预算待确认" if "预算" in text and any(key in text for key in ("不明确", "未知", "未定", "没有")) else "待确认"
    return {"name": inferred_name, "industry": industry, "stage": stage, "priority": priority, "risk": risk}


def _set_session(response: Response, user_id: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=create_session_token(user_id),
        max_age=MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        # HTTPS is required for ECS production. A short-lived HTTP smoke test
        # must opt in explicitly with ZHIKE_COOKIE_SECURE=false.
        secure=os.getenv("ZHIKE_COOKIE_SECURE", "true").lower() not in {"0", "false", "no"},
        path="/",
    )


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "runtime": runtime_mode(), "api_configured": has_api_provider()}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterPayload, response: Response) -> dict[str, Any]:
    try:
        user = create_user(_validate_email(payload.email), payload.display_name, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _set_session(response, user["id"])
    return {"user": user}


@app.post("/api/auth/login")
def login(payload: LoginPayload, response: Response) -> dict[str, Any]:
    user = authenticate_user(_validate_email(payload.email), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    _set_session(response, user["id"])
    return {"user": user}


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@app.get("/api/auth/me")
def me(user_id: str = Depends(_user_id)) -> dict[str, str]:
    return {"id": user_id}


@app.get("/api/dashboard")
def dashboard(user_id: str = Depends(_user_id)) -> dict[str, Any]:
    return {**dashboard_snapshot(user_id), "runtime": runtime_mode(), "api_configured": has_api_provider()}


@app.get("/api/customers")
def customers(user_id: str = Depends(_user_id)) -> list[dict[str, Any]]:
    return list_customers(user_id)


@app.get("/api/customers/{customer_id}")
def customer(customer_id: str, user_id: str = Depends(_user_id)) -> dict[str, Any]:
    data = get_customer(user_id, customer_id)
    if not data:
        raise HTTPException(status_code=404, detail="未找到该客户")
    return data


@app.post("/api/analysis", status_code=status.HTTP_201_CREATED)
def analyse(payload: AnalysisPayload, user_id: str = Depends(_user_id)) -> dict[str, Any]:
    if not payload.force_mock and not has_api_provider():
        raise HTTPException(
            status_code=503,
            detail="No model API is configured. Add SYNSCALE_API_KEY on the ECS server, then retry.",
        )
    try:
        result = business_agent_with_trace(payload.raw_note, force_mock=payload.force_mock)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Model service is temporarily unavailable. Please retry. {str(exc)}",
        ) from exc
    metadata = _metadata(payload.raw_note, payload.customer_name)
    customer_id = create_customer(user_id, metadata["name"], payload.raw_note, metadata)
    provider = runtime_mode(force_mock=payload.force_mock)
    report_id = save_report(user_id, customer_id, result["report"], result["trace"], provider)
    return {"customer_id": customer_id, "report_id": report_id, "customer": get_customer(user_id, customer_id), "runtime": provider}


@app.get("/api/tasks")
def tasks(include_done: bool = False, user_id: str = Depends(_user_id)) -> list[dict[str, Any]]:
    return list_tasks(user_id, include_done=include_done)


@app.post("/api/tasks", status_code=status.HTTP_201_CREATED)
def add_task(payload: TaskPayload, user_id: str = Depends(_user_id)) -> dict[str, str]:
    if not get_customer(user_id, payload.customer_id):
        raise HTTPException(status_code=404, detail="客户不存在")
    try:
        task_id = create_task(user_id, payload.customer_id, payload.title, payload.due_at, "人工创建")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"id": task_id}


@app.patch("/api/tasks/{task_id}")
def change_task(task_id: str, payload: TaskStatusPayload, user_id: str = Depends(_user_id)) -> dict[str, bool]:
    try:
        update_task_status(user_id, task_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/feedback", status_code=status.HTTP_201_CREATED)
def feedback(payload: FeedbackPayload, user_id: str = Depends(_user_id)) -> dict[str, str]:
    if not get_customer(user_id, payload.customer_id):
        raise HTTPException(status_code=404, detail="客户不存在")
    return {"id": record_feedback_event(user_id, payload.customer_id, payload.event_type, payload.note)}


@app.post("/api/feedback/{event_id}/revert")
def undo_feedback(event_id: str, user_id: str = Depends(_user_id)) -> dict[str, bool]:
    try:
        revert_feedback_event(user_id, event_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}
