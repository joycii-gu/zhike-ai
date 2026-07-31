# 知客 ZhiKe AI — Skills（S3W3）

本目录提供知客 ZhiKe AI 在 S3W3 半决赛中使用的 Skills 交付说明。W3 将 W2 已验证的客户处理能力整合为可交互 Agent：网页负责收集业务目标、客户记录和人工确认的跟进反馈；Agent Runtime 依次调度 Skills；KPI 层只对人工确认事件进行确定性计算。

本目录不是一组可随意拼接的长 Prompt。每个 Skill 都定义了职责、输入、输出、事实边界和验收规则，可单独检查，也可按既定顺序构成完整业务链。

## 目录与运行时步骤对应关系

```text
zhike-ai/
├── skills/
│   ├── customer_info_parse/       # Skill 1：客户信息解析
│   ├── customer_profile/          # Skill 2：客户档案生成
│   ├── need_analysis/             # Skill 3：客户需求分析
│   ├── opportunity_judgement/     # Skill 4：业务机会判断
│   ├── follow_up/                 # Skill 5：跟进建议
│   ├── communication/             # Skill 6：沟通话术
│   └── daily_report/              # Skill 7：业务日报
```

| 顺序 | Skill | 主要输入 | 主要输出 |
|---:|---|---|---|
| 1 | 客户信息解析 | 原始客户记录 | 事实、推断、未知和证据片段 |
| 2 | 客户档案生成 | 解析结果 | 统一、可浏览的客户档案 |
| 3 | 客户需求分析 | 档案与证据 | 显性需求、潜在痛点、待确认问题 |
| 4 | 业务机会判断 | 需求分析与信号 | 机会等级、依据、风险 |
| 5 | 跟进建议 | 档案、需求、机会判断 | 动作、时点、目标与材料 |
| 6 | 沟通话术 | 关注点、渠道、跟进目标 | 可编辑沟通参考话术 |
| 7 | 业务日报 | 当前客户结果与演示 Mock 集合 | 跨客户待办、排序和风险汇总 |

## W3 运行方式

```text
app.py
  → src/agent.py（Provider 选择：MiniMax API / Mock）
    → src/workflow.py（链式调度、上下文剪裁、字段校验、执行轨迹）
      → 7 个 Skills 依次执行
        → src/kpi_agent.py（人工反馈驱动的 KPI 与行动层）
```

在 API 模式下，前一个 Skill 的结构化输出会被压缩为后一个 Skill 必需的上下文；后续步骤不会反复读取全部原始记录。若某一步模型返回异常或格式不符合约束，系统仅对该步骤启用本地安全回退，并在页面执行轨迹中标记 `fallback`，避免整份报告不可用。

Mock 模式用于离线演示与回归测试；MiniMax API 模式用于真实模型生成。两种模式都遵守相同的输出结构和事实边界。Mock 客户仅服务于业务日报的跨客户演示，不代表数据库或历史客户管理。

## 验证方式

```bash
python tests/test_workflow.py
python tests/test_kpi_agent.py
```

评审可使用 `docs/04_demo_case.md` 的三个案例运行网页 Demo，并按 `docs/10_w3_evaluation.md` 评分。已执行的本地测试与待补充的 API 验收记录见 `docs/11_w3_test_evidence.md`。

## 事实边界

- 原文明确出现的信息标为事实；基于上下文的判断标为推断；缺失信息标为未知或待确认。
- 不虚构预算、决策权限、成交概率、产品效果或未验证承诺。
- KPI 不由模型文本自动计数，只由业务员确认的跟进事件改变。
- 话术与机会判断均为辅助建议，最终发送和业务决策由人工确认。
