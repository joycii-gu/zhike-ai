"""Prompt assembly for model-backed ZhiKe AI reports."""

from __future__ import annotations

import json
from typing import Any


SYSTEM_PROMPT = """你是知客 ZhiKe AI，一名面向业务员的 AI 业务处理智能体。
你的任务是理解客户、分析需求并生成审慎、可执行的下一步行动。

必须返回符合给定 JSON Schema 的对象，六个字段的值均使用中文 Markdown：
1. customer_profile：客户名称、行业、角色、当前需求、关注点、当前阶段、待确认信息；
2. need_analysis：明确区分事实、推断、未知；
3. opportunity_assessment：机会等级只能使用“🟢 高”“🟡 中”“🔴 低”，并列出有利信号、风险因素、判断依据；
4. follow_up_plan：包含下一步动作、时间建议、沟通目标；
5. communication_script：生成微信或电话沟通参考话术；
6. daily_report：联合当前客户与 Mock 今日客户，包含今日客户列表、优先级排序、待办事项、风险提醒、明日计划和数据范围说明。

约束：
- 不得虚构客户信息、预算、决策权限或成交概率；
- 缺失内容标注为“未知/待确认”；
- 推断内容明确标注为“推断”；
- 不能因为客户感兴趣就直接判断为高机会；
- 话术不得承诺未经验证的效果；
- 输出仅供业务员参考，最终发送和决策由人工确认；
- Mock 客户只用于 W2 演示，不代表数据库或真实历史记录。
"""


def build_user_prompt(customer_input: str, mock_customers: list[dict[str, Any]]) -> str:
    """Build the focused runtime context passed to a model provider."""
    mock_json = json.dumps(mock_customers, ensure_ascii=False, indent=2)
    return f"""请处理以下当前客户信息：

<customer_input>
{customer_input.strip()}
</customer_input>

以下是仅用于 W2 日报演示的内存 Mock 今日客户：

<mock_customers>
{mock_json}
</mock_customers>

JSON top level must directly contain exactly these six keys: customer_profile, need_analysis, opportunity_assessment, follow_up_plan, communication_script, daily_report.
Do not wrap them in report, data, or output, and do not add explanatory text outside JSON.

请严格遵守系统指令并返回结构化业务报告。"""


SKILL_SYSTEM_PROMPT = """你是知客 ZhiKe AI 的一个受约束业务 Skill。
你只能根据输入中的事实、已标注推断和未知项工作：不得编造预算、决策权限、成交概率、产品效果或客户历史。
缺失信息必须写为“未知/待确认”；推断必须显式写为“推断”。
返回严格 JSON，不要输出 Markdown 围栏、解释性文字或思考过程。"""


def _compact_json(value: Any, limit: int = 5200) -> str:
    """Keep chained context focused so later Skills do not receive long raw notes."""
    text = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return text if len(text) <= limit else text[:limit] + "…（已剪裁）"


def build_skill_prompt(
    skill_id: str,
    *,
    customer_input: str,
    context: dict[str, Any],
    mock_customers: list[dict[str, Any]],
) -> str:
    """Build a compact, step-specific prompt for the real chained workflow."""
    raw = customer_input.strip()
    if skill_id == "customer_info_parse":
        return f"""执行 Skill 1：客户信息解析。

原始客户记录：
{raw}

返回 JSON 对象，至少包含：
{{"facts":{{"customer_name":"","industry":"","role":"","needs":[],"concerns":[],"budget":"","time_plan":"","stage":""}},"inferences":[],"unknowns":[],"evidence":[]}}
所有事实尽量保留短证据；未出现的信息不要补写。"""

    focused_context = _compact_json(context)
    instructions = {
        "customer_profile": "执行 Skill 2：客户档案生成。将解析结果整理为便于业务员阅读的结构化客户档案。",
        "need_analysis": "执行 Skill 3：客户需求分析。必须区分显性需求（事实）、潜在痛点（推断）和待确认问题（未知）。",
        "opportunity_judgement": "执行 Skill 4：业务机会判断。审慎给出高/中高/中/低/暂不判断之一，同时给出有利信号、不确定因素、风险和依据。不得给出成交概率。",
        "follow_up": "执行 Skill 5：跟进建议。每条建议必须含动作、对象、时点和目标；不能跳过需求确认直接强推成交。",
        "communication": "执行 Skill 6：沟通话术。生成自然、简洁、可编辑的参考话术；不得承诺未经验证的效果或价格。",
        "daily_report": "执行 Skill 7：业务日报。仅联合当前客户与给定 Mock 客户，汇总优先级、待办、风险和明日计划，并声明数据范围。",
    }
    if skill_id not in instructions:
        raise ValueError(f"未知的 Workflow Skill：{skill_id}")

    mock_block = ""
    if skill_id == "daily_report":
        mock_block = f"\n\nW2 演示 Mock 客户（仅可用于日报）：\n{_compact_json(mock_customers, 2800)}"
    return f"""{instructions[skill_id]}

以下是上游 Skill 已确认的必要上下文（不是新的原始事实）：
{focused_context}{mock_block}

返回格式必须为：{{"output":"中文 Markdown 内容"}}。
output 中必须使用清晰标题、项目符号或表格；不要把 JSON、Python 字典或内部字段名直接展示给业务员。"""
