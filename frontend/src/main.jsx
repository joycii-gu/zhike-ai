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
  const chooseCustomer = async (id) => {
    if (!id) { notify("该任务没有关联到有效客户，无法打开客户洞察。"); return; }
    try {
      setSelected(await api.customer(id));
      setPage("customers");
    } catch (err) {
      notify(err.message || "打开客户洞察失败，请稍后重试。");
    }
  };
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><b>知客</b><span>ZhiKe AI</span><small>AI Business Assistant</small></div>
      <nav>{NAV.map(([key, icon, label]) => <button key={key} className={page === key ? "nav active" : "nav"} onClick={() => setPage(key)}><i>{icon}</i>{label}</button>)}</nav>
      <div className="sidebar-foot"><span className="avatar">知</span><div><b>我的业务空间</b><small>数据仅归属当前账号</small></div><button className="logout" onClick={() => api.logout().then(() => setSession(null))}>退出</button></div>
    </aside>
    <main className="main"><header className="topbar"><div><p className="eyebrow">AI BUSINESS COMMAND CENTER</p><h1>{page === "dashboard" ? "今日业务驾驶舱" : page === "analysis" ? "新建客户分析" : page === "customers" ? "客户洞察" : "智能跟进"}</h1></div><div className="runtime"><span className={health?.api_configured ? "dot online" : "dot"}></span>{health?.runtime || "正在检查 Agent Runtime"}</div></header>
      {page === "dashboard" && <Dashboard dashboard={dashboard} tasks={tasks} customers={customers} onCreate={() => setPage("analysis")} onCustomer={chooseCustomer} />}
      {page === "analysis" && <Analysis customers={customers} onDone={async (customer) => { await refresh(); setSelected(customer); setPage("customers"); notify("分析完成，已保存到客户洞察"); }} />}
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
  const activeTasks = tasks.filter((task) => task.status === "待办" || task.status === "已延期");
  const highRiskCustomers = customers.filter((customer) => customer.priority === "高");
  const kpis = [
    ["有效沟通", dashboard?.effective_communications || 0],
    ["方案沟通", dashboard?.solution_meetings || 0],
    ["重点客户推进", dashboard?.priority_advanced || 0],
  ];
  const firstTask = activeTasks[0];
  return <>
    <section className="hero"><div><p className="eyebrow">TODAY · FOCUS · ACTION</p><h2>今天，先推进<br/>最重要的客户。</h2><p>一次沟通后只记录关键变化；知客把它转成待确认的下一步，让业务员把时间留给客户。</p><button className="primary" onClick={onCreate}>＋ 快速记录本次进展</button></div><div className="hero-agent"><b><span className="dot online"/> Agent Status</b><p>{activeTasks.length} 项待推进动作</p><p>{highRiskCustomers.length} 位重点风险客户</p><p>结果仅在人工确认后写入任务与 KPI</p></div></section>
    <section className="focus-grid">
      <article className="focus-card"><span>01 · 现在该做什么</span><b>{firstTask?.customer_name || "先记录一次刚结束的沟通"}</b><p>{firstTask?.title || "用一句话记录电话、微信或会议中的关键变化。"}</p>{firstTask ? <button onClick={() => onCustomer(firstTask.customer_id)}>查看行动 →</button> : <button onClick={onCreate}>快速记录 →</button>}</article>
      <article className="focus-card"><span>02 · 需要留意什么</span><b>{highRiskCustomers.length ? `${highRiskCustomers.length} 位客户需要优先关注` : "暂无高优先级风险"}</b><p>{highRiskCustomers[0]?.risk || "客户风险会在 AI 分析与人工确认后显示在这里。"}</p></article>
      <article className="focus-card"><span>03 · 避免遗漏什么</span><b>{activeTasks.length ? `${activeTasks.length} 项行动尚未完成` : "当前没有遗留待办"}</b><p>知客不会自动替你发送或计入业绩，所有行动都等待你的确认。</p></article>
    </section>
    <section className="workspace-grid"><article className="panel actions"><div className="panel-title"><div><p className="eyebrow">AI RECOMMENDED</p><h3>今日优先行动</h3><p className="panel-subtitle">基于最新客户进展生成；任务只有在人工确认后才会出现。</p></div><button onClick={onCreate}>快速记录 →</button></div>{activeTasks.slice(0, 5).map((task) => <div className="task-row" key={task.id}><span className="priority">{task.priority || "中"}</span><div><b>{task.customer_name}</b><p>{task.title}</p></div><span className="task-status">{task.status}</span><button onClick={() => onCustomer(task.customer_id)}>查看 →</button></div>)}{!activeTasks.length && <Empty title="还没有待办行动" body="记录一位客户的最新进展，知客会先生成待确认的下一步。" action="快速记录进展" onAction={onCreate} />}</article><aside className="side-panels"><article className="panel"><div className="panel-title"><h3>风险提醒</h3><span>TOP RISKS</span></div>{customers.slice(0, 4).map((c) => <button className="risk-row" key={c.id} onClick={() => onCustomer(c.id)}><i className={c.priority === "高" ? "risk high" : "risk"}></i><div><b>{c.name}</b><p>{c.risk || "待确认关键业务信息"}</p></div><span>{c.priority || "中"}</span></button>)}{!customers.length && <p className="muted">暂无客户风险信息</p>}</article><article className="panel"><div className="panel-title"><div><h3>个人行动进度</h3><p className="panel-subtitle">仅统计人工确认的真实结果</p></div><span>SESSION KPI</span></div>{kpis.map(([label, value]) => <div className="compact-progress" key={label}><span>{label}</span><b>{value}</b><i><em style={{ width: `${Math.min(100, Number(value) * 20)}%` }} /></i></div>)}</article></aside></section>
  </>;
}

