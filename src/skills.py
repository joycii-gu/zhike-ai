"""W2 Skills workflow adapter.

The Markdown files under ``zhike-ai/skills`` are the human-readable Skill
specifications submitted for S3W2.  This module provides a small local runner
that mirrors their input/output boundaries in Mock mode, so the Streamlit
Prototype can execute the same workflow without an external model or runtime.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


SKILL_ORDER = (
    "customer_info_parse",
    "customer_profile",
    "need_analysis",
    "opportunity_judgement",
    "follow_up",
    "communication",
    "daily_report",
)
SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"


def skill_files() -> dict[str, Path]:
    """Return the submitted Skill specification files in workflow order."""
    return {name: SKILLS_DIR / name / "SKILL.md" for name in SKILL_ORDER}


def load_skill_definition(name: str) -> str:
    """Load one human-readable Skill definition for inspection or future runtimes."""
    if name not in SKILL_ORDER:
        raise ValueError(f"未知 Skill：{name}")
    path = skill_files()[name]
    if not path.exists():
        raise FileNotFoundError(f"Skill 定义文件不存在：{path}")
    return path.read_text(encoding="utf-8")


def _contains(text: str, *keywords: str) -> bool:
    return any(keyword in text for keyword in keywords)


def _extract_name(text: str) -> str:
    patterns = (
        r"([\u4e00-\u9fff]{1,3}(?:总|经理|老师|校长|主任))",
        r"客户[：:]?\s*([\u4e00-\u9fff]{2,4})",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return "当前客户"


def parse_customer_info(customer_input: str) -> dict[str, Any]:
    """Skill 1: extract evidence-bound fields from free-form customer notes."""
    name = _extract_name(customer_input)
    if _contains(customer_input, "课程顾问", "学员", "职业技能培训"):
        industry = "【事实】职业教育/培训"
        role = "【未知】机构负责人或业务相关人员，具体决策权限待确认"
        need = "【事实】整理学员咨询、辅助判断意向并生成跟进话术"
        concerns = ["【事实】话术质量", "【事实】使用门槛", "【事实】新人顾问是否容易使用"]
        stage = "【推断】需求探索或演示评估阶段"
    elif _contains(customer_input, "财税", "工商", "政策咨询", "企业服务"):
        industry = "【事实】企业服务"
        role = "【未知】企业负责人或业务相关人员，具体决策流程待确认"
        need = "【事实】整理企业客户需求、提炼方案沟通重点并生成跟进计划"
        concerns = ["【事实】数据保密", "【事实】输出准确性", "【事实】员工使用成本"]
        stage = "【推断】内部了解或演示准备阶段"
    else:
        industry = "【事实】企业培训" if "培训" in customer_input else "【未知】行业待确认"
        role = "【未知】企业负责人或业务相关人员，决策权限待确认"
        need = "【事实】了解 AI 如何辅助销售团队进行客户跟进"
        concerns = ["【事实】部署难度", "【事实】价格", "【事实】实际效果", "【事实】业务员采用意愿"]
        stage = "【推断】初步了解或方案探索阶段"

    budget = "【未知】未明确预算范围"
    if re.search(r"预算.{0,8}\d", customer_input):
        budget = "【事实】输入中出现预算线索，需人工核对具体金额和口径"
    return {
        "客户称谓": f"【事实】{name}",
        "行业": industry,
        "角色": role,
        "需求": [need],
        "关注点": concerns,
        "预算信号": budget,
        "时间计划": "【事实】已提及下周/本周沟通" if "下周" in customer_input or "本周" in customer_input else "【未知】未明确",
        "当前阶段": stage,
        "证据摘录": [customer_input[:120]],
        "待确认字段": ["团队规模", "现用工具", "决策权限", "预算范围", "实施或试用范围"],
    }


def generate_customer_profile(parsed: dict[str, Any]) -> dict[str, Any]:
    """Skill 2: normalize the parsed fields into a customer profile."""
    return {
        "基本信息": {
            "称谓": parsed["客户称谓"],
            "行业": parsed["行业"],
            "角色": parsed["角色"],
        },
        "核心需求": parsed["需求"],
        "关注点": parsed["关注点"],
        "预算": parsed["预算信号"],
        "决策阶段": parsed["当前阶段"],
        "时间计划": parsed["时间计划"],
        "待确认事项": parsed["待确认字段"],
        "证据摘录": parsed["证据摘录"],
    }


def analyze_needs(profile: dict[str, Any]) -> dict[str, Any]:
    """Skill 3: separate explicit needs, inferences and unknowns."""
    return {
        "显性需求": profile["核心需求"],
        "潜在痛点": [
            "【推断】客户可能正在评估 AI 业务助理的适用性，尚无充分证据表明已进入采购阶段。",
            "【推断】当前团队可能存在信息整理或跟进一致性问题，需通过下一次沟通验证。",
        ],
        "决策因素": profile["关注点"],
        "成交阻碍": [
            "预算、决策权限和实施范围尚未完整确认。",
            "实际使用效果和团队采用情况仍需通过演示或试用验证。",
        ],
        "待确认问题": [
            "当前最耗时的客户处理环节是什么？",
            "希望先验证哪个具体业务场景？",
        ],
    }


def assess_opportunity(profile: dict[str, Any], needs: dict[str, Any]) -> dict[str, Any]:
    """Skill 4: make a conservative opportunity judgement."""
    return {
        "商机等级": "中",
        "判断依据": "存在与产品能力相关的需求和沟通意愿，但预算、决策权限、实施范围等关键信息不足，不直接判定为高机会。",
        "有利信号": ["客户提出了与产品能力相关的明确问题或关注点。", "具备继续沟通、演示或需求访谈的基础。"],
        "风险因素": ["预算、决策流程和实施范围尚未完整确认。", "团队实际采用和效果标准仍未知。"],
        "不确定事项": profile["待确认事项"],
    }


def generate_follow_up_plan(profile: dict[str, Any], needs: dict[str, Any], opportunity: dict[str, Any]) -> list[dict[str, str]]:
    """Skill 5: turn analysis into stage-appropriate executable actions."""
    name = profile["基本信息"]["称谓"].replace("【事实】", "")
    need = profile["核心需求"][0]
    return [
        {"动作": f"与{name}确认下一次沟通时间", "对象": name, "时点建议": "1 个工作日内", "沟通目标": "锁定演示或需求访谈安排", "准备材料": "简短流程介绍", "优先级": "高"},
        {"动作": f"准备与“{need}”相关的一页式示例", "对象": name, "时点建议": "会前 1 天", "沟通目标": "让客户理解核心闭环", "准备材料": "业务流程示例和输出样例", "优先级": "中"},
        {"动作": "询问团队规模、现用工具和主要耗时环节", "对象": name, "时点建议": "下次沟通前半段", "沟通目标": "验证真实业务痛点", "准备材料": "需求确认问题清单", "优先级": "高"},
        {"动作": "确认预算、决策参与者和试用范围", "对象": name, "时点建议": "需求明确后", "沟通目标": "判断是否进入小范围验证", "准备材料": "待确认事项清单", "优先级": "中"},
    ]


def generate_communication_script(profile: dict[str, Any], follow_up: list[dict[str, str]]) -> dict[str, str]:
    """Skill 6: generate a reference script without unsupported promises."""
    name = profile["基本信息"]["称谓"].replace("【事实】", "")
    concerns = "、".join(item.replace("【事实】", "") for item in profile["关注点"][:3])
    return {
        "渠道": "微信",
        "话术": f"{name}您好，您提到比较关注{concerns}。我们可以安排一次简短线上沟通，我会结合实际流程示例，演示从客户信息整理、需求分析到跟进建议和日报生成的过程，也想进一步了解您目前的工作方式和主要困难。您近期哪个时间段比较方便？（发送前请业务员核实并按需调整）",
    }


def _generate_scope_safe_daily_report(current: dict[str, Any], customers_in_scope: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a safe daily report when the account scope has fewer than two demos.

    W4 account and guest workspaces intentionally do not inherit W2 Mock
    customers.  The local fallback must therefore work with an empty customer
    scope instead of assuming two pre-seeded records exist.
    """
    current_name = current["profile"]["基本信息"]["称谓"].replace("【事实】", "")
    current_level = current["opportunity"]["商机等级"]
    current_action = "确认下一次沟通并补充待确认信息"
    if current.get("follow_up"):
        current_action = str(current["follow_up"][0].get("动作") or current_action)

    today_customers = [{
        "客户": current_name,
        "要点": (
            f"{current['profile']['基本信息']['行业']}，"
            f"{current['profile']['决策阶段']}，机会等级{current_level}。"
        ),
    }]
    todos = [{"客户": current_name, "待办": current_action}]
    risks = [{"客户": current_name, "风险": "预算、决策权限和实施范围仍需确认"}]

    seen_names = {current_name}
    for item in customers_in_scope:
        name = str(item.get("name") or item.get("客户") or "待确认客户")
        if name in seen_names:
            # The current analysis already represents this customer's newest
            # state.  Avoid showing the same customer twice after an update.
            continue
        seen_names.add(name)
        industry = str(item.get("industry") or item.get("行业") or "行业待确认")
        stage = str(item.get("stage") or item.get("当前阶段") or "当前阶段待确认")
        level = str(item.get("opportunity_level") or item.get("机会等级") or item.get("priority") or item.get("优先级") or "待判断")
        todo = str(item.get("todo") or item.get("待办") or "确认下一步沟通安排")
        risk = str(item.get("risk") or item.get("风险") or "关键信息待确认")
        today_customers.append({"客户": name, "要点": f"{industry}，{stage}，机会等级{level}。"})
        todos.append({"客户": name, "待办": todo})
        risks.append({"客户": name, "风险": risk})

    names = [item["客户"] for item in today_customers]
    if customers_in_scope:
        scope = (
            f"本日报汇总当前客户及当前工作空间内 {len(customers_in_scope)} 位客户。"
            "不引入 W2 演示 Mock 客户；数据仅归属当前账号或访客会话。"
        )
    else:
        scope = "本日报仅汇总当前客户的本次分析结果；未引入 W2 演示 Mock 客户，数据不会跨账号或跨访客会话混入。"

    return {
        "数据组成": names,
        "今日客户情况": today_customers,
        "优先级排序": names,
        "待办事项": todos,
        "风险提醒": risks,
        "明日计划": [f"推进{current_name}的下一次沟通并确认关键缺口。"],
        "数据范围说明": scope,
    }


