"""Streamlit entry point for the ZhiKe AI W2 prototype."""

from __future__ import annotations

import os
import json
import ast
import re

import streamlit as st

from src.agent import business_agent, has_api_provider, runtime_mode


EXAMPLES = {
    "案例 1 · 企业培训客户": "李总，做企业培训，最近想了解 AI 员工如何帮助销售团队做客户跟进。之前看过我们的 HermesAgent 安装服务，对 AI 业务助理感兴趣，但还没有明确预算，希望下周约一次线上沟通。他比较关心部署难度、价格、实际效果，以及业务员是否真的会用。",
    "案例 2 · 课程顾问客户": "周校长经营一家职业技能培训机构，想了解 AI 能否帮助课程顾问整理学员微信咨询、判断报名意向并生成后续沟通话术。机构目前有 6 名课程顾问，新人较多，担心 AI 话术太生硬，也担心顾问不会使用。预算暂时没有确定，希望本周五先看一次线上演示，再决定是否安排小范围试用。",
    "案例 3 · 企业服务客户": "赵总负责一家为小微企业提供工商、财税和政策咨询服务的公司。团队有 4 名业务员，客户需求经常散落在电话纪要和个人备注里。赵总希望 AI 帮助整理企业客户需求、提炼方案沟通重点并生成跟进计划。目前处于内部了解阶段，关注数据保密、输出准确性和员工使用成本。",
}


