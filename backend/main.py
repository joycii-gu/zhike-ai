"""FastAPI application for the ECS-deployed ZhiKe AI workspace."""

from __future__ import annotations

import re
import os
import secrets
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
    append_customer_capture,
    authenticate_user,
    confirm_action_draft,
    create_customer,
    create_action_draft,
    create_task,
    create_user,
    dashboard_snapshot,
    dismiss_action_draft,
    find_customer_by_name,
    get_customer,
    get_user,
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


class CapturePayload(BaseModel):
    """A minimum-input record of an action that has already happened."""

    capture: str = Field(min_length=2, max_length=4000)
    customer_id: str = Field(default="", max_length=64)
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


class ActionDraftPayload(BaseModel):
    draft_id: str


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


def _draft_title(report: dict[str, Any]) -> str:
    """Turn the agent's follow-up output into a short, editable confirmation item."""
    raw = str(report.get("follow_up_plan", ""))
    # Prefer an actual action field.  Markdown headings such as
    # "## 跟进建议清单" must never become the businessperson's task title.
    patterns = (
        r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:下一步)?动作(?:\*\*)?\s*[：:]\s*(.+)$",
        r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?建议(?:\*\*)?\s*[：:]\s*(.+)$",
        r"(?im)^\s*###?\s*(?:下一步)?动作\s*$\s*^\s*(?:[-*]\s*)?(.+)$",
    )
    candidate = ""
    for pattern in patterns:
        match = re.search(pattern, raw)
        if match and match.group(1).strip():
            candidate = match.group(1).strip()
            break
    if not candidate:
        for line in raw.splitlines():
            cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.、])\s*", "", line).strip()
            cleaned = re.sub(r"^#+\s*", "", cleaned).strip()
            if (
                len(cleaned) >= 6
                and not re.fullmatch(r"(?:跟进建议|跟进建议清单|下一步行动|行动建议|优先级)[:：]?", cleaned)
                and not cleaned.startswith(("优先级", "时间建议", "沟通目标", "准备材料"))
            ):
                candidate = cleaned
                break
    candidate = candidate or "确认本次客户的下一步跟进动作"
    # The action draft is a product UI field, not a Markdown document.  Model
    # formatting must never leak into the task title shown to a salesperson.
    candidate = re.sub(r"[*`#_]", "", candidate)
    candidate = re.sub(r"^\s*(?:动作|下一步动作|建议行动|行动建议|跟进建议(?:清单)?)\s*[：:]\s*", "", candidate)
    candidate = re.sub(r"^\s*(?:[-*•]|\d+[.、])\s*", "", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip(" -:：")
    return candidate[:120]


def _display_task_title(value: Any) -> str:
    """Return a readable, action-oriented label for both new and legacy tasks.

    Older W2/W3 records can have a Markdown section heading (for example
    ``# 跟进建议清单``) saved as their task title.  That is not an executable
    action, so the UI must not present it as one.  New tasks are normalized by
    ``_draft_title``; this function keeps historical rows honest at read time.
    """
    title = str(value or "")
    title = re.sub(r"[*`#_]", "", title)
    title = re.sub(r"^\s*(?:[-•]|\d+[.、])\s*", "", title)
    title = re.sub(r"\s+", " ", title).strip(" -:：")
    normalized = title.replace(" ", "")
    generic_headings = {
        "跟进建议清单",
        "跟进建议",
        "下一步行动",
        "行动建议",
        "建议行动",
    }
    if not title or normalized in generic_headings:
        return "查看客户分析并确认下一步行动"
    return title[:120]


def _daily_customer_context(user_id: str) -> list[dict[str, str]]:
    """Return only the signed-in user's existing customers for Skill 7."""
    return [
        {
            "客户": str(customer.get("name", "待确认客户")),
            "行业": str(customer.get("industry", "待确认")),
            "当前阶段": str(customer.get("stage", "待确认")),
            "优先级": str(customer.get("priority", "中")),
            "风险": str(customer.get("risk", "待确认")),
        }
        for customer in list_customers(user_id)
    ]


def _account_daily_report(user_id: str) -> str:
    """Build the daily view from the current account, never a saved demo prompt.

    A report generated during an earlier W2 demonstration may still contain
    Mock customer names in its stored JSON.  The W4 customer screen therefore
    derives the daily-report tab from the signed-in account at read time.  It
    keeps historical analysis modules intact while preventing old demo data
    from being presented as the user's current business information.
    """
    customers = _daily_customer_context(user_id)
    tasks = list_tasks(user_id, include_done=False)
    lines = [
        "# 业务日报",
        "数据范围说明：仅汇总当前账号内已保存的客户与待办；不包含 W2 演示 Mock 客户。",
        "## 今日客户情况",
    ]
    if customers:
        lines.extend([
            "| 客户 | 行业 | 当前阶段 | 优先级 | 风险 |",
            "| --- | --- | --- | --- | --- |",
        ])
        for customer in customers:
            lines.append(
                "| {客户} | {行业} | {当前阶段} | {优先级} | {风险} |".format(
                    **{key: str(value).replace("|", "／") for key, value in customer.items()}
                )
            )
    else:
        lines.append("当前账号暂未保存客户。完成一次分析后，客户会出现在此处。")

    lines.append("## 优先级排序")
    if customers:
        rank = {"高": 0, "中高": 1, "中": 2, "低": 3}
        for index, customer in enumerate(sorted(customers, key=lambda item: rank.get(item["优先级"], 9)), 1):
            lines.append(f"- {index}. {customer['客户']}：{customer['优先级']}优先级；{customer['当前阶段']}。")
    else:
        lines.append("- 暂无可排序客户。")

    lines.append("## 待办事项")
    if tasks:
        for task in tasks:
            lines.append(
                f"- {task['customer_name']}：{_display_task_title(task['title'])}"
                f"（状态：{task['status']}）"
            )
    else:
        lines.append("- 暂无已确认待办。AI 建议需由业务员确认后才会出现在这里。")
    return "\n".join(lines)


def _present_customer_for_account(customer: dict[str, Any], user_id: str) -> dict[str, Any]:
    """Attach account-scoped daily data before returning a customer to the UI."""
    report = customer.get("report")
    if isinstance(report, dict):
        customer["report"] = {**report, "daily_report": _account_daily_report(user_id)}
    return customer


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


@app.post("/api/auth/guest", status_code=status.HTTP_201_CREATED)
def create_guest_session(response: Response) -> dict[str, Any]:
    """Open a one-click, account-isolated visitor workspace without an AI call."""
    token = secrets.token_urlsafe(18).replace("-", "").replace("_", "").lower()
    user = create_user(
        f"guest-{token}@visitor.zhike.local",
        "访客演示",
        secrets.token_urlsafe(32),
    )
    _set_session(response, user["id"])
    return {"user": {**user, "is_guest": True}}


@app.post("/api/auth/logout", status_code=status.HTTP_200_OK)
def logout(response: Response) -> dict[str, bool]:
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user_id: str = Depends(_user_id)) -> dict[str, Any]:
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="当前会话已失效，请重新进入。")
    return {**user, "is_guest": user["email"].endswith("@visitor.zhike.local")}


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
    return _present_customer_for_account(data, user_id)