def generate_daily_report(current: dict[str, Any], customers_in_scope: list[dict[str, Any]]) -> dict[str, Any]:
    """Skill 7: aggregate only the active account or visitor scope.

    W4 must never silently inject the old W2 demo customers.  The caller is
    responsible for providing the current account/visitor context explicitly.
    """
    return _generate_scope_safe_daily_report(current, customers_in_scope)


def _md_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _render_profile(profile: dict[str, Any]) -> str:
    rows = [
        ("客户称谓", profile["基本信息"]["称谓"]),
        ("所属行业", profile["基本信息"]["行业"]),
        ("客户角色", profile["基本信息"]["角色"]),
        ("当前需求", "；".join(profile["核心需求"])),
        ("关注点", "；".join(profile["关注点"])),
        ("预算", profile["预算"]),
        ("当前阶段", profile["决策阶段"]),
        ("待确认信息", "；".join(profile["待确认事项"])),
    ]
    return "| 字段 | 内容 |\n|---|---|\n" + "\n".join(f"| {key} | {value} |" for key, value in rows)


def _render_needs(needs: dict[str, Any]) -> str:
    return "**显性需求**\n" + _md_list(needs["显性需求"]) + "\n\n**潜在痛点**\n" + _md_list(needs["潜在痛点"]) + "\n\n**决策因素**\n" + _md_list(needs["决策因素"]) + "\n\n**成交阻碍**\n" + _md_list(needs["成交阻碍"]) + "\n\n**待确认问题**\n" + _md_list(needs["待确认问题"])