st.set_page_config(
    page_title="知客 ZhiKe AI",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    .stApp {background: linear-gradient(180deg, #f7fbff 0%, #ffffff 38%);}
    .block-container {max-width: 1180px; padding-top: 2.4rem; padding-bottom: 4rem;}
    .hero {padding: 2.2rem 2.4rem; border-radius: 22px; background: linear-gradient(135deg, #12365a, #1f6b8f); color: white; box-shadow: 0 16px 38px rgba(18,54,90,.18); margin-bottom: 1.5rem;}
    .hero h1 {font-size: 2.45rem; margin: 0 0 .35rem 0; color: white;}
    .hero p {font-size: 1.08rem; opacity: .92; margin: .25rem 0;}
    .flow {font-size: .92rem !important; opacity: .78 !important; margin-top: 1rem !important;}
    .scope {padding: .8rem 1rem; border-left: 4px solid #3b82a0; background: #eef7fb; border-radius: 8px; margin: .5rem 0 1rem; color: #27465a;}
    .status-row {display:flex; gap:.65rem; flex-wrap:wrap; margin:-.6rem 0 1.4rem;}
    .status-pill {padding:.35rem .75rem; border-radius:999px; font-size:.82rem; font-weight:650; border:1px solid #d9e6ee; background:#fff; color:#365267;}
    .status-pill.online {background:#ecfdf5; border-color:#a7f3d0; color:#047857;}
    .status-pill.prototype {background:#eff6ff; border-color:#bfdbfe; color:#1d4ed8;}
    .step-strip {display:flex; gap:.45rem; align-items:center; flex-wrap:wrap; margin:0 0 1.25rem;}
    .step {padding:.42rem .7rem; border-radius:10px; background:#f3f6f8; color:#6b7d89; font-size:.8rem; border:1px solid #e4ebef;}
    .step-arrow {color:#9aabb5; font-size:.85rem;}
    .result-head {display:flex; justify-content:space-between; align-items:center; padding:.85rem 1rem; margin:.8rem 0 1rem; border-radius:12px; background:#f4f9fc; border:1px solid #dcecf3; color:#23465d;}
    .result-head strong {font-size:1.05rem;}
    .footer-note {padding:.9rem 1rem; border-radius:12px; background:#f8fafc; border:1px solid #e5e7eb; color:#64748b; font-size:.82rem;}
    div[data-testid="stTabs"] button {font-weight: 650;}
    div[data-testid="stTabs"] button[aria-selected="true"] {color:#0f6d8f; border-bottom-color:#0f8ca8;}
    div[data-testid="stMarkdownContainer"] table {width: 100%;}
</style>
""",
    unsafe_allow_html=True,
)

if "customer_input" not in st.session_state:
    st.session_state.customer_input = EXAMPLES["案例 1 · 企业培训客户"]
if "report" not in st.session_state:
    st.session_state.report = None


def select_example(example_text: str) -> None:
    """Update the input before Streamlit instantiates widgets on the rerun."""
    st.session_state.customer_input = example_text
    st.session_state.report = None


def render_report_content(content: str) -> None:
    """Render structured model output as readable sections instead of raw JSON."""
    original_content = content
    try:
        parsed = json.loads(original_content)
    except (TypeError, json.JSONDecodeError):
        parsed = extract_embedded_json(original_content)
        if parsed is None:
            content = prettify_inline_records(original_content)
            fields = parse_inline_fields(content)
            if fields:
                rows = []
                for key, value in fields:
                    rows.append(f"| {key} | {value.replace('|', '／')} |")
                st.markdown("| 字段 | 内容 |\n|---|---|\n" + "\n".join(rows))
            else:
                st.markdown(content)
            return

    if isinstance(parsed, dict):
        rows = []
        for key, value in parsed.items():
            if isinstance(value, list):
                display = "<br>".join(f"• {str(item)}" for item in value)
            elif isinstance(value, dict):
                display = "<pre>" + json.dumps(value, ensure_ascii=False, indent=2) + "</pre>"
            else:
                display = str(value)
            display = display.replace("|", "\\|")
            rows.append(f"| {key} | {display} |")
        st.markdown("| 字段 | 内容 |\n|---|---|\n" + "\n".join(rows), unsafe_allow_html=True)
    elif isinstance(parsed, list):
        st.markdown("\n".join(f"- {item}" for item in parsed))
    else:
        st.markdown(str(parsed))


def parse_inline_fields(content: str) -> list[tuple[str, str]]:
    """Parse model text such as '客户名称：…；行业：…' into table rows."""
    labels = (
        "客户名称", "客户称谓", "行业", "所属行业", "角色", "客户角色",
        "当前需求", "核心需求", "关注点", "主要关注点", "预算", "当前阶段",
        "时间计划", "待确认信息", "待确认事项",
    )
    label_pattern = "|".join(re.escape(label) for label in labels)
    matches = list(re.finditer(rf"({label_pattern})\s*[：:]\s*", content))
    if len(matches) < 2:
        return []
    rows: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
        value = content[start:end].strip(" ；;\\n")
        if value:
            rows.append((match.group(1), value))
    return rows


def extract_embedded_json(content: str) -> dict | list | None:
    """Extract a JSON object embedded in a Markdown table or explanatory text."""
    decoder = json.JSONDecoder()
    for index, character in enumerate(content):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(content[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, (dict, list)):
            return parsed
    return None


def prettify_inline_records(content: str) -> str:
    """Turn Python-style list/dict records in Markdown into compact readable text."""
    pattern = re.compile(r"\[(?:\s*\{.*?\}\s*,?)+\]", re.DOTALL)

    def replace_list(match: re.Match[str]) -> str:
        try:
            records = ast.literal_eval(match.group(0))
        except (ValueError, SyntaxError):
            return match.group(0)
        if not isinstance(records, list) or not all(isinstance(item, dict) for item in records):
            return match.group(0)
        rendered = []
        for item in records:
            preferred = [
                ("客户名称", "客户"), ("行业", "行业"), ("优先级", "优先级"),
                ("当前阶段", "阶段"), ("待办事项", "待办"), ("风险提醒", "风险"),
            ]
            parts = []
            used = set()
            for source, label in preferred:
                if source in item:
                    value = item[source]
                    if isinstance(value, list):
                        value = "、".join(str(v) for v in value)
                    parts.append(f"{label}：{value}")
                    used.add(source)
            for key, value in item.items():
                if key not in used and value not in (None, "", [], {}):
                    parts.append(f"{key}：{value}")
            rendered.append("；".join(parts))
        return "<br>".join(f"• {line}" for line in rendered)

    return pattern.sub(replace_list, content)

st.markdown(
    """
<section class="hero">
  <h1>知客 ZhiKe AI</h1>
  <p><strong>面向业务员的 AI 业务处理智能体</strong></p>
  <p>输入客户信息，生成结构化档案、需求分析、机会判断、跟进建议、沟通话术与业务日报。</p>
  <p class="flow">客户信息输入 → 客户档案 → 需求分析 → 机会判断 → 跟进建议 → 沟通话术 → 业务日报</p>
</section>
""",
    unsafe_allow_html=True,
)

api_ready = has_api_provider()
st.markdown(
    f"""
<div class="status-row">
  <span class="status-pill prototype">W2 Prototype</span>
  <span class="status-pill {'online' if api_ready else ''}">{'● MiniMax-M2.7 API 已配置' if api_ready else '● Mock Skills Workflow'}</span>
  <span class="status-pill">无数据库 · 不保存客户数据</span>
</div>
<div class="step-strip">
  <span class="step">① 信息输入</span><span class="step-arrow">→</span>
  <span class="step">② 客户档案</span><span class="step-arrow">→</span>
  <span class="step">③ 需求分析</span><span class="step-arrow">→</span>
  <span class="step">④ 机会判断</span><span class="step-arrow">→</span>
  <span class="step">⑤ 跟进建议</span><span class="step-arrow">→</span>
  <span class="step">⑥ 沟通话术</span><span class="step-arrow">→</span>
  <span class="step">⑦ 业务日报</span>
</div>
""",
    unsafe_allow_html=True,
)

left, right = st.columns([1.75, 1], gap="large")

with left:
    input_type = st.selectbox(
        "输入类型（用于提示模型处理重点）",
        ["微信聊天记录", "电话纪要", "会议记录", "业务员手动备注"],
    )
    st.subheader("客户信息输入")
    customer_input = st.text_area(
        "粘贴客户备注、聊天摘要、电话纪要或会议记录",
        key="customer_input",
        height=210,
        placeholder="例如：李总，做企业培训，最近想了解 AI 员工如何帮助销售团队做客户跟进……",
    )
    st.caption(f"当前输入 {len(customer_input.strip())} 个字符 · 无需预先整理，直接粘贴原始纪要即可")
    st.caption("无需先整理格式；知客会自动提取客户信息、需求和待确认事项。")
    optional_name = st.text_input("客户称谓（可选）", placeholder="例如：李总")
    optional_channel = st.selectbox(
        "沟通渠道（可选）", ["未指定", "微信", "电话", "会议"]
    )
    optional_follow_up = st.text_input(
        "计划跟进时间（可选）", placeholder="例如：下周三上午"
    )
    st.info("信息不完整也可以生成；缺失内容会标记为‘未知/待确认’，无需先补齐。")

with right:
    st.subheader("示例案例")
    st.caption("点击后自动填充输入框，可继续编辑。")
    for label, text in EXAMPLES.items():
        st.button(
            label,
            use_container_width=True,
            on_click=select_example,
            args=(text,),
        )
    st.markdown(
        '<div class="scope"><strong>W2 范围</strong><br>Mock 客户仅用于跨客户日报演示；无数据库、登录、CRM 或微信接入。</div>',
        unsafe_allow_html=True,
    )
    force_mock = st.toggle(
        "强制使用 Mock 演示模式",
        value=not api_ready,
    )
    st.caption(f"当前运行模式：{runtime_mode(force_mock=force_mock)}")

generate = st.button("生成业务报告", type="primary", use_container_width=True)

if generate:
    try:
        context_lines = [f"输入类型：{input_type}"]
        if optional_name.strip():
            context_lines.append(f"业务员补充的客户称谓：{optional_name.strip()}")
        if optional_channel != "未指定":
            context_lines.append(f"业务员补充的沟通渠道：{optional_channel}")
        if optional_follow_up.strip():
            context_lines.append(f"业务员补充的计划跟进时间：{optional_follow_up.strip()}")
        enriched_input = "\n".join(context_lines) + "\n\n原始客户记录：\n" + customer_input
        with st.spinner("知客正在整理客户信息并生成业务报告……"):
            st.session_state.report = business_agent(enriched_input, force_mock=force_mock)
    except Exception as exc:
        st.session_state.report = None
        st.error(f"生成失败：{exc}")

report = st.session_state.report
if report:
    st.markdown(
        """
<div class="result-head">
  <strong>业务处理报告</strong>
  <span>✓ 已完成 7 个 Skills · 已纳入 2 个 Mock 今日客户</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.success("业务报告已生成。请在发送话术或作出业务决策前进行人工确认。")
    tabs = st.tabs(
        ["👤 客户档案", "🔎 客户需求分析", "📈 业务机会判断", "✅ 跟进建议", "💬 沟通话术", "🗓️ 业务日报"]
    )
    keys = (
        "customer_profile",
        "need_analysis",
        "opportunity_assessment",
        "follow_up_plan",
        "communication_script",
        "daily_report",
    )
    for tab, key in zip(tabs, keys):
        with tab:
            render_report_content(report[key])

st.divider()
st.markdown(
    '<div class="footer-note">W2 Prototype · 输出仅供业务辅助参考 · 不保存客户数据 · 最终发送与业务决策由人工确认</div>',
    unsafe_allow_html=True,
)
