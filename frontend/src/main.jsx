import { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { api } from "./api";
import "./styles.css";

const NAV = [
  ["dashboard", "⌂", "业务驾驶舱"],
  ["customers", "◉", "客户洞察"],
  ["tasks", "✓", "智能跟进"],
  ["analysis", "＋", "新建分析"],
];

const EXAMPLES = {
  "企业培训客户": "李总，做企业培训，最近想了解 AI 员工如何帮助销售团队做客户跟进。之前看过我们的 HermesAgent 安装服务，对 AI 业务助理感兴趣，但还没有明确预算，希望下周约一次线上沟通。他比较关心部署难度、价格、实际效果，以及业务员是否真的会用。",
  "课程顾问客户": "周校长经营职业技能培训机构，想用 AI 整理学员咨询、判断报名意向并生成顾问话术。本周五可以线上演示，关注新人顾问是否容易上手；预算和试用范围尚待确认。",
  "企业服务客户": "赵总经营小微企业工商、财税和政策咨询服务，团队有 4 名业务员。希望 AI 整理企业客户电话纪要并形成方案沟通重点和跟进计划，关注数据保密、输出准确性和员工使用成本，目前处于内部了解阶段。",
};

function App() {
  const [session, setSession] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [dashboard, setDashboard] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [health, setHealth] = useState(null);
  const [selected, setSelected] = useState(null);
  const [toast, setToast] = useState("");

  const refresh = async () => {
    const [d, c, t, h] = await Promise.all([api.dashboard(), api.customers(), api.tasks(), api.health()]);
    setDashboard(d); setCustomers(c); setTasks(t); setHealth(h);
  };
  useEffect(() => { api.me().then((user) => { setSession(user); refresh(); }).catch(() => setSession(null)); }, []);
  const notify = (text) => { setToast(text); window.setTimeout(() => setToast(""), 2800); };
  if (!session) return <Auth onAuth={(user) => { setSession(user); refresh(); }} />;
  const chooseCustomer = async (id) => { setSelected(await api.customer(id)); setPage("customers"); };
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><b>知客</b><span>ZhiKe AI</span><small>AI Business Assistant</small></div>
      <nav>{NAV.map(([key, icon, label]) => <button key={key} className={page === key ? "nav active" : "nav"} onClick={() => setPage(key)}><i>{icon}</i>{label}</button>)}</nav>
      <div className="sidebar-foot"><span className="avatar">知</span><div><b>我的业务空间</b><small>数据仅归属当前账号</small></div><button className="logout" onClick={() => api.logout().then(() => setSession(null))}>退出</button></div>
    </aside>
    <main className="main"><header className="topbar"><div><p className="eyebrow">AI BUSINESS COMMAND CENTER</p><h1>{page === "dashboard" ? "今日业务驾驶舱" : page === "analysis" ? "新建客户分析" : page === "customers" ? "客户洞察" : "智能跟进"}</h1></div><div className="runtime"><span className={health?.api_configured ? "dot online" : "dot"}></span>{health?.runtime || "正在检查 Agent Runtime"}</div></header>
      {page === "dashboard" && <Dashboard dashboard={dashboard} tasks={tasks} customers={customers} onCreate={() => setPage("analysis")} onCustomer={chooseCustomer} />}
      {page === "analysis" && <Analysis onDone={async (customer) => { await refresh(); setSelected(customer); setPage("customers"); notify("分析完成，已保存到客户洞察"); }} />}
      {page === "customers" && <Customers customers={customers} selected={selected} onSelect={chooseCustomer} onFeedback={async (payload) => { await api.feedback(payload); await refresh(); setSelected(await api.customer(payload.customer_id)); notify("已记录人工确认反馈，KPI 已更新"); }} />}
      {page === "tasks" && <Tasks tasks={tasks} onRefresh={refresh} onCustomer={chooseCustomer} />}
    </main>{toast && <div className="toast">✓ {toast}</div>}
  </div>;
}

function Auth({ onAuth }) {
  const [mode, setMode] = useState("login"), [email, setEmail] = useState(""), [password, setPassword] = useState(""), [name, setName] = useState(""), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const submit = async (e) => { e.preventDefault(); setBusy(true); setError(""); try { const data = mode === "login" ? await api.login({ email, password }) : await api.register({ email, display_name: name, password }); onAuth(data.user); } catch (err) { setError(err.message); } finally { setBusy(false); } };
  return <div className="auth-page"><section className="auth-brand"><p className="brand-kicker">● AI BUSINESS COMMAND CENTER</p><h1>知客 <span>ZhiKe AI</span></h1><p>把分散的客户信息，转化为下一步业务行动。知客协助业务人员理解客户、推进任务，并以人工确认结果驱动业务 KPI。</p><div className="feature-pills"><span>客户洞察</span><span>智能跟进</span><span>风险提示</span><span>KPI 反馈</span></div><small>企业级业务工作空间<br/>你的客户、任务与反馈仅归属于当前账号</small></section><section className="auth-form-wrap"><form className="auth-card" onSubmit={submit}><p className="eyebrow">WELCOME TO ZHIKE</p><h2>{mode === "login" ? "欢迎回来" : "创建业务空间"}</h2><p>{mode === "login" ? "登录后继续管理你的客户与任务。" : "注册后即可创建你的 AI 业务工作台。"}</p>{mode === "register" && <label>姓名<input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：Stella" required /></label>}<label>邮箱<input value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="name@example.com" required /></label><label>密码<input value={password} onChange={(e) => setPassword(e.target.value)} type="password" minLength="8" placeholder="至少 8 位" required /></label>{error && <div className="form-error">{error}</div>}<button className="primary" disabled={busy}>{busy ? "正在处理…" : mode === "login" ? "登录业务空间" : "创建账号"}</button><button className="text-button" type="button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "没有账号？立即注册" : "已有账号？返回登录"}</button><small className="privacy">登录即表示：你的数据仅在当前账户业务空间内管理；AI 分析会发送至已配置的模型服务。</small></form></section></div>;
}

function Dashboard({ dashboard, tasks, customers, onCreate, onCustomer }) {
  const metrics = [ ["新增客户", dashboard?.customer_count || 0, "客户洞察"], ["有效沟通", dashboard?.effective_communications || 0, "人工确认"], ["方案沟通", dashboard?.solution_meetings || 0, "人工确认"], ["重点客户推进", dashboard?.priority_advanced || 0, "人工确认"] ];
  return <><section className="hero"><div><p className="eyebrow">TODAY · FOCUS · ACTION</p><h2>让每一次客户跟进<br/>都有清晰的下一步。</h2><p>从原始沟通记录到客户理解、机会判断和人工确认的 KPI 反馈闭环。</p><button className="primary" onClick={onCreate}>＋ 新建客户分析</button></div><div className="hero-agent"><b><span className="dot online"/> Agent Status</b><p>7 个业务 Skills 已编排</p><p>KPI 仅统计人工确认事件</p><p>当前账户数据隔离</p></div></section><section className="metric-grid">{metrics.map(([label, value, detail]) => <article className="metric-card" key={label}><p>{label}</p><b>{value}</b><span>{detail}</span><div className="progress"><i style={{ width: `${Math.min(100, Number(value) * 20)}%` }} /></div></article>)}</section><section className="workspace-grid"><article className="panel actions"><div className="panel-title"><div><p className="eyebrow">AI RECOMMENDED</p><h3>今日优先行动</h3></div><button onClick={() => onCreate()}>新建分析 →</button></div>{tasks.slice(0, 5).map((task) => <div className="task-row" key={task.id}><span className="priority">{task.priority || "中"}</span><div><b>{task.customer_name}</b><p>{task.title}</p></div><span className="task-status">{task.status}</span><button onClick={() => onCustomer(task.customer_id)}>查看 →</button></div>)}{!tasks.length && <Empty title="还没有待办行动" body="先分析一位客户，知客会将后续动作转为可管理的任务。" action="新建客户分析" onAction={onCreate} />}</article><aside className="side-panels"><article className="panel"><div className="panel-title"><h3>风险提醒</h3><span>TOP RISKS</span></div>{customers.slice(0, 4).map((c) => <button className="risk-row" key={c.id} onClick={() => onCustomer(c.id)}><i className={c.priority === "高" ? "risk high" : "risk"}></i><div><b>{c.name}</b><p>{c.risk || "待确认关键业务信息"}</p></div><span>{c.priority || "中"}</span></button>)}{!customers.length && <p className="muted">暂无客户风险信息</p>}</article><article className="panel"><div className="panel-title"><h3>最近客户</h3><span>{customers.length} 位</span></div>{customers.slice(0, 4).map((c) => <button className="customer-mini" key={c.id} onClick={() => onCustomer(c.id)}><span className="avatar">{c.name?.slice(0, 1)}</span><div><b>{c.name}</b><p>{c.industry || "待确认"} · {c.stage || "需求确认"}</p></div><span>→</span></button>)}</article></aside></section></>;
}

function Analysis({ onDone }) {
  const [note, setNote] = useState(""), [name, setName] = useState(""), [mock, setMock] = useState(false), [busy, setBusy] = useState(false), [stage, setStage] = useState(""), [error, setError] = useState("");
  const run = async () => { if (note.trim().length < 8) return setError("请至少输入 8 个字符的客户记录"); setBusy(true); setError(""); const steps = ["提取客户关键信息", "分析需求与机会", "生成跟进与话术", "汇总报告并保存"]; let i = 0; setStage(steps[0]); const timer = window.setInterval(() => { i = Math.min(i + 1, steps.length - 1); setStage(steps[i]); }, 1300); try { const data = await api.analyse({ raw_note: note, customer_name: name, force_mock: mock }); onDone(data.customer); } catch (err) { setError(err.message); } finally { clearInterval(timer); setBusy(false); setStage(""); } };
  return <section className="analysis-layout"><div className="analysis-main"><div className="privacy-banner"><b>数据与隐私提示</b><span>输入内容会发送至当前配置的模型服务用于分析。请勿输入身份证号、银行卡号、完整联系方式、合同密钥等敏感信息。</span></div><div className="form-grid"><label>客户称谓 <small>可选</small><input value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：李总" /></label></div><label className="note-label">客户原始记录<textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="粘贴聊天记录、电话纪要、会议记录或业务备注。无需预先整理；知客会标记事实、推断与待确认项。" /></label><div className="analysis-options"><label className="switch"><input type="checkbox" checked={mock} onChange={(e) => setMock(e.target.checked)} /><span></span>强制使用本地 Mock 模式</label><p>生成过程会显示每一步真实运行来源；模型不可用时结果会明确标记为回退生成。</p></div>{error && <div className="form-error">{error}</div>}<button className="primary generate" disabled={busy} onClick={run}>{busy ? `AI 正在${stage}…` : "生成业务行动方案 →"}</button>{busy && <div className="loading"><i></i><span>{stage}</span><small>正在执行 7 个 Skills，请勿重复提交。</small></div>}</div><aside className="examples"><p className="eyebrow">QUICK START</p><h3>示例案例</h3>{Object.entries(EXAMPLES).map(([label, value]) => <button key={label} onClick={() => setNote(value)}>{label}<span>填充 →</span></button>)}<article><b>输入更轻，持续更容易</b><p>先贴一段原始记录；后续可在客户洞察中补充一句进展，避免每次重复整理。</p></article></aside></section>;
}

function Customers({ customers, selected, onSelect, onFeedback }) {
  const [tab, setTab] = useState("customer_profile");
  const report = selected?.report || {};
  const sections = [["customer_profile", "客户档案"], ["need_analysis", "需求分析"], ["opportunity_assessment", "机会判断"], ["follow_up_plan", "跟进建议"], ["communication_script", "沟通话术"], ["daily_report", "业务日报"]];
  return <section className="customer-layout"><aside className="customer-list"><div className="panel-title"><h3>客户列表</h3><span>{customers.length}</span></div>{customers.map((c) => <button className={selected?.id === c.id ? "customer-item selected" : "customer-item"} onClick={() => onSelect(c.id)} key={c.id}><span className="avatar">{c.name?.slice(0, 1)}</span><div><b>{c.name}</b><p>{c.industry || "待确认"}</p></div><i>{c.priority || "中"}</i></button>)}{!customers.length && <p className="muted">尚未创建客户分析。</p>}</aside><div className="customer-detail">{selected ? <><div className="customer-heading"><div><p className="eyebrow">CUSTOMER INSIGHT</p><h2>{selected.name}</h2><p>{selected.industry || "待确认"} · {selected.stage || "待确认"} · <span className="source-badge">{selected.provider || "已保存报告"}</span></p></div><div className="customer-meta"><b>人工确认后才计入 KPI</b><span>模型推断不会自动视为业务结果</span></div></div><div className="report-tabs">{sections.map(([key, label]) => <button className={tab === key ? "selected" : ""} key={key} onClick={() => setTab(key)}>{label}</button>)}</div><article className="report-card"><div className="report-source"><span>内容来源：AI 分析结果</span><span>发送或决策前请人工确认</span></div><pre>{report[tab] || "该模块暂无内容"}</pre>{tab === "communication_script" && <button className="secondary" onClick={() => navigator.clipboard?.writeText(report[tab] || "")}>复制话术</button>}</article><Feedback customer={selected} onSubmit={onFeedback} /></> : <Empty title="选择一位客户查看洞察" body="完成新建分析后，这里会展示结构化报告、建议与人工反馈。" />}</div></section>;
}

function Feedback({ customer, onSubmit }) {
  const [event, setEvent] = useState("effective_communication"), [note, setNote] = useState(""), [busy, setBusy] = useState(false);
  const submit = async () => { setBusy(true); await onSubmit({ customer_id: customer.id, event_type: event, note }); setNote(""); setBusy(false); };
  return <section className="feedback"><div><p className="eyebrow">HUMAN-CONFIRMED KPI</p><h3>记录一次跟进反馈</h3><p>只有业务员确认的结果会计入 KPI，并保留在当前账户的业务记录中。</p></div><select value={event} onChange={(e) => setEvent(e.target.value)}><option value="effective_communication">已完成一次有效沟通</option><option value="solution_meeting">已完成方案沟通/演示</option><option value="priority_advanced">重点客户已推进</option><option value="need_confirmed">已确认客户需求</option></select><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="说明（可选）" /><button className="primary" disabled={busy} onClick={submit}>{busy ? "保存中…" : "确认并更新 KPI"}</button></section>;
}

function Tasks({ tasks, onRefresh, onCustomer }) { return <section className="panel full-panel"><div className="panel-title"><div><p className="eyebrow">FOLLOW-UP QUEUE</p><h2>智能跟进</h2></div><span>{tasks.length} 项任务</span></div>{tasks.length ? <div className="table"><div className="table-head"><span>客户</span><span>下一步行动</span><span>风险</span><span>状态</span><span></span></div>{tasks.map((t) => <div className="table-row" key={t.id}><button onClick={() => onCustomer(t.customer_id)}>{t.customer_name}</button><span>{t.title}</span><span>{t.risk || "待确认"}</span><select value={t.status} onChange={async (e) => { await api.changeTask(t.id, e.target.value); onRefresh(); }}><option>待办</option><option>已完成</option><option>已延期</option><option>已取消</option></select><button onClick={() => onCustomer(t.customer_id)}>查看 →</button></div>)}</div> : <Empty title="暂无跟进任务" body="客户分析完成后，可以将 AI 生成的建议转为可执行任务。" />}</section> }
function Empty({ title, body, action, onAction }) { return <div className="empty"><b>{title}</b><p>{body}</p>{action && <button className="secondary" onClick={onAction}>{action}</button>}</div> }

createRoot(document.getElementById("root")).render(<App />);