@app.post("/api/analysis", status_code=status.HTTP_201_CREATED)
def analyse(payload: AnalysisPayload, user_id: str = Depends(_user_id)) -> dict[str, Any]:
    if not payload.force_mock and not has_api_provider():
        raise HTTPException(
            status_code=503,
            detail="No model API is configured. Add SYNSCALE_API_KEY on the ECS server, then retry.",
        )
    try:
        result = business_agent_with_trace(
            payload.raw_note,
            force_mock=payload.force_mock,
            daily_customers=_daily_customer_context(user_id),
        )
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
    customer = get_customer(user_id, customer_id)
    return {"customer_id": customer_id, "report_id": report_id, "customer": _present_customer_for_account(customer, user_id), "runtime": provider}


@app.post("/api/captures", status_code=status.HTTP_201_CREATED)
def capture_business_update(payload: CapturePayload, user_id: str = Depends(_user_id)) -> dict[str, Any]:
    """Convert one post-conversation update into a reviewable next action.

    This endpoint deliberately does not create a task.  The resulting action
    remains a draft until the businessperson confirms it in the UI.
    """
    if not payload.force_mock and not has_api_provider():
        raise HTTPException(status_code=503, detail="当前没有可用的模型 API，请稍后重试。")

    existing: dict[str, Any] | None = None
    if payload.customer_id:
        existing = get_customer(user_id, payload.customer_id)
        if not existing:
            raise HTTPException(status_code=404, detail="未找到该客户。")
    elif payload.customer_name.strip():
        existing = find_customer_by_name(user_id, payload.customer_name)

    # An existing customer's past record is used as limited context.  The new
    # capture is visibly separated so the Agent can distinguish new facts.
    historical_note = str(existing.get("raw_note", "")) if existing else ""
    analysis_input = (
        f"历史客户记录：\n{historical_note[-8000:]}\n\n本次业务进展（优先依据）：\n{payload.capture.strip()}"
        if historical_note
        else payload.capture.strip()
    )
    try:
        result = business_agent_with_trace(
            analysis_input,
            force_mock=payload.force_mock,
            daily_customers=_daily_customer_context(user_id),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=f"模型服务暂时不可用，请重试。{exc}") from exc

    known_name = str(existing.get("name", "")) if existing else payload.customer_name
    metadata = _metadata(analysis_input, known_name)
    if existing:
        customer_id = str(existing["id"])
        append_customer_capture(user_id, customer_id, payload.capture, metadata)
    else:
        customer_id = create_customer(user_id, metadata["name"], payload.capture, metadata)

    provider = runtime_mode(force_mock=payload.force_mock)
    report_id = save_report(user_id, customer_id, result["report"], result["trace"], provider)
    draft = create_action_draft(
        user_id,
        customer_id,
        _draft_title(result["report"]),
        reason="基于本次业务进展与客户上下文生成；请在执行前人工确认。",
        risk=metadata["risk"],
    )
    return {
        "customer_id": customer_id,
        "report_id": report_id,
        "customer": _present_customer_for_account(get_customer(user_id, customer_id), user_id),
        "action_draft": draft,
        "runtime": provider,
    }


@app.post("/api/action-drafts/confirm")
def confirm_action(payload: ActionDraftPayload, user_id: str = Depends(_user_id)) -> dict[str, str]:
    try:
        return confirm_action_draft(user_id, payload.draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/action-drafts/dismiss")
def dismiss_action(payload: ActionDraftPayload, user_id: str = Depends(_user_id)) -> dict[str, bool]:
    try:
        dismiss_action_draft(user_id, payload.draft_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@app.get("/api/tasks")
def tasks(include_done: bool = False, user_id: str = Depends(_user_id)) -> list[dict[str, Any]]:
    # Normalize legacy records at the API boundary as well.  This is a
    # presentation-only migration: it never overwrites a user's stored task.
    return [
        {**task, "title": _display_task_title(task.get("title"))}
        for task in list_tasks(user_id, include_done=include_done)
    ]


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
    dismiss_action_draft,
    find_customer_by_name,
