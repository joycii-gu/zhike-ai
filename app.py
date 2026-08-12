"""ZhiKe AI W4 business workspace.

This Streamlit application keeps the existing seven-Skill Agent runtime and
adds the minimum product layer required for continuous use: account isolation,
durable customer records, tasks, human feedback and auditable KPI events.
"""

from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from src.agent import business_agent_with_trace, has_api_provider, runtime_mode
from src.kpi_agent import EVENT_LABELS
from src.storage import (
    authenticate_user,
    create_customer,
    create_task,
    create_user,
    dashboard_snapshot,
    get_customer,
    initialize_database,
    list_customers,
    list_tasks,
    record_feedback_event,
    revert_feedback_event,
    save_report,
    update_task_status,
)


EXAMPLES = {
    "企业培训客户": "李总，做企业培训，最近想了解 AI 员工如何帮助销售团队做客户跟进。之前看过我们的 HermesAgent 安装服务，对 AI 业务助理感兴趣，但还没有明确预算，希望下周约一次线上沟通。他比较关心部署难度、价格、实际效果，以及业务员是否真的会用。",
    "课程顾问客户": "周校长经营一家职业技能培训机构，想了解 AI 能否帮助课程顾问整理学员微信咨询、判断报名意向并生成后续沟通话术。机构目前有 6 名课程顾问，新人较多，担心 AI 话术太生硬，也担心顾问不会使用。预算暂时没有确定，希望本周五先看一次线上演示，再决定是否安排小范围试用。",
    "企业服务客户": "赵总负责一家为小微企业提供工商、财税和政策咨询服务的公司。团队有 4 名业务员，客户需求经常散落在电话纪要和个人备注里。赵总希望 AI 帮助整理企业客户需求、提炼方案沟通重点并生成跟进计划。目前处于内部了解阶段，关注数据保密、输出准确性和员工使用成本。",
}

NAVIGATION = {
    "工作台": "◫",
    "客户管理": "◎",
    "跟进任务": "✓",
    "新建分析": "＋",
}


