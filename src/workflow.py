"""Real chained Skills workflow for the W3 ZhiKe Agent.

The LLM is used for customer understanding and language generation.  Workflow
state, field validation, fallback behaviour and execution traces are managed
locally so that a malformed model response cannot break the whole report.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any, TypedDict

from .prompt import SKILL_SYSTEM_PROMPT, build_skill_prompt
from .schema import BusinessReport, validate_report
from .skills import load_skill_definition, parse_customer_info, run_mock_skills_pipeline


class SkillTraceEntry(TypedDict):
    skill_id: str
    name: str
    status: str
    runtime: str
    detail: str


class AgentRunResult(TypedDict):
    report: BusinessReport
    trace: list[SkillTraceEntry]


SkillCaller = Callable[[str, str], dict[str, Any]]

SKILL_STEPS: tuple[tuple[str, str, str | None], ...] = (
    ("customer_info_parse", "客户信息解析 / Customer Parsing", None),
    ("customer_profile", "客户档案生成 / Customer Profile", "customer_profile"),
    ("need_analysis", "客户需求分析 / Need Analysis", "need_analysis"),
    ("opportunity_judgement", "业务机会判断 / Opportunity Assessment", "opportunity_assessment"),
    ("follow_up", "跟进建议生成 / Follow-up Plan", "follow_up_plan"),
    ("communication", "沟通话术生成 / Communication Script", "communication_script"),
    ("daily_report", "业务日报生成 / Daily Business Report", "daily_report"),
)


def _fallback_trace(skill_id: str, name: str, detail: str) -> SkillTraceEntry:
    return {
        "skill_id": skill_id,
        "name": name,
        "status": "fallback",
        "runtime": "Local fallback",
        "detail": detail,
    }


def _api_trace(skill_id: str, name: str) -> SkillTraceEntry:
    return {
        "skill_id": skill_id,
        "name": name,
        "status": "api",
        "runtime": "MiniMax API",
        "detail": "已完成结构化输出与上下文传递",
    }


def _extract_output(payload: dict[str, Any]) -> str:
    """Convert common JSON response shapes into reviewer-friendly Markdown.

    Some OpenAI-compatible models return ``{"output": "..."}``, while
    others return a directly structured object such as ``{"跟进时间": ...}``.
    Both are valid model answers for a Skill; only rejecting the latter causes
    unnecessary local fallbacks and hides successful API calls.
    """

    def format_value(value: Any, depth: int = 0) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            lines: list[str] = []
            for item in value:
                rendered = format_value(item, depth + 1)
                if rendered:
                    lines.append(f"- {rendered}")
            return "\n".join(lines)
        if isinstance(value, dict):
            lines = []
            for key, nested in value.items():
                rendered = format_value(nested, depth + 1)
                if not rendered:
                    continue
                if isinstance(nested, (dict, list)):
                    heading = "###" if depth == 0 else "####"
                    lines.append(f"{heading} {key}\n{rendered}")
                else:
                    lines.append(f"- **{key}**：{rendered}")
            return "\n".join(lines)
        return ""

    for key in ("output", "result", "content", "markdown", "data", "response", "answer"):
        if key not in payload:
            continue
        rendered = format_value(payload[key])
        if rendered:
            return rendered

    rendered = format_value(payload)
    if rendered:
        return rendered
    raise ValueError("Skill 返回内容为空")


def _normalize_parsed_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Unwrap a JSON object returned inside a common parse-step wrapper."""
    for key in ("data", "result", "output", "response"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                return parsed
    return payload


def _context_for_step(
    skill_id: str,
    parsed: dict[str, Any],
    outputs: dict[str, str],
) -> dict[str, Any]:
    """Pass only evidence and relevant upstream results to later Skills."""
    if skill_id == "customer_profile":
        return {"parsed_customer": parsed}
    if skill_id == "need_analysis":
        return {"parsed_customer": parsed, "customer_profile": outputs.get("customer_profile", "")}
    if skill_id == "opportunity_judgement":
        return {
            "customer_profile": outputs.get("customer_profile", ""),
            "need_analysis": outputs.get("need_analysis", ""),
        }
    if skill_id == "follow_up":
        return {
            "customer_profile": outputs.get("customer_profile", ""),
            "need_analysis": outputs.get("need_analysis", ""),
            "opportunity_assessment": outputs.get("opportunity_assessment", ""),
        }
    if skill_id == "communication":
        return {
            "customer_profile": outputs.get("customer_profile", ""),
            "follow_up_plan": outputs.get("follow_up_plan", ""),
        }
    if skill_id == "daily_report":
        return {
            "customer_profile": outputs.get("customer_profile", ""),
            "opportunity_assessment": outputs.get("opportunity_assessment", ""),
            "follow_up_plan": outputs.get("follow_up_plan", ""),
        }
    return {}


def run_chained_workflow(
    call_json: SkillCaller,
    customer_input: str,
    mock_customers: list[dict[str, Any]],
    *,
    runtime_label: str = "MiniMax API",
    allow_local_fallback: bool = False,
) -> AgentRunResult:
    """Run all seven Skills in order.

    A deployed API run fails transparently by default.  Local fallback remains
    available only when an offline or controlled demo explicitly requests it.
    """
    local_report = run_mock_skills_pipeline(customer_input, mock_customers) if allow_local_fallback else None
    parsed = parse_customer_info(customer_input)
    outputs: dict[str, str] = {}
    trace: list[SkillTraceEntry] = []

    for skill_id, name, report_field in SKILL_STEPS:
        try:
            context = _context_for_step(skill_id, parsed, outputs)
            prompt = build_skill_prompt(
                skill_id,
                customer_input=customer_input,
                context=context,
                mock_customers=mock_customers,
                skill_definition=load_skill_definition(skill_id),
            )

            # Model output can occasionally be truncated or fail JSON parsing.
            # Retry the isolated Skill once before using deterministic local
            # fallback; never rerun already successful upstream Skills.
            last_error: Exception | None = None
            completed_after_retry = False
            for attempt in range(2):
                try:
                    payload = call_json(SKILL_SYSTEM_PROMPT, prompt)
                    if skill_id == "customer_info_parse":
                        if not isinstance(payload, dict) or not payload:
                            raise ValueError("客户信息解析结果为空")
                        parsed = _normalize_parsed_payload(payload)
                    else:
                        if report_field is None:
                            raise RuntimeError("Workflow 定义错误：缺少报告字段")
                        outputs[report_field] = _extract_output(payload)
                    completed_after_retry = attempt == 1
                    last_error = None
                    break
                except Exception as exc:
                    last_error = exc

            if last_error is not None:
                raise last_error
            entry = _api_trace(skill_id, name)
            entry["runtime"] = runtime_label
            if completed_after_retry:
                entry["detail"] = "首次输出未通过校验，重试后已完成结构化输出"
            trace.append(entry)
        except Exception as exc:
            if not allow_local_fallback:
                raise RuntimeError(
                    f"{skill_id} API call failed; no local fallback was generated: {type(exc).__name__}"
                ) from exc
            if skill_id == "customer_info_parse":
                parsed = parse_customer_info(customer_input)
            elif report_field:
                assert local_report is not None
                outputs[report_field] = local_report[report_field]
            trace.append(_fallback_trace(skill_id, name, f"API 输出异常，已使用本地安全回退：{type(exc).__name__}"))

    if local_report is None:
        report = validate_report(outputs)
    else:
        report = validate_report({field: outputs.get(field, local_report[field]) for field in local_report})
    return {"report": report, "trace": trace}


def run_local_workflow(customer_input: str, mock_customers: list[dict[str, Any]]) -> AgentRunResult:
    """Run the submitted local Skills pipeline and expose the same trace contract."""
    report = validate_report(run_mock_skills_pipeline(customer_input, mock_customers))
    trace = [
        {
            "skill_id": skill_id,
            "name": name,
            "status": "local",
            "runtime": "Mock Skills Workflow",
            "detail": "本地 Skills 流程已完成",
        }
        for skill_id, name, _ in SKILL_STEPS
    ]
    return {"report": report, "trace": trace}
