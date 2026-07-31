# 知客 ZhiKe AI

## 面向业务员的目标驱动型 AI 业务处理智能体

> 滴水湖全球 OPC 人工智能挑战赛 · S3 全球青年培育赛 · W3 半决赛 · X创新赛道

知客 ZhiKe AI 面向销售人员、客户经理、课程顾问、企业服务顾问及其他顾问型业务人员。它将客户备注、聊天摘要、电话纪要等非结构化信息转化为客户档案、需求分析、机会判断、跟进建议、沟通话术和业务日报，并在 W3 阶段加入“业务目标—跟进反馈—KPI 进度—下一步行动”的会话内闭环。

知客不是开放式聊天机器人，也不是以存储数据为主的传统 CRM。它将资深业务人员的客户理解和行动规划方法拆解为可运行、可评测的 Skills 工作流；KPI 数据只来自业务员确认的反馈事件，不由模型自行编造。

## 核心 Agent 闭环

**客户信息输入 → 客户档案 → 需求分析 → 机会判断 → 跟进建议 → 沟通话术 → 业务日报 → 跟进反馈 → KPI 与行动调整**

- **客户处理链：** 将原始记录整理为可核查的业务报告，区分事实、推断和未知。
- **反馈状态层：** 业务员确认“有效沟通、需求确认、完成演示、重点客户推进”等事件。
- **KPI 行动层：** 基于已确认事件计算进度、识别风险，并形成当前会话内的优先行动队列。

## W3 Agent Demo

当前网页 Demo 用于演示一个可交付、可交互的业务 Agent，而非完整商业系统。

1. 设定本周或本月的业务目标；
2. 粘贴客户信息，生成 7 个 Skills 的业务处理报告；
3. 在“🎯 KPI 与行动”页记录业务员确认的跟进结果；
4. 查看 KPI 进度、节奏风险与今日优先行动。

在线演示：<https://zhike-ai-demo.streamlit.app/>

### 数据与能力边界

- KPI 仅统计当前浏览器会话中、由业务员确认的反馈；AI 输出不等同于已达成业绩。
- 当前版本不使用数据库，不提供跨会话持久化、登录、多用户权限或真实 CRM/微信/日历接入。
- W2 的 Mock 客户仍仅用于跨客户日报演示；W3 的客户状态和 KPI 是独立的会话内演示数据。
- 话术、机会判断和业务建议均供人工参考，最终发送与决策由业务员确认。

## 快速开始

```bash
cd zhike-ai
pip install -r requirements.txt
streamlit run app.py
```

W3 默认使用 W2 获奖算力 SynScale 生成业务报告；如同时配置 SynScale 与 MiniMax，系统优先选择 SynScale，MiniMax 作为备用 Provider。未配置任何模型密钥或开启“强制使用 Mock 演示模式”时，系统使用本地 Mock Skills Workflow，便于稳定演示和回归测试。

本地 API 配置示例（不要将真实密钥提交到仓库）：

```text
SYNSCALE_API_KEY=sk-syn-your_key
SYNSCALE_BASE_URL=http://synscale.onesyn.ai/v1
SYNSCALE_MODEL=deepseek-v4-pro
```

部署到 Streamlit Community Cloud 时，将同名字段写入 **App Settings → Secrets**。可选 MiniMax 备用配置见 `.env.example`；不要将真实密钥提交到仓库。

## 项目结构

```text
zhike-ai/
├── app.py                         # Streamlit W3 Agent Demo
├── README.md
├── README_EN.md
├── requirements.txt
├── skills/                        # 可评审的业务 Skills 定义
├── src/
│   ├── agent.py                   # 模型 Provider 与报告容错层
│   ├── workflow.py                # W3 七步链式 Skills 调度与执行轨迹
│   ├── skills.py                  # W2 本地 Skills pipeline / Mock 回退
│   ├── kpi_agent.py               # W3 确定性 KPI 与会话行动层
│   ├── prompt.py
│   ├── schema.py
│   └── mock_customers.py
├── tests/
│   ├── test_workflow.py           # W3 Skills 调度与容错测试
│   └── test_kpi_agent.py          # W3 KPI 回归测试
├── docs/
│   ├── 01_project_specs.md
│   ├── 02_skills_workflow.md
│   ├── 03_prototype_usage.md
│   ├── 04_demo_case.md
│   ├── 05_evaluation.md
│   ├── 06_roadmap.md
│   ├── 07_w3_agent_design.md
│   ├── 08_kpi_framework.md
│   ├── 09_w3_demo_script.md
│   └── 10_w3_evaluation.md
└── prototype/                     # W2 交互参考页面
```

## 验证方式

```bash
python tests/test_kpi_agent.py
python tests/test_workflow.py
```

该测试验证：重复生成同一客户不会重复计数；只有业务员确认的反馈才会更新 KPI；KPI 层不依赖真实模型调用。

## 文档

- [项目提案 / Project Specs](docs/01_project_specs.md)
- [核心 Skills / Workflow](docs/02_skills_workflow.md)
- [W3 Agent 设计](docs/07_w3_agent_design.md)
- [KPI 框架](docs/08_kpi_framework.md)
- [W3 Demo 演示脚本](docs/09_w3_demo_script.md)
- [W3 评测标准](docs/10_w3_evaluation.md)
- [W3 测试证据](docs/11_w3_test_evidence.md)
- [English README](README_EN.md)

## 赛事信息

- **当前赛段：** S3 全球青年培育赛 · W3 半决赛
- **参赛赛道：** X创新赛道
- **W3 阶段任务：** 提交整合 Skills、可交付且可演示的智能体（Agent），展示交互方式与用户价值。
- **W2 冻结基线：** Git tag `w2-final`，保留 W2 复赛完成时的原型版本。