function Analysis({ onDone, customers = [] }) {
  const [note, setNote] = useState(""), [name, setName] = useState(""), [customerId, setCustomerId] = useState(""), [mock, setMock] = useState(false), [busy, setBusy] = useState(false), [stage, setStage] = useState(""), [error, setError] = useState(""), [mode, setMode] = useState("quick"), [captureResult, setCaptureResult] = useState(null), [confirming, setConfirming] = useState(false), [scriptCopied, setScriptCopied] = useState(false);
  const run = async () => {
    const minimum = mode === "quick" ? 2 : 8;
    if (note.trim().length < minimum) return setError(mode === "quick" ? "请写下一句本次业务进展" : "请至少输入 8 个字符的客户记录");
    setBusy(true); setError(""); setCaptureResult(null); setScriptCopied(false);
    const steps = mode === "quick" ? ["识别本次沟通变化", "结合客户上下文判断优先级", "生成待确认的下一步行动"] : ["提取客户关键信息", "分析需求与机会", "生成跟进与话术", "汇总报告并保存"];
    let i = 0; setStage(steps[0]); const timer = window.setInterval(() => { i = Math.min(i + 1, steps.length - 1); setStage(steps[i]); }, 1100);
    try {
      if (mode === "quick") {
        const data = await api.capture({ capture: note, customer_id: customerId, customer_name: name, force_mock: mock });
        setCaptureResult(data);
      } else {
        const data = await api.analyse({ raw_note: note, customer_name: name, force_mock: mock });
        onDone(data.customer);
      }
    } catch (err) { setError(err.message); } finally { clearInterval(timer); setBusy(false); setStage(""); }
  };
  const confirmDraft = async () => {
    if (!captureResult?.action_draft) return;
    setConfirming(true); setError("");
    try { await api.confirmActionDraft(captureResult.action_draft.id); onDone(captureResult.customer); }
    catch (err) { setError(err.message); } finally { setConfirming(false); }
  };
  const dismissDraft = async () => {
    if (!captureResult?.action_draft) return;
    try { await api.dismissActionDraft(captureResult.action_draft.id); setCaptureResult(null); setNote(""); }
    catch (err) { setError(err.message); }
  };
  const copyScript = async () => {
    const script = captureResult?.customer?.report?.communication_script || captureResult?.report?.communication_script;
    if (!script) { setError("本次分析暂未生成可复制的话术，请查看完整分析结果。"); return; }
    try {
      await copyToClipboard(plainText(script));
      setError(""); setScriptCopied(true);
      window.setTimeout(() => setScriptCopied(false), 1800);
    } catch { setError("浏览器未能自动复制，请手动选择话术内容复制。"); }
  };
  return <section className="analysis-layout"><div className="analysis-main"><div className="capture-intro"><p className="eyebrow">AI ACTION INBOX</p><h2>少录入，直接得到下一步</h2><p>完成一次电话、微信或会议后，只记下关键变化。知客会生成可确认的待办、风险提醒和后续行动。</p></div><div className="mode-switch"><button className={mode === "quick" ? "selected" : ""} onClick={() => { setMode("quick"); setError(""); }}>快速记录 <span>推荐</span></button><button className={mode === "deep" ? "selected" : ""} onClick={() => { setMode("deep"); setError(""); }}>深度分析</button></div><div className="privacy-banner"><b>数据与隐私提示</b><span>输入内容会发送至当前配置的模型服务用于分析。请勿输入身份证号、银行卡号、完整联系方式、合同密钥等敏感信息。</span></div>{captureResult ? <article className="action-confirm-card"><p className="eyebrow">AI ACTION DRAFT · 待人工确认</p><h3>已识别本次进展，建议你现在做这一步</h3><div className="action-confirm-main"><div><span>客户</span><b>{captureResult.customer?.name}</b></div><div><span>建议行动</span><b>{captureResult.action_draft?.title}</b></div><div><span>风险提示</span><b>{captureResult.action_draft?.risk || "待确认"}</b></div></div><p className="action-reason">{captureResult.action_draft?.reason}</p><div className="action-confirm-buttons"><button className="primary" disabled={confirming} onClick={confirmDraft}>{confirming ? "确认中…" : "确认并创建待办"}</button><button className="secondary" onClick={copyScript}>{scriptCopied ? "✓ 已复制话术" : "复制沟通话术"}</button><button className="secondary" onClick={dismissDraft}>暂不创建</button></div><small>这是一项 AI 建议。只有你确认后才会写入任务列表；不会自动发送消息或计入 KPI。</small></article> : <><div className="form-grid">{mode === "quick" && <label>关联已有客户 <small>可选；选中后自动写回该客户</small><select value={customerId} onChange={(e) => { setCustomerId(e.target.value); if (e.target.value) setName(""); }}><option value="">新客户或暂不关联</option>{customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name} · {customer.industry || "待确认"}</option>)}</select></label>}<label>客户称谓 <small>可选</small><input disabled={Boolean(customerId)} value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：李总；留空则由知客识别" /></label></div><label className="note-label">{mode === "quick" ? "本次发生了什么？" : "客户原始记录"}<textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder={mode === "quick" ? "例如：李总刚确认下周三下午可以演示，但希望先看到数据安全说明；预算仍待确认。" : "粘贴聊天记录、电话纪要、会议记录或业务备注。无需预先整理；知客会标记事实、推断与待确认项。"} /></label><p className="input-helper">{mode === "quick" ? "只需一句进展，不必重复粘贴整段聊天记录。" : "适合首次建立客户档案或需要重新完整判断时使用。"}</p><div className="analysis-options"><label className="switch"><input type="checkbox" checked={mock} onChange={(e) => setMock(e.target.checked)} /><span></span>强制使用本地 Mock 模式</label><p>模型不可用时，结果会明确标记为回退生成。</p></div>{error && <div className="form-error">{error}</div>}<button className="primary generate" disabled={busy} onClick={run}>{busy ? `AI 正在${stage}…` : mode === "quick" ? "生成下一步行动 →" : "生成完整业务分析 →"}</button>{busy && <div className="loading"><i></i><span>{stage}</span><small>正在执行必要的业务 Skills，请勿重复提交。</small></div>}</>}</div><aside className="examples"><p className="eyebrow">QUICK START</p><h3>快速体验</h3>{Object.entries(EXAMPLES).map(([label, value]) => <button key={label} onClick={() => { setMode("deep"); setNote(value); }}>{label}<span>填充 →</span></button>)}<article><b>不把 AI 建议当成已完成业绩</b><p>知客负责整理与建议；发送、跟进和 KPI 只由业务员的人工确认结果驱动。</p></article></aside></section>;
}

