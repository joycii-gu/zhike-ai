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

请严格遵守系统指令并返回结构化业务报告。"""