def _render_opportunity(opportunity: dict[str, Any]) -> str:
    return f"### 🟡 {opportunity['商机等级']}\n\n**有利信号**\n{_md_list(opportunity['有利信号'])}\n\n**风险因素**\n{_md_list(opportunity['风险因素'])}\n\n**判断依据**\n{opportunity['判断依据']}\n\n**不确定事项**\n{_md_list(opportunity['不确定事项'])}"


def _render_follow_up(plan: list[dict[str, str]]) -> str:
    blocks = []
    for idx, item in enumerate(plan, 1):
        blocks.append(f"{idx}. **动作：** {item['动作']}；**对象：** {item['对象']}；**时点：** {item['时点建议']}；**目标：** {item['沟通目标']}；**材料：** {item['准备材料']}；**优先级：** {item['优先级']}")
    return "\n".join(blocks)


def _render_daily(report: dict[str, Any]) -> str:
    customer_lines = "\n".join(f"{idx}. {item['客户']}：{item['要点']}" for idx, item in enumerate(report["今日客户情况"], 1))
    todo_lines = _md_list([f"{item['客户']}：{item['待办']}" for item in report["待办事项"]])
    risk_lines = _md_list([f"{item['客户']}：{item['风险']}" for item in report["风险提醒"]])
    return f"**数据组成**\n- " + "、".join(report["数据组成"]) + f"\n\n**今日客户列表与优先级**\n{customer_lines}\n\n**优先级排序**\n" + "、".join(report["优先级排序"]) + f"\n\n**待办事项**\n{todo_lines}\n\n**风险提醒**\n{risk_lines}\n\n**明日计划**\n{_md_list(report['明日计划'])}\n\n**数据范围说明**\n{report['数据范围说明']}"


def run_mock_skills_pipeline(customer_input: str, mock_customers: list[dict[str, Any]]) -> dict[str, str]:
    """Execute all submitted Skills in order and render the public report contract."""
    parsed = parse_customer_info(customer_input)
    profile = generate_customer_profile(parsed)
    needs = analyze_needs(profile)
    opportunity = assess_opportunity(profile, needs)
    follow_up = generate_follow_up_plan(profile, needs, opportunity)
    communication = generate_communication_script(profile, follow_up)
    daily = generate_daily_report(
        {"profile": profile, "needs": needs, "opportunity": opportunity, "follow_up": follow_up},
        mock_customers,
    )
    return {
        "customer_profile": _render_profile(profile),
        "need_analysis": _render_needs(needs),
        "opportunity_assessment": _render_opportunity(opportunity),
        "follow_up_plan": _render_follow_up(follow_up),
        "communication_script": f"> {communication['话术']}",
        "daily_report": _render_daily(daily),
    }