st.set_page_config(page_title="知客 ZhiKe AI", page_icon="◆", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
:root { --brand:#2B5FE0; --brand-dark:#173B91; --ink:#182230; --muted:#667085; --line:#EAECF0; --surface:#ffffff; --canvas:#F8FAFC; }
.stApp { background:var(--canvas); color:var(--ink); font-family:'Microsoft YaHei','Noto Sans CJK SC','PingFang SC',Arial,sans-serif; }
.block-container { max-width:1380px; padding:2rem 2.25rem 4rem; }
[data-testid='stSidebar'] { background:#0B1F3A; }
[data-testid='stSidebar'] * { color:#E8EEF8 !important; }
[data-testid='stSidebar'] .stRadio > div { gap:.35rem; }
[data-testid='stSidebar'] label { padding:.55rem .7rem; border-radius:9px; }
[data-testid='stSidebar'] label:has(input:checked) { background:#244EAE; }
h1,h2,h3 { letter-spacing:-.025em; }
h1 { font-size:30px !important; font-weight:700 !important; margin-bottom:.1rem !important; }
h2 { font-size:21px !important; font-weight:700 !important; }
.muted { color:var(--muted); font-size:13px; }
.workspace-head { display:flex; align-items:flex-start; justify-content:space-between; margin:0 0 1.75rem; }
.logo { font:700 21px/1 'Microsoft YaHei','Noto Sans CJK SC',Arial,sans-serif; letter-spacing:-.04em; margin:1rem .25rem 1.5rem; color:white; }
.logo span { color:#6EA0FF; }
.side-note { margin-top:3rem; border-top:1px solid rgba(255,255,255,.14); padding-top:1rem; font-size:12px; line-height:1.7; color:#B9C7DD; }
.metric-card,.panel { background:var(--surface); border:1px solid var(--line); border-radius:12px; box-shadow:0 1px 3px rgba(16,24,40,.06),0 1px 2px rgba(16,24,40,.04); }
.metric-card { padding:20px 22px; min-height:150px; }
.metric-label { color:#475467; font-size:14px; font-weight:600; margin-bottom:10px; }
.metric-value { font-family:'Arial','Microsoft YaHei',sans-serif; font-variant-numeric:tabular-nums; font-size:32px; font-weight:700; color:var(--brand); }
.metric-target { color:#98A2B3; font-size:16px; margin-left:4px; }
.progress-track { height:6px; border-radius:999px; background:#EAECF0; margin:16px 0 9px; overflow:hidden; }
.progress-fill { height:100%; min-width:2px; border-radius:999px; background:var(--brand); }
.metric-foot { color:#667085; font-size:12px; }
.panel { padding:20px 22px; margin-top:1rem; }
.panel-title { display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; font-size:17px; font-weight:700; }
.panel-title small { color:var(--brand); font-weight:600; font-size:12px; }
.pill { display:inline-block; border-radius:999px; padding:4px 10px; font-size:12px; line-height:1.35; font-weight:600; border:0; }
.pill-high { background:#FEECEC; color:#D0292E; }.pill-medium { background:#FFF3E5; color:#B54708; }.pill-normal { background:#ECFDF3; color:#027A48; }.pill-pending { background:#EFF6FF; color:#175CD3; }
.source { display:inline-block; font-size:12px; padding:3px 9px; border-radius:999px; margin-right:5px; background:#F2F4F7; color:#475467; }.source-fact { background:#ECFDF3;color:#027A48; }.source-inference { background:#EFF6FF;color:#175CD3; }.source-pending { background:#FFF6E8;color:#B54708; }.source-human { background:#F4F3FF;color:#5925DC; }
.table-wrap table { border-collapse:separate; border-spacing:0; overflow:hidden; border:1px solid var(--line); border-radius:10px; width:100%; }
.table-wrap th { background:#F9FAFB; color:#667085; font-size:12px; letter-spacing:.02em; text-align:left; padding:13px 14px; }.table-wrap td { padding:16px 14px; border-top:1px solid var(--line); font-size:14px; vertical-align:middle; }.table-wrap tr:hover td { background:#F9FAFB; }
.task-action { color:var(--brand); font-weight:600; font-size:13px; }
.privacy { border-left:4px solid var(--brand); background:#EFF6FF; color:#344054; border-radius:8px; padding:14px 16px; line-height:1.7; font-size:13px; margin:1rem 0; }
.report-section { border:1px solid var(--line); border-radius:12px; padding:18px 20px; background:#fff; margin:0 0 14px; }.report-section h3 { font-size:17px!important; margin:0 0 10px; }.report-section p,.report-section li { line-height:1.75; }
.trace { display:grid; grid-template-columns:repeat(7,minmax(105px,1fr)); gap:9px; overflow-x:auto; margin:1rem 0; }.trace-card { border:1px solid #DCE6F1; border-radius:10px; padding:12px; min-width:105px; }.trace-card b { display:block; font-size:13px; margin:5px 0; }.trace-card small { color:#667085; font-size:11px; }.api { color:#027A48; }.fallback { color:#B54708; }.local { color:#175CD3; }
.login-wrap { max-width:440px; margin:9vh auto; }.login-card { background:white;border:1px solid var(--line);border-radius:16px;padding:30px;box-shadow:0 8px 30px rgba(16,24,40,.08); }.login-card h1 { margin:0!important; }.login-card p { color:#667085; line-height:1.65; }
.stButton > button { border-radius:8px; font-weight:600; min-height:42px; }.stButton > button[kind='primary'] { background:var(--brand); border-color:var(--brand); }.stButton > button[kind='primary']:hover { background:var(--brand-dark); border-color:var(--brand-dark); }
div[data-testid='stDataFrame'] { border:1px solid var(--line); border-radius:10px; overflow:hidden; }
@media(max-width:900px){ .block-container{padding:1.25rem 1rem 3rem}.trace{grid-template-columns:repeat(3,1fr)} }
</style>
""",
    unsafe_allow_html=True,
)


def infer_metadata(text: str, name: str) -> dict[str, str]:
    industry = "待确认"
    for keyword, value in (("企业培训", "企业培训"), ("职业技能", "职业教育"), ("财税", "企业服务"), ("工商", "企业服务"), ("软件", "企业软件")):
        if keyword in text:
            industry = value
            break
    stage = "需求探索"
    if any(word in text for word in ("演示", "线上沟通", "下周", "本周五")):
        stage = "沟通/演示准备"
    priority = "高" if any(word in text for word in ("演示", "本周", "下周", "试用")) else "中"
    risk = "预算或决策信息待确认" if "预算" in text else "需确认下一步跟进安排"
    return {"industry": industry, "stage": stage, "priority": priority, "risk": risk, "name": name or "待确认客户"}


def pill(value: str) -> str:
    if "高" in value or "风险" in value:
        style = "pill-high"
    elif "中" in value:
        style = "pill-medium"
    elif "待" in value or "确认" in value:
        style = "pill-pending"
    else:
        style = "pill-normal"
    return f'<span class="pill {style}">{value}</span>'


def source_badges() -> str:
    return '<span class="source source-fact">事实</span><span class="source source-inference">AI 推断</span><span class="source source-pending">待确认</span><span class="source source-human">人工确认</span>'


def render_report(content: str) -> None:
    """Display a field clearly even when the provider returns JSON text."""
    try:
        data = json.loads(content)
    except (TypeError, json.JSONDecodeError):
        data = None
    if isinstance(data, dict):
        rows = "".join(f"<tr><th>{key}</th><td>{value if not isinstance(value, list) else '；'.join(map(str,value))}</td></tr>" for key, value in data.items())
        st.markdown(f'<div class="table-wrap"><table>{rows}</table></div>', unsafe_allow_html=True)
    elif isinstance(data, list):
        st.markdown("\n".join(f"- {item}" for item in data))
    else:
        safe = re.sub(r"\n{3,}", "\n\n", content).replace("<br>", "\n")
        st.markdown(safe)


def render_trace(trace: list[dict[str, Any]]) -> None:
    if not trace:
        return
    cards = []
    for index, item in enumerate(trace, 1):
        status = str(item.get("status", "local"))
        label = {"api": "● API 完成", "fallback": "● 安全回退", "local": "● 本地规则"}.get(status, "● 已完成")
        cards.append(f'<div class="trace-card"><small>SKILL {index}</small><b>{item.get("name", "业务 Skill")}</b><span class="{status}">{label}</span><br><small>{item.get("runtime", "")}</small></div>')
    st.markdown('<div class="trace">' + ''.join(cards) + '</div>', unsafe_allow_html=True)


def init() -> None:
    initialize_database()
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("page", "工作台")
    st.session_state.setdefault("selected_customer", None)
    st.session_state.setdefault("analysis_input", EXAMPLES["企业培训客户"])


def login_screen() -> None:
    st.markdown('<div class="login-wrap"><div class="login-card">', unsafe_allow_html=True)
    st.markdown("# 知客 ZhiKe AI")
    st.markdown("<p>面向业务人员的 AI 业务工作台。客户、任务、反馈与 KPI 仅归属于当前账号。</p>", unsafe_allow_html=True)
    login, register = st.tabs(["登录", "注册账号"])
    with login:
        with st.form("login"):
            email = st.text_input("邮箱")
            password = st.text_input("密码", type="password")
            submit = st.form_submit_button("登录", type="primary", width="stretch")
        if submit:
            user = authenticate_user(email, password)
            if user:
                st.session_state.user = user
                st.rerun()
            st.error("邮箱或密码不正确。")
    with register:
        with st.form("register"):
            name = st.text_input("姓名")
            email = st.text_input("邮箱", key="register_email")
            password = st.text_input("设置密码（至少 8 位）", type="password", key="register_password")
            submit = st.form_submit_button("创建账号", type="primary", width="stretch")
        if submit:
            try:
                st.session_state.user = create_user(email, name, password)
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
    st.markdown('</div></div>', unsafe_allow_html=True)


def sidebar() -> str:
    user = st.session_state.user
    with st.sidebar:
        st.markdown('<div class="logo">知客 <span>ZhiKe AI</span></div>', unsafe_allow_html=True)
        pages = list(NAVIGATION)
        current = st.session_state.page if st.session_state.page in pages else pages[0]
        page = st.radio("导航", pages, index=pages.index(current), format_func=lambda item: f"{NAVIGATION[item]}　{item}", label_visibility="collapsed")
        st.session_state.page = page
        st.markdown(f'<div class="side-note"><b>{user["display_name"]}</b><br>{user["email"]}<br><br>数据仅对当前账号可见<br>AI 原始记录会发送至已配置模型服务</div>', unsafe_allow_html=True)
        if st.button("退出登录", width="stretch"):
            st.session_state.user = None
            st.session_state.selected_customer = None
            st.rerun()
    return page


def header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="workspace-head"><div><h1>{title}</h1><div class="muted">{subtitle}</div></div><div class="muted">当前账号：{st.session_state.user["display_name"]}</div></div>', unsafe_allow_html=True)


def dashboard() -> None:
    user_id = st.session_state.user["id"]
    snapshot = dashboard_snapshot(user_id)
    header("今日业务工作台", "AI Business Workspace · 以人工确认的业务结果驱动 KPI")
    targets = (("新增合格客户", snapshot["qualified_customers"], 3), ("有效沟通", snapshot["effective_communications"], 5), ("方案沟通/演示", snapshot["solution_meetings"], 2), ("重点客户推进", snapshot["priority_advanced"], 2))
    cols = st.columns(4)
    for column, (name, actual, target) in zip(cols, targets):
        percent = min(100, round(actual / target * 100))
        column.markdown(f'<div class="metric-card"><div class="metric-label">{name}</div><span class="metric-value">{actual}</span><span class="metric-target">/ {target}</span><div class="progress-track"><div class="progress-fill" style="width:{percent}%"></div></div><div class="metric-foot">完成进度 {percent}% · 仅统计人工确认</div></div>', unsafe_allow_html=True)
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        st.markdown('<div class="panel"><div class="panel-title">今日优先行动 <small>查看任务 ›</small></div>', unsafe_allow_html=True)
        tasks = snapshot["tasks"][:5]
        if tasks:
            rows = ''.join(f"<tr><td><b>{task['customer_name']}</b></td><td>{task['title']}</td><td>{task['due_at'] or '未设截止时间'}</td><td>{pill(task['priority'])}</td><td>{pill(task['status'])}</td></tr>" for task in tasks)
            st.markdown(f'<div class="table-wrap"><table><thead><tr><th>客户</th><th>下一步</th><th>截止时间</th><th>优先级</th><th>状态</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.info("暂无待办任务。创建客户分析后，可把 AI 跟进建议保存为任务。")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-title">最近客户 <small>客户数据已持久化</small></div>', unsafe_allow_html=True)
        customers = snapshot["customers"][:5]
        if customers:
            rows = ''.join(f"<tr><td><b>{item['name']}</b><br><span class='muted'>{item['industry'] or '待确认'}</span></td><td>{item['stage'] or '待确认'}</td><td>{pill(item['priority'] or '待确认')}</td><td>{item['updated_at'][:10]}</td></tr>" for item in customers)
            st.markdown(f'<div class="table-wrap"><table><thead><tr><th>客户</th><th>当前阶段</th><th>优先级</th><th>最近更新</th></tr></thead><tbody>{rows}</tbody></table></div>', unsafe_allow_html=True)
        else:
            st.caption("尚无客户记录。")
        st.markdown('</div>', unsafe_allow_html=True)
    with right:
        st.markdown('<div class="panel"><div class="panel-title">风险提醒 <small>基于客户记录</small></div>', unsafe_allow_html=True)
        risks = [item for item in snapshot["customers"] if item.get("risk")][:4]
        if risks:
            for item in risks:
                st.markdown(f"<div style='padding:10px 0;border-bottom:1px solid #EAECF0'><b>{item['name']}</b><br><span class='muted'>{item['risk']}</span></div>", unsafe_allow_html=True)
        else:
            st.caption("暂无风险提醒。")
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('<div class="panel"><div class="panel-title">AI 分析状态 <small>可追溯 Skills</small></div>', unsafe_allow_html=True)
        st.markdown("客户解析　需求分析　商机判断　跟进建议　沟通话术　业务日报")
        st.caption("每次分析都会保存本次运行来源、Skill 执行状态和报告版本。")
        st.markdown('</div>', unsafe_allow_html=True)


def new_analysis() -> None:
    header("新建客户分析", "粘贴原始记录 → 7 个 Skills 分析 → 人工确认 → 创建任务")
    st.markdown('<div class="privacy"><b>数据与隐私提示</b><br>输入内容会发送至当前配置的第三方模型 API 用于生成分析。请勿输入身份证号、银行卡号、完整联系方式、合同密钥等敏感信息。知客在本服务器保存客户记录；外部模型服务的数据处理以其自身政策为准。</div>', unsafe_allow_html=True)
    left, right = st.columns([1.7, 1], gap="large")
    with left:
        name = st.text_input("客户称谓（可选）", placeholder="例如：李总")
        text = st.text_area("客户原始记录", key="analysis_input", height=260, placeholder="粘贴聊天记录、电话纪要、会议记录或业务备注。")
        force_mock = st.toggle("强制使用本地 Mock 模式", value=not has_api_provider())
        st.caption(f"当前运行源：{runtime_mode(force_mock=force_mock)}。生成过程会显示每一步真实运行来源。")
        generate = st.button("开始 AI 分析", type="primary", width="stretch", disabled=not text.strip())
    with right:
        st.markdown("#### 示例案例")
        for label, value in EXAMPLES.items():
            if st.button(label, width="stretch"):
                st.session_state.analysis_input = value
                st.rerun()
        st.markdown("#### 本次将执行")
        st.caption("1. 客户信息解析\n\n2. 客户档案生成\n\n3. 客户需求分析\n\n4. 商机判断\n\n5. 跟进建议\n\n6. 沟通话术\n\n7. 业务日报")
    if generate:
        with st.status("正在执行 7 个业务 Skills…", expanded=True) as status:
            result = business_agent_with_trace(text, force_mock=force_mock)
            status.update(label="分析完成，正在保存客户与报告…", state="running")
            metadata = infer_metadata(text, name)
            customer_id = create_customer(st.session_state.user["id"], metadata["name"], text, metadata)
            save_report(st.session_state.user["id"], customer_id, result["report"], result["trace"], runtime_mode(force_mock=force_mock))
            status.update(label="客户分析已保存", state="complete", expanded=False)
        st.session_state.selected_customer = customer_id
        st.session_state.page = "客户管理"
        st.success("已创建客户、保存 AI 报告，并进入客户详情。")
        st.rerun()


def customers_page() -> None:
    user_id = st.session_state.user["id"]
    header("客户管理", "客户资料、AI 结论和人工确认均按账号持久化保存")
    customers = list_customers(user_id)
    if not customers:
        st.info("还没有客户。请先在“新建分析”中生成第一份客户报告。")
        return
    choices = {f"{item['name']} · {item['industry'] or '待确认'}": item["id"] for item in customers}
    current = st.session_state.selected_customer
    default = next((index for index, item in enumerate(choices.values()) if item == current), 0)
    selected_label = st.selectbox("选择客户", list(choices), index=default)
    customer = get_customer(user_id, choices[selected_label])
    if not customer:
        st.error("无法读取客户数据。")
        return
    st.session_state.selected_customer = customer["id"]
    st.markdown(f"## {customer['name']}　{pill(customer['priority'] or '待确认')}", unsafe_allow_html=True)
    st.markdown(source_badges(), unsafe_allow_html=True)
    summary = st.columns(4)
    for column, label, value in zip(summary, ("行业", "阶段", "风险", "状态"), (customer["industry"] or "待确认", customer["stage"] or "待确认", customer["risk"] or "待确认", customer["status"])):
        column.markdown(f"<div class='metric-card'><div class='metric-label'>{label}</div><div style='font-weight:600;line-height:1.5'>{value}</div></div>", unsafe_allow_html=True)
    tabs = st.tabs(["客户原始记录", "AI 分析报告", "任务与反馈", "数据边界"])
    with tabs[0]:
        st.markdown("### 原始记录")
        st.text_area("来源：客户原话 / 业务员录入", value=customer["raw_note"], height=220, disabled=True)
        st.caption("原始记录不自动等同于事实结论；AI 推断会在报告中单独标识，最终以人工确认版本为准。")
    with tabs[1]:
        if not customer["report"]:
            st.info("该客户暂无已保存的 AI 报告。")
        else:
            render_trace(customer["trace"])
            for key, title in (("customer_profile", "客户档案"), ("need_analysis", "客户需求分析"), ("opportunity_assessment", "业务机会判断"), ("follow_up_plan", "跟进建议"), ("communication_script", "沟通话术"), ("daily_report", "业务日报")):
                with st.expander(title, expanded=key in {"customer_profile", "opportunity_assessment", "follow_up_plan"}):
                    st.markdown(source_badges(), unsafe_allow_html=True)
                    render_report(customer["report"][key])
                    if key == "follow_up_plan":
                        if st.button("将此建议创建为跟进任务", key=f"task_{customer['id']}"):
                            create_task(user_id, customer["id"], "按 AI 跟进建议推进：" + customer["name"])
                            st.success("任务已创建。")
                    if key == "communication_script":
                        st.code(customer["report"][key], language=None)
                        st.caption("仅供复制、编辑和人工确认；知客不会直接向客户发送内容。")
    with tabs[2]:
        st.markdown("### 跟进任务")
        with st.form("new_task"):
            title = st.text_input("新建任务")
            due_at = st.text_input("截止时间（可选）", placeholder="例如：2026-08-13 15:00")
            if st.form_submit_button("创建任务"):
                try:
                    create_task(user_id, customer["id"], title, due_at, "人工创建")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        tasks = [task for task in list_tasks(user_id, include_done=True) if task["customer_name"] == customer["name"]]
        for task in tasks:
            left, middle, right = st.columns([5, 2, 2])
            left.write(task["title"])
            middle.write(task["status"])
            if task["status"] != "已完成" and right.button("完成", key=f"done_{task['id']}"):
                update_task_status(user_id, task["id"], "已完成")
                st.rerun()
        st.markdown("### 记录真实跟进结果")
        with st.form("feedback"):
            event = st.selectbox("业务员确认的结果", list(EVENT_LABELS), format_func=lambda item: EVENT_LABELS[item])
            note = st.text_input("说明（可选）")
            if st.form_submit_button("确认并更新 KPI"):
                record_feedback_event(user_id, customer["id"], event, note)
                st.success("已记录。KPI 仅按该人工确认事件计算。")
                st.rerun()
        for event in customer["feedback"]:
            state = "已撤销" if event["is_reverted"] else "已确认"
            cols = st.columns([5, 2, 2])
            cols[0].write(f"{EVENT_LABELS.get(event['event_type'], event['event_type'])} · {event['note'] or '未补充说明'}")
            cols[1].caption(event["created_at"][:16])
            if not event["is_reverted"] and cols[2].button("撤销", key=f"revert_{event['id']}"):
                revert_feedback_event(user_id, event["id"])
                st.rerun()
            elif event["is_reverted"]:
                cols[2].caption(state)
    with tabs[3]:
        st.markdown('<div class="privacy"><b>数据范围</b><br>客户记录与 AI 报告保存在当前 ECS/服务器的应用数据库中，并按当前账号隔离。生成分析时，原始文本会发送到当前配置的模型 API。请使用脱敏示例或获得授权的业务信息；不要提交高敏感个人信息。</div>', unsafe_allow_html=True)


def tasks_page() -> None:
    header("跟进任务", "把 AI 建议转成可执行、可完成、可追踪的业务动作")
    tasks = list_tasks(st.session_state.user["id"], include_done=True)
    if not tasks:
        st.info("暂无任务。请从客户报告的“跟进建议”中创建任务。")
        return
    for task in tasks:
        cols = st.columns([2, 5, 2, 2, 1])
        cols[0].write(task["customer_name"])
        cols[1].write(task["title"])
        cols[2].write(task["due_at"] or "未设截止时间")
        cols[3].markdown(pill(task["status"]), unsafe_allow_html=True)
        if task["status"] == "待办" and cols[4].button("完成", key=f"task_done_{task['id']}"):
            update_task_status(st.session_state.user["id"], task["id"], "已完成")
            st.rerun()


def main() -> None:
    init()
    if not st.session_state.user:
        login_screen()
        return
    page = sidebar()
    if page == "工作台":
        dashboard()
    elif page == "新建分析":
        new_analysis()
    elif page == "客户管理":
        customers_page()
    else:
        tasks_page()


if __name__ == "__main__":
    main()
