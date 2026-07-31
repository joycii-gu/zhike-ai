"""Streamlit entry point for the ZhiKe AI W2 prototype."""

from __future__ import annotations

import os
import json
import ast
import re

import streamlit as st

from src.agent import business_agent_with_trace, has_api_provider, runtime_mode
from src.kpi_agent import (
    EVENT_LABELS,
    build_kpi_dashboard,
    default_session_state,
    ingest_customer,
    normalize_goal,
    record_feedback,
)


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
    .hero {position:relative; overflow:hidden; padding:1.65rem 2rem; border-radius:24px; background:linear-gradient(120deg,#0d2d4b 0%,#164d72 52%,#167b94 100%); color:#fff; box-shadow:0 18px 42px rgba(18,54,90,.18); margin-bottom:1.25rem;}
    .hero::before {content:""; position:absolute; inset:0; opacity:.15; background-image:radial-gradient(rgba(255,255,255,.8) 1px,transparent 1px); background-size:18px 18px; mask-image:linear-gradient(90deg,transparent 0%,black 50%,transparent 100%);}
    .hero-grid {position:relative; display:grid; grid-template-columns:minmax(0,1.55fr) minmax(250px,.8fr); gap:2rem; align-items:center;}
    .hero-eyebrow {display:inline-flex; align-items:center; gap:.38rem; padding:.3rem .62rem; border:1px solid rgba(203,237,246,.42); background:rgba(255,255,255,.10); border-radius:999px; color:#d9f6fb; font-size:.73rem; letter-spacing:.08em; font-weight:700;}
    .hero h1 {font-size:2.28rem; letter-spacing:-.035em; margin:.7rem 0 .32rem; color:#fff;}
    .hero-kicker {font-size:1.13rem; font-weight:650; opacity:.96; margin:0 0 .45rem;}
    .hero-desc {max-width:680px; font-size:.92rem; line-height:1.65; color:rgba(237,249,252,.83); margin:0;}
    .hero-flow {display:flex; flex-wrap:wrap; gap:.42rem; align-items:center; margin-top:1rem;}
    .hero-node {padding:.34rem .55rem; border:1px solid rgba(220,245,250,.26); border-radius:8px; font-size:.76rem; font-weight:600; color:#e7fbff; background:rgba(7,26,46,.18);}
    .hero-arrow {color:#aeeaf2; opacity:.8; font-size:.78rem;}
    .agent-panel {padding:1rem; border:1px solid rgba(216,245,250,.26); border-radius:16px; background:linear-gradient(145deg,rgba(255,255,255,.16),rgba(255,255,255,.06)); box-shadow:inset 0 1px 0 rgba(255,255,255,.12); backdrop-filter:blur(8px);}
    .agent-panel-top {display:flex; align-items:center; gap:.42rem; font-size:.73rem; color:#c7f3f7; letter-spacing:.06em; font-weight:700; margin-bottom:.8rem;}
    .live-dot {width:7px; height:7px; border-radius:50%; background:#75e6b6; box-shadow:0 0 0 4px rgba(117,230,182,.14);}
    .agent-status {display:grid; gap:.52rem;}
    .agent-status-item {display:flex; justify-content:space-between; gap:.7rem; align-items:center; padding:.52rem .6rem; border-radius:10px; background:rgba(5,25,43,.22); font-size:.79rem; color:#dff8fb;}
    .agent-status-item strong {font-size:.78rem; color:#fff; white-space:nowrap;}
    .agent-panel-foot {margin:.72rem 0 0; font-size:.72rem; line-height:1.45; color:rgba(224,248,251,.72);}
    @media (max-width: 760px) {.hero{padding:1.4rem 1.2rem}.hero-grid{grid-template-columns:1fr;gap:1.15rem}.hero h1{font-size:2rem}.agent-panel{padding:.85rem}.hero-desc{font-size:.87rem}.goal-console{padding:.9rem;flex-direction:column;gap:.55rem}}
    .scope {padding: .8rem 1rem; border-left: 4px solid #3b82a0; background: #eef7fb; border-radius: 8px; margin: .5rem 0 1rem; color: #27465a;}
    .goal-console {display:flex; justify-content:space-between; align-items:flex-start; gap:1rem; padding:1rem 1.15rem .82rem; margin:.2rem 0 0; border:1px solid #d7e9f1; border-top:4px solid #2d89a7; border-radius:16px 16px 0 0; background:linear-gradient(105deg,#f5fbfe 0%,#fbfdfe 68%);}
    .goal-console h3 {font-size:1rem; color:#163c56; margin:0 0 .23rem;}
    .goal-console p {font-size:.82rem; color:#5d7483; margin:0;}
    .goal-badge {flex:0 0 auto; padding:.3rem .6rem; border:1px solid #cce4ee; border-radius:999px; background:#fff; color:#2b718b; font-size:.75rem; font-weight:650;}
    div[data-testid="stForm"] {margin-top:0; padding:.8rem 1.15rem 1rem; border:1px solid #d7e9f1; border-top:0; border-radius:0 0 16px 16px; background:#fff;}
    .status-row {display:flex; gap:.65rem; flex-wrap:wrap; margin:-.6rem 0 1.4rem;}
    .status-pill {padding:.35rem .75rem; border-radius:999px; font-size:.82rem; font-weight:650; border:1px solid #d9e6ee; background:#fff; color:#365267;}
    .status-pill.online {background:#ecfdf5; border-color:#a7f3d0; color:#047857;}
    .status-pill.prototype {background:#eff6ff; border-color:#bfdbfe; color:#1d4ed8;}
    .step-strip {display:flex; gap:.45rem; align-items:center; flex-wrap:wrap; margin:0 0 1.25rem;}
    .step {padding:.42rem .7rem; border-radius:10px; background:#f3f6f8; color:#6b7d89; font-size:.8rem; border:1px solid #e4ebef;}
    .step-arrow {color:#9aabb5; font-size:.85rem;}
    .result-head {display:flex; justify-content:space-between; align-items:center; padding:.85rem 1rem; margin:.8rem 0 1rem; border-radius:12px; background:#f4f9fc; border:1px solid #dcecf3; color:#23465d;}
    .result-head strong {font-size:1.05rem;}
    .trace-title {display:flex; justify-content:space-between; align-items:center; gap:1rem; margin:1rem 0 .55rem;}
    .trace-title h4 {margin:0; color:#23465d; font-size:.96rem;}
    .trace-title span {font-size:.75rem; color:#6b7d89;}
    .trace-grid {display:grid; grid-template-columns:repeat(7,minmax(96px,1fr)); gap:.45rem; margin-bottom:1rem; overflow-x:auto;}
    .trace-item {min-width:96px; padding:.62rem .58rem; border:1px solid #dbe8ee; border-radius:10px; background:#fff;}
    .trace-step {font-size:.67rem; color:#718492; margin-bottom:.27rem;}
    .trace-name {font-size:.75rem; line-height:1.35; color:#284354; font-weight:650;}
    .trace-state {margin-top:.38rem; font-size:.68rem; font-weight:700;}
    .trace-runtime {margin-top:.24rem; font-size:.61rem; line-height:1.25; color:#718492; overflow-wrap:anywhere;}
    .trace-api {color:#047857;}.trace-local {color:#365267;}.trace-fallback {color:#b45309;}
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
if "w3_state" not in st.session_state:
    st.session_state.w3_state = default_session_state()
if "w3_current_customer_id" not in st.session_state:
    st.session_state.w3_current_customer_id = None
if "agent_trace" not in st.session_state:
    st.session_state.agent_trace = []


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
                st.markdown(content.replace("<br>", "；"))
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

    content = pattern.sub(replace_list, content)

    # Some model responses emit each customer as a standalone Python dict.
    dict_pattern = re.compile(r"\{[^{}\n]*\}")
    key_labels = {
        "序号": "序号", "name": "客户", "industry": "行业", "stage": "阶段",
        "priority": "优先级", "opportunity": "机会", "key_concerns": "关注点",
        "next_action": "下一步", "risk": "风险",
    }

    def replace_dict(match: re.Match[str]) -> str:
        try:
            record = ast.literal_eval(match.group(0))
        except (ValueError, SyntaxError):
            return match.group(0)
        if not isinstance(record, dict):
            return match.group(0)
        parts = []
        for key, value in record.items():
            label = key_labels.get(str(key), str(key))
            if isinstance(value, list):
                value = "、".join(str(item) for item in value)
            parts.append(f"{label}：{value}")
        return "<br>".join(parts)

    return dict_pattern.sub(replace_dict, content)


def render_execution_trace(trace: list[dict]) -> None:
    """Render the actual API/local fallback outcomes for every Agent Skill."""
    if not trace:
        return
    labels = {"api": "● API 完成", "local": "● 本地完成", "fallback": "● 安全回退"}
    cards = []
    for index, entry in enumerate(trace, 1):
        status = str(entry.get("status", "local"))
        safe_status = status if status in labels else "local"
        name = str(entry.get("name", "Skill"))
        runtime = str(entry.get("runtime", "Unknown runtime"))
        cards.append(
            f'<div class="trace-item"><div class="trace-step">SKILL {index}</div>'
            f'<div class="trace-name">{name}</div>'
            f'<div class="trace-state trace-{safe_status}">{labels[safe_status]}</div>'
            f'<div class="trace-runtime">{runtime}</div></div>'
        )
    st.markdown(
        '<div class="trace-title"><h4>⚙ Skills 执行轨迹 / Agent Execution Trace</h4>'
        '<span>基于本次实际运行结果，不展示模拟状态</span></div>'
        f'<div class="trace-grid">{"".join(cards)}</div>',
        unsafe_allow_html=True,
    )


def render_kpi_dashboard() -> None:
    """Render the W3 in-session KPI view from deterministic state only."""
    dashboard = build_kpi_dashboard(st.session_state.w3_state)
    st.caption("KPI 仅统计业务员在本页确认的跟进反馈；AI 分析与建议不会被当作已完成业绩。 / KPI counts only user-confirmed follow-up events.")
    metric_columns = st.columns(4)
    for column, metric in zip(metric_columns, dashboard["metrics"]):
        target_text = "未设置目标" if metric["target"] <= 0 else f"目标 {metric['target']}"
        progress_text = "—" if metric["progress"] is None else f"{metric['progress']}% · {metric['status']}"
        column.metric(metric["name"], metric["actual"], f"{target_text} · {progress_text}")
        if metric["target"] > 0:
            daily_text = "周期已结束" if metric["daily_required"] is None else f"后续日均需完成 {metric['daily_required']}"
            column.caption(f"应达 {metric['expected_by_today']} · 缺口 {metric['remaining_gap']} · {daily_text}")

    st.markdown("#### 今日优先行动 / Priority Actions")
    if dashboard["actions"]:
        st.dataframe(dashboard["actions"], width="stretch", hide_index=True)
    else:
        st.info("先生成一份客户业务报告，系统会将当前客户加入本次会话的行动队列。 / Generate a report to add a customer to this session.")

    if dashboard["warnings"]:
        st.markdown("#### 节奏与风险提醒 / Pace & Risk Alerts")
        for warning in dashboard["warnings"]:
            st.warning(warning)

    if dashboard["recent_feedback"]:
        st.markdown("#### 最近反馈记录 / Recent Activity")
        activity_rows = [
            {
                "日期": item["recorded_on"],
                "客户": item["customer_name"],
                "确认事件": item["event_label"],
                "说明": item["note"],
            }
            for item in dashboard["recent_feedback"]
        ]
        st.dataframe(activity_rows, width="stretch", hide_index=True)

    st.markdown("#### 记录一次跟进反馈 / Record Follow-up Feedback")
    customers = st.session_state.w3_state.get("customers", [])
    if not customers:
        return
    name_by_id = {item["id"]: item["name"] for item in customers}
    default_index = 0
    current_id = st.session_state.w3_current_customer_id
    if current_id in name_by_id:
        default_index = list(name_by_id).index(current_id)
    with st.form("w3_feedback_form", clear_on_submit=True):
        selected_id = st.selectbox(
            "本次反馈对应客户 / Customer",
            options=list(name_by_id),
            index=default_index,
            format_func=lambda item: name_by_id[item],
        )
        event = st.selectbox(
            "业务员确认的跟进结果 / Confirmed Outcome",
            options=list(EVENT_LABELS),
            format_func=lambda item: EVENT_LABELS[item],
        )
        note = st.text_area("补充说明（可选） / Notes", placeholder="例如：客户确认周三 15:00 参加线上演示")
        submitted = st.form_submit_button("保存反馈并更新 KPI / Save & Update")
    if submitted:
        try:
            state, customer_name = record_feedback(st.session_state.w3_state, selected_id, event, note)
            st.session_state.w3_state = state
            st.success(f"已记录 {customer_name}：{EVENT_LABELS[event]}。KPI 已按确认反馈更新。 / Feedback recorded and KPI updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"反馈记录失败 / Failed to record feedback：{exc}")

    st.caption(
        f"数据范围 / Data scope：{dashboard['source_scope']} 当前会话客户 {dashboard['customer_count']} 位，"
        f"已记录反馈 {dashboard['feedback_count']} 条。"
    )

api_ready = has_api_provider()
runtime_label = runtime_mode() if api_ready else "Mock Skills Workflow"
runtime_status = f"● {runtime_label} 已配置 / Connected" if api_ready else "● Mock Skills Workflow"

st.markdown(
    f"""
<section class="hero">
  <div class="hero-grid">
    <div>
      <span class="hero-eyebrow">✦ W3 AGENT DEMO · 目标驱动</span>
      <h1>知客 ZhiKe AI</h1>
      <p class="hero-kicker">让客户信息，转化为下一步业务行动</p>
      <p class="hero-desc">从非结构化沟通记录出发，完成客户理解、业务判断与行动生成；再由业务员确认反馈，形成可追溯的 KPI 进度和优先行动。</p>
      <div class="hero-flow">
        <span class="hero-node">客户理解</span><span class="hero-arrow">→</span>
        <span class="hero-node">业务判断</span><span class="hero-arrow">→</span>
        <span class="hero-node">行动生成</span><span class="hero-arrow">→</span>
        <span class="hero-node">KPI 反馈</span>
      </div>
    </div>
    <aside class="agent-panel">
      <div class="agent-panel-top"><span class="live-dot"></span> AGENT STATUS</div>
      <div class="agent-status">
        <div class="agent-status-item"><span>业务 Skills</span><strong>7 个已编排</strong></div>
        <div class="agent-status-item"><span>模型运行层</span><strong>{runtime_label}</strong></div>
        <div class="agent-status-item"><span>KPI 数据边界</span><strong>会话内可追溯</strong></div>
      </div>
      <p class="agent-panel-foot">分析由模型辅助生成；业绩反馈仅由业务员确认后计入 KPI。</p>
    </aside>
  </div>
</section>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class="status-row">
  <span class="status-pill prototype">W3 Agent Demo</span>
  <span class="status-pill {'online' if api_ready else ''}">{runtime_status}</span>
  <span class="status-pill">会话内 KPI / No Database</span>
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

st.markdown(
    """
<div class="goal-console">
  <div>
    <h3>🎯 本次会话目标与 KPI / Session Goals &amp; KPI</h3>
    <p>先定义业务节奏；KPI 仅会根据后续由业务员确认的反馈更新。 / Goals guide actions, not model-made performance.</p>
  </div>
  <span class="goal-badge">Session only · Not persisted</span>
</div>
""",
    unsafe_allow_html=True,
)
saved_goal = normalize_goal(st.session_state.w3_state.get("business_goal"))
with st.form("w3_goal_form"):
    goal_row_one = st.columns(3, gap="medium")
    with goal_row_one[0]:
        period = st.selectbox("目标周期 / Goal Period", ["本周", "本月"], index=0 if saved_goal["period"] == "本周" else 1)
    with goal_row_one[1]:
        total_workdays = st.number_input("周期总工作日 / Total Workdays", min_value=1, max_value=31, value=saved_goal["period_total_workdays"])
    with goal_row_one[2]:
        remaining_days = st.number_input("剩余工作日 / Working Days Left", min_value=0, max_value=31, value=saved_goal["remaining_workdays"])

    goal_row_two = st.columns(3, gap="medium")
    with goal_row_two[0]:
        qualified_target = st.number_input("新增合格客户 / Qualified Customers", min_value=0, max_value=100, value=saved_goal["new_qualified_customers_target"])
    with goal_row_two[1]:
        communication_target = st.number_input("有效沟通 / Effective Contacts", min_value=0, max_value=200, value=saved_goal["effective_communications_target"])
    with goal_row_two[2]:
        meeting_target = st.number_input("方案沟通 / 演示 / Demos", min_value=0, max_value=100, value=saved_goal["solution_meetings_target"])

    goal_row_three = st.columns([1, 1, 1], gap="medium")
    with goal_row_three[0]:
        advance_target = st.number_input("重点客户推进 / Priority Advances", min_value=0, max_value=100, value=saved_goal["priority_customers_to_advance_target"])
    _, save_column = goal_row_three[1:]
    with save_column:
        save_goal = st.form_submit_button("保存目标 / Save Goals", width="stretch")
if save_goal:
    st.session_state.w3_state["business_goal"] = normalize_goal(
        {
            "period": period,
            "period_total_workdays": total_workdays,
            "remaining_workdays": remaining_days,
            "new_qualified_customers_target": qualified_target,
            "effective_communications_target": communication_target,
            "solution_meetings_target": meeting_target,
            "priority_customers_to_advance_target": advance_target,
        }
    )
    st.success("业务目标已保存到当前会话。 / Session goals saved.")

left, right = st.columns([1.75, 1], gap="large")

with left:
    input_type = st.selectbox(
        "输入类型 / Input Type",
        ["微信聊天记录", "电话纪要", "会议记录", "业务员手动备注"],
    )
    st.subheader("客户信息输入 / Customer Input")
    customer_input = st.text_area(
        "粘贴客户备注、聊天摘要、电话纪要或会议记录 / Paste Customer Notes",
        key="customer_input",
        height=210,
        placeholder="例如：李总，做企业培训，最近想了解 AI 员工如何帮助销售团队做客户跟进……",
    )
    st.caption(f"当前输入 {len(customer_input.strip())} 个字符 · 无需预先整理，直接粘贴原始纪要即可 / Paste raw notes directly.")
    st.caption("无需先整理格式；知客会自动提取客户信息、需求和待确认事项。 / Missing information is marked for confirmation.")
    optional_name = st.text_input("客户称谓（可选） / Customer Name", placeholder="例如：李总")
    optional_channel = st.selectbox(
        "沟通渠道（可选） / Channel", ["未指定", "微信", "电话", "会议"]
    )
    optional_follow_up = st.text_input(
        "计划跟进时间（可选） / Follow-up Time", placeholder="例如：下周三上午"
    )
    st.info("信息不完整也可以生成；缺失内容会标记为‘未知/待确认’，无需先补齐。 / Incomplete notes are accepted.")

with right:
    st.subheader("示例案例 / Demo Cases")
    st.caption("点击后自动填充输入框，可继续编辑。 / Select a case to autofill the input.")
    for label, text in EXAMPLES.items():
        st.button(
            label,
            width="stretch",
            on_click=select_example,
            args=(text,),
        )
    st.markdown(
        '<div class="scope"><strong>W2 范围 / W2 Scope</strong><br>Mock 客户仅用于跨客户日报演示；无数据库、登录、CRM 或微信接入。<br><span style="font-size:.78rem">Mock customers are for daily-report aggregation only.</span></div>',
        unsafe_allow_html=True,
    )
    force_mock = st.toggle(
        "强制使用 Mock 演示模式 / Force Mock Mode",
        value=not api_ready,
    )
    st.caption(f"当前运行模式 / Runtime Mode：{runtime_mode(force_mock=force_mock)}")

generate = st.button("生成业务报告 / Generate Business Report", type="primary", width="stretch")

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
        with st.status("知客正在按 7 个 Skills 处理客户信息 / Running 7 Agent Skills…", expanded=False) as status:
            run_result = business_agent_with_trace(enriched_input, force_mock=force_mock)
            st.session_state.report = run_result["report"]
            st.session_state.agent_trace = run_result["trace"]
            api_steps = sum(1 for item in run_result["trace"] if item["status"] == "api")
            fallback_steps = sum(1 for item in run_result["trace"] if item["status"] == "fallback")
            status.update(
                label=f"业务报告已完成 / Report ready · API Skills {api_steps} · 安全回退 {fallback_steps}",
                state="complete",
                expanded=False,
            )
        # KPI state is deliberately isolated from the report-generation path:
        # an unexpected KPI issue must never invalidate an already generated report.
        try:
            state, current_customer = ingest_customer(
                st.session_state.w3_state,
                customer_input,
                customer_name=optional_name,
            )
            st.session_state.w3_state = state
            st.session_state.w3_current_customer_id = current_customer["id"]
        except Exception as state_exc:
            st.warning(f"报告已生成，但本次未写入 W3 会话状态 / Report generated, but session state was not saved：{state_exc}")
    except Exception as exc:
        st.session_state.report = None
        st.session_state.agent_trace = []
        st.error(f"生成失败 / Generation failed：{exc}")

report = st.session_state.report
if report:
    st.markdown(
        """
<div class="result-head">
  <strong>业务处理报告 / Business Processing Report</strong>
  <span>✓ 7 Skills complete · Confirm feedback to update session KPI</span>
</div>
""",
        unsafe_allow_html=True,
    )
    st.success("业务报告已生成。请在发送话术或作出业务决策前进行人工确认。 / Please confirm before sending or deciding.")
    render_execution_trace(st.session_state.agent_trace)
    tabs = st.tabs(
        ["👤 客户档案 / Profile", "🔎 需求分析 / Needs", "📈 机会判断 / Opportunity", "✅ 跟进建议 / Follow-up", "💬 沟通话术 / Script", "🗓️ 业务日报 / Daily Report", "🎯 KPI 与行动 / Actions"]
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
    with tabs[-1]:
        render_kpi_dashboard()

st.divider()
st.markdown(
    '<div class="footer-note">W3 Agent Demo · KPI 仅统计当前会话内经业务员确认的反馈 · 不保存客户数据 · 最终发送与业务决策由人工确认<br><span style="font-size:.76rem">KPI counts only user-confirmed feedback in this session. No customer data is persisted.</span></div>',
    unsafe_allow_html=True,
)
