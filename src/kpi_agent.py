"""Deterministic KPI state and action planning for the W3 ZhiKe Agent.

This module deliberately does not call an LLM.  It turns explicit business
goals and user-confirmed follow-up events into traceable KPI progress, so the
demo never treats an AI inference as an achieved business result.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from hashlib import sha1
from math import ceil
import re
from typing import Any


DEFAULT_GOAL = {
    "period": "本周",
    "period_total_workdays": 5,
    "remaining_workdays": 5,
    "new_qualified_customers_target": 3,
    "effective_communications_target": 5,
    "solution_meetings_target": 2,
    "priority_customers_to_advance_target": 2,
}

EVENT_LABELS = {
    "effective_communication": "已完成一次有效沟通",
    "need_confirmed": "已确认客户关键需求",
    "solution_meeting": "已完成方案沟通/演示",
    "priority_advanced": "重点客户已推进到下一阶段",
    "awaiting_reply": "客户暂未回复",
    "material_requested": "客户要求补充材料",
    "on_hold": "客户暂缓或拒绝",
}


def default_session_state() -> dict[str, Any]:
    """Return a new in-memory W3 state. It is never persisted to a database."""
    return {
        "business_goal": deepcopy(DEFAULT_GOAL),
        "customers": [],
        "follow_up_feedback": [],
        "source_scope": "仅当前浏览器会话内的 W3 演示数据；刷新页面或服务重启后不保证保留。",
    }


def normalize_goal(raw: dict[str, Any] | None) -> dict[str, Any]:
    goal = deepcopy(DEFAULT_GOAL)
    if raw:
        goal.update({key: value for key, value in raw.items() if value is not None})
    for key in (
        "period_total_workdays",
        "remaining_workdays",
        "new_qualified_customers_target",
        "effective_communications_target",
        "solution_meetings_target",
        "priority_customers_to_advance_target",
    ):
        try:
            goal[key] = max(0, int(goal[key]))
        except (TypeError, ValueError):
            goal[key] = DEFAULT_GOAL[key]
    goal["period_total_workdays"] = max(1, goal["period_total_workdays"])
    goal["remaining_workdays"] = min(goal["remaining_workdays"], goal["period_total_workdays"])
    return goal


def _first_match(pattern: str, text: str, fallback: str) -> str:
    match = re.search(pattern, text)
    return match.group(1).strip() if match else fallback


def _infer_name(text: str, fallback: str = "当前客户") -> str:
    match = re.search(r"([\u4e00-\u9fff]{1,4}(?:总|经理|老师|校长|先生|女士))", text)
    return match.group(1) if match else fallback


def _infer_industry(text: str) -> str:
    mapping = (
        ("企业培训", "企业培训"),
        ("职业技能培训", "职业技能培训"),
        ("职业教育", "职业教育"),
        ("企业软件", "企业软件"),
        ("财税", "企业服务"),
        ("工商", "企业服务"),
        ("保险", "保险"),
        ("房产", "房产"),
    )
    for keyword, industry in mapping:
        if keyword in text:
            return industry
    return "待确认"


def _infer_stage(text: str) -> str:
    if any(word in text for word in ("演示", "线上沟通", "约一次")):
        return "沟通/演示准备"
    if any(word in text for word in ("比较", "方案", "报价")):
        return "方案评估"
    if "试用" in text:
        return "试用评估"
    return "需求探索"


def _infer_priority(text: str) -> str:
    if any(word in text for word in ("本周", "下周", "演示", "沟通", "试用")):
        return "高"
    if any(word in text for word in ("感兴趣", "了解", "咨询")):
        return "中"
    return "待确认"


def _initial_risk(text: str) -> str:
    risks = []
    if "预算" in text and any(word in text for word in ("没有", "未", "暂时")):
        risks.append("预算尚未明确")
    if "数据" in text or "保密" in text:
        risks.append("需确认数据处理与权限边界")
    if not risks:
        risks.append("尚需通过后续沟通确认需求与决策条件")
    return "；".join(risks)


def _next_action(stage: str) -> str:
    mapping = {
        "沟通/演示准备": "确认沟通档期，并准备围绕客户关注点的演示材料",
        "方案评估": "补充方案对比材料，并确认决策流程与关键顾虑",
        "试用评估": "确认试用范围、成功标准与下一次复盘时间",
        "需求探索": "发送需求确认问题清单，并约定下一次沟通",
    }
    return mapping.get(stage, "补充需求确认信息后安排下一步沟通")


def ingest_customer(
    state: dict[str, Any],
    customer_input: str,
    customer_name: str = "",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add or update a current customer without claiming any KPI achievement."""
    text = customer_input.strip()
    name = customer_name.strip() or _infer_name(text)
    customer_id = sha1(f"{name}|{text}".encode("utf-8")).hexdigest()[:12]
    record = {
        "id": customer_id,
        "name": name,
        "industry": _infer_industry(text),
        "stage": _infer_stage(text),
        "priority": _infer_priority(text),
        "suggested_next_action": _next_action(_infer_stage(text)),
        "risk": _initial_risk(text),
        "qualified": False,
        "effective_communications": 0,
        "solution_meetings": 0,
        "priority_advanced": False,
        "latest_status": "已生成客户处理报告，等待业务员确认跟进反馈",
        "feedback_count": 0,
    }
    customers = state.setdefault("customers", [])
    existing = next((item for item in customers if item.get("id") == customer_id), None)
    if existing:
        # Preserve confirmed process outcomes; only refresh source-derived context.
        for key in ("name", "industry", "stage", "priority", "suggested_next_action", "risk"):
            existing[key] = record[key]
        return state, existing
    customers.append(record)
    return state, record