const REPORT_META = {
  customer_profile: ["客户档案", "把分散信息整理为一眼可读的客户画像"],
  need_analysis: ["客户需求分析", "区分客户明确表达、AI 推断与待确认事项"],
  opportunity_assessment: ["业务机会判断", "基于已有信号给出审慎的优先级参考"],
  follow_up_plan: ["下一步行动", "将分析转为业务员可以执行的具体动作"],
  communication_script: ["沟通话术", "发送前请结合真实情况编辑并人工确认"],
  daily_report: ["业务日报", "汇总当前会话中的客户行动与风险事项"]
};

function plainText(value = "") {
  return String(value).replace(/\*\*/g, "").replace(/`/g, "").replace(/<br\s*\/?>/gi, "\n").trim();
}

async function copyToClipboard(value) {
  const text = String(value || "").trim();
  if (!text) throw new Error("没有可复制的内容");
  // Clipboard API needs HTTPS in most browsers.  ECS may be accessed through
  // an HTTP address during the competition, so retain a user-gesture fallback.
  if (navigator.clipboard?.writeText && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.cssText = "position:fixed;left:-9999px;top:0;opacity:0;";
  document.body.appendChild(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("浏览器未授予复制权限");
}

function parseReport(content) {
  const blocks = [];
  let current = { title: "", level: 0, fields: [], bullets: [], paragraphs: [], tables: [] };
  const flush = () => {
    if (current.title || current.fields.length || current.bullets.length || current.paragraphs.length || current.tables.length) blocks.push(current);
  };
  const lines = String(content || "").replace(/\r/g, "").split("\n");
  const tableCells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((cell) => plainText(cell).trim());
  const isTableLine = (line) => /^\s*\|.+\|\s*$/.test(line);
  for (let cursor = 0; cursor < lines.length; cursor += 1) {
    const raw = lines[cursor];
    const line = raw.trim();
    if (!line) continue;
    if (isTableLine(line)) {
      const tableLines = [];
      while (cursor < lines.length && isTableLine(lines[cursor])) {
        tableLines.push(lines[cursor]);
        cursor += 1;
      }
      cursor -= 1;
      const header = tableCells(tableLines[0]);
      const bodyLines = tableLines.slice(1).filter((row) => !/^\s*\|?\s*:?-{3,}/.test(row));
      const rows = bodyLines.map(tableCells).filter((row) => row.some(Boolean));
      if (header.length && rows.length) current.tables.push({ header, rows });
      else current.paragraphs.push(...tableLines.map((row) => plainText(row)));
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flush();
      current = { title: plainText(heading[2]), level: heading[1].length, fields: [], bullets: [], paragraphs: [], tables: [] };
      continue;
    }
    const list = line.match(/^[-*]\s+(.+)$/);
    const candidate = plainText(list ? list[1] : line);
    const field = candidate.match(/^([^：:]{1,24})[：:]\s*(.+)$/);
    if (field) current.fields.push({ label: field[1].trim(), value: field[2].trim() });
    else if (list) current.bullets.push(candidate);
    else current.paragraphs.push(candidate);
  }
  flush();
  return blocks;
}

function valueTone(value) {
  if (/高风险|高优先|优先级.?高|\b高\b/.test(value)) return "danger";
  if (/中风险|中高|待确认|未知/.test(value)) return "warning";
  if (/低风险|已完成|可推进|正常/.test(value)) return "success";
  return "neutral";
}

function ReportView({ section, content }) {
  const [copied, setCopied] = useState(false);
  const [title, description] = REPORT_META[section] || ["分析结果", "AI 生成内容"];
  const blocks = parseReport(content);
  const copy = async () => {
    try { await copyToClipboard(plainText(content)); setCopied(true); setTimeout(() => setCopied(false), 1800); }
    catch { setCopied(false); }
  };
  if (!content) return <Empty title="该模块暂无内容" body="完成一次分析后，知客会在这里展示可供人工确认的结果。" />;
  return <div className={`report-view report-${section}`}>
    <div className="report-overview"><div><p className="eyebrow">AI-ORGANIZED RESULT</p><h3>{title}</h3><span>{description}</span></div>{section === "communication_script" && <button className="secondary report-copy" onClick={copy}>{copied ? "已复制" : "复制话术"}</button>}</div>
    <div className="report-blocks">{blocks.map((block, index) => <article className={`report-block level-${block.level || 3}`} key={`${block.title}-${index}`}>
      {block.title && <h4>{block.title}</h4>}
      {block.fields.length > 0 && <dl className="report-fields">{block.fields.map((field, fieldIndex) => <div className="report-field" key={`${field.label}-${fieldIndex}`}><dt>{field.label}</dt><dd className={valueTone(field.value)}>{field.value}</dd></div>)}</dl>}
      {block.paragraphs.map((paragraph, paragraphIndex) => <p className="report-paragraph" key={paragraphIndex}>{paragraph}</p>)}
      {block.tables.map((table, tableIndex) => <div className="report-table-wrap" key={tableIndex}><table className="report-table"><thead><tr>{table.header.map((cell, cellIndex) => <th key={cellIndex}>{cell}</th>)}</tr></thead><tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>{table.header.map((_, cellIndex) => <td key={cellIndex}>{row[cellIndex] || "—"}</td>)}</tr>)}</tbody></table></div>)}
      {block.bullets.length > 0 && <ul className="report-list">{block.bullets.map((bullet, bulletIndex) => <li key={bulletIndex}>{bullet}</li>)}</ul>}
    </article>)}</div>
  </div>;
}

function Customers({ customers, selected, onSelect, onFeedback }) {
  const [tab, setTab] = useState("follow_up_plan");
  const report = selected?.report || {};
  const sections = [["customer_profile", "客户档案"], ["need_analysis", "需求分析"], ["opportunity_assessment", "机会判断"], ["follow_up_plan", "跟进建议"], ["communication_script", "沟通话术"], ["daily_report", "业务日报"]];
  return <section className="customer-layout"><aside className="customer-list"><div className="panel-title"><h3>客户列表</h3><span>{customers.length}</span></div>{customers.map((c) => <button className={selected?.id === c.id ? "customer-item selected" : "customer-item"} onClick={() => onSelect(c.id)} key={c.id}><span className="avatar">{c.name?.slice(0, 1)}</span><div><b>{c.name}</b><p>{c.industry || "待确认"}</p></div><i>{c.priority || "中"}</i></button>)}{!customers.length && <p className="muted">尚未创建客户分析。</p>}</aside><div className="customer-detail">{selected ? <><div className="customer-heading"><div><p className="eyebrow">CUSTOMER INSIGHT</p><h2>{selected.name}</h2><p>{selected.industry || "待确认"} · {selected.stage || "待确认"} · <span className="source-badge">{selected.provider || "已保存报告"}</span></p></div><div className="customer-meta"><b>人工确认后才计入 KPI</b><span>模型推断不会自动视为业务结果</span></div></div><div className="report-tabs">{sections.map(([key, label]) => <button className={tab === key ? "selected" : ""} key={key} onClick={() => setTab(key)}>{label}</button>)}</div><article className="report-card"><div className="report-source"><span>内容来源：AI 分析结果</span><span>发送或决策前请人工确认</span></div><ReportView section={tab} content={report[tab]} /></article><Feedback customer={selected} onSubmit={onFeedback} /></> : <Empty title="选择一位客户查看洞察" body="完成新建分析后，这里会展示结构化报告、建议与人工反馈。" />}</div></section>;
}

function Feedback({ customer, onSubmit }) {
  const [event, setEvent] = useState("effective_communication"), [note, setNote] = useState(""), [busy, setBusy] = useState(false);
  const submit = async () => { setBusy(true); await onSubmit({ customer_id: customer.id, event_type: event, note }); setNote(""); setBusy(false); };
  return <section className="feedback"><div><p className="eyebrow">HUMAN-CONFIRMED KPI</p><h3>记录一次跟进反馈</h3><p>只有业务员确认的结果会计入 KPI，并保留在当前账户的业务记录中。</p></div><select value={event} onChange={(e) => setEvent(e.target.value)}><option value="effective_communication">已完成一次有效沟通</option><option value="solution_meeting">已完成方案沟通/演示</option><option value="priority_advanced">重点客户已推进</option><option value="need_confirmed">已确认客户需求</option></select><input value={note} onChange={(e) => setNote(e.target.value)} placeholder="说明（可选）" /><button className="primary" disabled={busy} onClick={submit}>{busy ? "保存中…" : "确认并更新 KPI"}</button></section>;
}

function Tasks({ tasks, onRefresh, onCustomer }) { return <section className="panel full-panel"><div className="panel-title"><div><p className="eyebrow">FOLLOW-UP QUEUE</p><h2>智能跟进</h2></div><span>{tasks.length} 项任务</span></div>{tasks.length ? <div className="table"><div className="table-head"><span>客户</span><span>下一步行动</span><span>风险</span><span>状态</span><span></span></div>{tasks.map((t) => <div className="table-row" key={t.id}><button onClick={() => onCustomer(t.customer_id)}>{t.customer_name}</button><span>{t.title}</span><span>{t.risk || "待确认"}</span><select value={t.status} onChange={async (e) => { await api.changeTask(t.id, e.target.value); onRefresh(); }}><option>待办</option><option>已完成</option><option>已延期</option><option>已取消</option></select><button onClick={() => onCustomer(t.customer_id)}>查看 →</button></div>)}</div> : <Empty title="暂无跟进任务" body="客户分析完成后，可以将 AI 生成的建议转为可执行任务。" />}</section> }
function Empty({ title, body, action, onAction }) { return <div className="empty"><b>{title}</b><p>{body}</p>{action && <button className="secondary" onClick={onAction}>{action}</button>}</div> }

createRoot(document.getElementById("root")).render(<App />);
