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
6. daily_report：仅汇总当前客户及输入中给定的同账号客户摘要，包含今日客户列表、优先级排序、待办事项、风险提醒、明日计划和数据范围说明。

约束：
- 不得虚构客户信息、预算、决策权限或成交概率；
- 缺失内容标注为“未知/待确认”；
- 推断内容明确标注为“推断”；
- 不能因为客户感兴趣就直接判断为高机会；
- 话术不得承诺未经验证的效果；
- 输出仅供业务员参考，最终发送和决策由人工确认；
- 只有明确进入 Mock 演示模式时才可以使用演示客户；正式账号日报不得混入演示客户。
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


def _compact_skill_definition(definition: str, limit: int = 1800) -> str:
    """Keep the public Skill contract available without burying the model in docs.

    The complete ``SKILL.md`` remains the submitted and runtime-loaded source
    of truth. A Skill call receives only its task-defining excerpt: this keeps
    the public contract traceable while reducing truncation and invalid-JSON
    failures caused by passing many thousands of documentation characters.
    """
    normalized = definition.strip()
    return normalized if len(normalized) <= limit else normalized[:limit] + "\n\n[Skill definition truncated]"


def build_skill_prompt(
    skill_id: str,
    *,
    customer_input: str,
    context: dict[str, Any],
    mock_customers: list[dict[str, Any]],
    skill_definition: str,
) -> str:
    """Build a compact, step-specific prompt for the real chained workflow."""
    raw = customer_input.strip()
    public_skill_contract = _compact_skill_definition(skill_definition)
    if skill_id == "customer_info_parse":
        raw = (
            f"{raw}\n\n"
            "The following is the public Skill Definition loaded by the current runtime. "
            "It defines the input, output and fact boundary for this step:\n"
            "<public_skill_definition>\n"
            f"{public_skill_contract}\n"
            "</public_skill_definition>"
        )
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
        "daily_report": "执行 Skill 7：业务日报。仅联合当前客户与给定的同账号客户摘要，汇总优先级、待办、风险和明日计划，并声明数据范围。不得编造或混入其他客户。",
    }
    if skill_id not in instructions:
        raise ValueError(f"未知的 Workflow Skill：{skill_id}")

    mock_block = ""
    if skill_id == "daily_report":
        mock_block = (
            "\n\n当前账号可用于日报汇总的客户摘要（只可使用下列名称；当前客户的上游结果优先）：\n"
            f"{_compact_json(mock_customers, 2800)}\n"
            "若该数组为空，则日报只能写当前客户，不能补写任何未在上下文出现的客户。"
        )
    # Keep one stable JSON envelope across every Skill.  Previously the
    # public follow_up definition requested a bare array while the runtime
    # requested {"output": "..."}, which made model replies ambiguous.
    if skill_id == "follow_up":
        output_contract = '''{"output":[{"动作":"","对象":"","时点建议":"","沟通目标":"","准备材料":"","优先级":"高/中/低"}]}'''
        output_note = "output 必须是 2–4 条跟进建议组成的 JSON 数组；每条必须包含动作、对象、时点建议、沟通目标、准备材料和优先级。"
    else:
        output_contract = '''{"output":"中文 Markdown 内容"}'''
        output_note = "output 中必须使用清晰标题、项目符号或表格。"
    return f"""{instructions[skill_id]}

以下是该步骤在仓库中公开提交、且由当前 Runtime 实际加载的 Skill Definition。它定义本步骤的输入、输出、事实边界与合格标准；如与通用说明冲突，以此定义为准：
<public_skill_definition>
{public_skill_contract}
</public_skill_definition>

以下是上游 Skill 已确认的必要上下文（不是新的原始事实）：
{focused_context}{mock_block}

返回格式必须为：{output_contract}。{output_note}
不要把 JSON、Python 字典或内部字段名直接展示给业务员。"""