def record_feedback(
    state: dict[str, Any], customer_id: str, event: str, note: str = ""
) -> tuple[dict[str, Any], str]:
    """Record one user-confirmed event. KPI counts only change in this function."""
    if event not in EVENT_LABELS:
        raise ValueError("未知的跟进反馈类型")
    customer = next((item for item in state.get("customers", []) if item.get("id") == customer_id), None)
    if not customer:
        raise ValueError("未找到当前客户，请先生成业务报告")

    if event == "effective_communication":
        customer["effective_communications"] = int(customer.get("effective_communications", 0)) + 1
    elif event == "need_confirmed":
        customer["qualified"] = True
        customer["stage"] = "需求已确认"
    elif event == "solution_meeting":
        customer["solution_meetings"] = int(customer.get("solution_meetings", 0)) + 1
        customer["stage"] = "方案沟通已完成"
    elif event == "priority_advanced":
        customer["priority_advanced"] = True
        customer["stage"] = "已推进至下一阶段"
    elif event == "awaiting_reply":
        customer["latest_status"] = "等待客户回复"
    elif event == "material_requested":
        customer["latest_status"] = "待补充客户要求的材料"
    elif event == "on_hold":
        customer["latest_status"] = "客户暂缓/拒绝，需降低跟进优先级"
        customer["priority"] = "低"

    customer["feedback_count"] = int(customer.get("feedback_count", 0)) + 1
    if event not in ("awaiting_reply", "material_requested", "on_hold"):
        customer["latest_status"] = EVENT_LABELS[event]
    state.setdefault("follow_up_feedback", []).append(
        {
            "customer_id": customer_id,
            "customer_name": customer["name"],
            "event": event,
            "event_label": EVENT_LABELS[event],
            "note": note.strip() or "未补充说明",
            "recorded_on": date.today().isoformat(),
        }
    )
    return state, customer["name"]


def _metric(
    name: str, actual: int, target: int, total_workdays: int, remaining_workdays: int
) -> dict[str, Any]:
    if target <= 0:
        return {
            "name": name,
            "actual": actual,
            "target": target,
            "progress": None,
            "status": "未设置目标",
            "expected_by_today": None,
            "remaining_gap": 0,
            "daily_required": None,
        }
    progress = round(actual / target * 100)
    elapsed_workdays = max(0, total_workdays - remaining_workdays)
    expected_by_today = round(target * elapsed_workdays / total_workdays, 1)
    remaining_gap = max(0, target - actual)
    daily_required = round(remaining_gap / remaining_workdays, 1) if remaining_workdays > 0 else None
    if progress >= 100:
        status = "已达成"
    elif elapsed_workdays == 0:
        status = "待启动"
    elif actual + 0.01 < expected_by_today:
        status = "节奏滞后"
    else:
        status = "节奏正常"
    return {
        "name": name,
        "actual": actual,
        "target": target,
        "progress": progress,
        "status": status,
        "expected_by_today": expected_by_today,
        "remaining_gap": remaining_gap,
        "daily_required": daily_required,
    }


def build_kpi_dashboard(state: dict[str, Any]) -> dict[str, Any]:
    """Build a deterministic, auditable KPI snapshot and action queue."""
    goal = normalize_goal(state.get("business_goal"))
    customers = list(state.get("customers", []))
    metrics = [
        _metric("新增合格客户", sum(1 for item in customers if item.get("qualified")), goal["new_qualified_customers_target"], goal["period_total_workdays"], goal["remaining_workdays"]),
        _metric("有效沟通", sum(int(item.get("effective_communications", 0)) for item in customers), goal["effective_communications_target"], goal["period_total_workdays"], goal["remaining_workdays"]),
        _metric("方案沟通/演示", sum(int(item.get("solution_meetings", 0)) for item in customers), goal["solution_meetings_target"], goal["period_total_workdays"], goal["remaining_workdays"]),
        _metric("重点客户推进", sum(1 for item in customers if item.get("priority_advanced")), goal["priority_customers_to_advance_target"], goal["period_total_workdays"], goal["remaining_workdays"]),
    ]

    priority_order = {"高": 0, "中": 1, "待确认": 2, "低": 3}
    action_queue = sorted(
        customers,
        key=lambda item: (priority_order.get(str(item.get("priority")), 4), -int(item.get("feedback_count", 0))),
    )
    actions = [
        {
            "客户": item["name"],
            "优先级": item["priority"],
            "当前阶段": item["stage"],
            "下一步": item["suggested_next_action"],
            "风险/状态": item["risk"] if item.get("latest_status", "").startswith("已生成") else item["latest_status"],
        }
        for item in action_queue
    ]
    warnings = []
    if goal["remaining_workdays"] <= 0:
        warnings.append("剩余工作日未设置或为 0，无法判断节奏风险。")
    for metric in metrics:
        if metric["status"] == "节奏滞后":
            warnings.append(
                f"{metric['name']}当前为 {metric['actual']}/{metric['target']}，"
                f"按当前节奏应完成约 {metric['expected_by_today']}；后续日均需完成 {metric['daily_required']}。"
            )
    if not customers:
        warnings.append("尚未生成客户报告，暂无可用于会话内 KPI 统计的客户。")

    return {
        "goal": goal,
        "metrics": metrics,
        "actions": actions,
        "warnings": warnings,
        "customer_count": len(customers),
        "feedback_count": len(state.get("follow_up_feedback", [])),
        "recent_feedback": list(reversed(state.get("follow_up_feedback", [])))[:5],
        "source_scope": state.get("source_scope", "仅当前会话数据"),
    }
