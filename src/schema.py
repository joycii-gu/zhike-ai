"""Unified report schema for the W2 prototype."""

from __future__ import annotations

from typing import Any, TypedDict


REPORT_FIELDS = (
    "customer_profile",
    "need_analysis",
    "opportunity_assessment",
    "follow_up_plan",
    "communication_script",
    "daily_report",
)


class BusinessReport(TypedDict):
    customer_profile: str
    need_analysis: str
    opportunity_assessment: str
    follow_up_plan: str
    communication_script: str
    daily_report: str


REPORT_JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {field: {"type": "string"} for field in REPORT_FIELDS},
    "required": list(REPORT_FIELDS),
    "additionalProperties": False,
}


def validate_report(data: Any) -> BusinessReport:
    """Validate and normalize provider output into the public report contract."""
    if not isinstance(data, dict):
        raise ValueError("业务报告必须是 JSON 对象。")

    missing = [field for field in REPORT_FIELDS if field not in data]
    if missing:
        raise ValueError(f"业务报告缺少字段：{', '.join(missing)}")

    report: BusinessReport = {
        field: str(data[field]).strip() for field in REPORT_FIELDS  # type: ignore[misc]
    }
    if any(not report[field] for field in REPORT_FIELDS):
        raise ValueError("业务报告包含空模块。")
    return report
