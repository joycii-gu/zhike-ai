# 知客 ZhiKe AI — Skills（S3W2）

本目录是 S3W1 Specs 中「4. Agent Workflow 设计」与「3. 产品需求设计」对应的 Skills 定义与 W2 运行契约，用于 S3W2 赛段提交。`zhike-ai/src/skills.py` 提供本地 Mock 模式下的顺序执行适配层，`zhike-ai/app.py` 是网页 Prototype 主入口。

## 目录结构与 FR 对应关系

```
zhike-ai/
├── skills/
│   ├── customer_profile/        # FR1 客户信息解析 + FR2 客户档案生成
│   ├── need_analysis/           # FR3 客户需求分析
│   ├── opportunity_judgement/   # FR4 业务机会判断
│   ├── follow_up/               # FR5 跟进建议
│   ├── communication/           # FR6 沟通话术
│   └── daily_report/            # FR7 业务日报
```

`customer_profile` 内部包含"信息解析"与"档案生成"两个步骤（对应 Specs 中的两个独立 Agent），因为二者输入输出强耦合、总是连续执行，合并为一个 Skill 目录管理更符合实际调用方式；其余 5 个 Skill 与 FR3–FR7 一一对应。

## Workflow 调用顺序

```
customer_profile → need_analysis → opportunity_judgement → follow_up → communication
                                                                    ↘
                                                              daily_report（多客户跨天汇总，最后单独触发）
```

每个 SKILL.md 内的"输入"章节都明确写了它依赖哪个上游 Skill 的输出，可以按此顺序串联成完整 Workflow；也可以单独拿某一个 Skill 出来单测，定位问题。

## 每个 SKILL.md 包含什么

- **定位**：这个 Skill 在整体 Workflow 里解决什么问题；
- **核心规则**：对应 Specs 验收标准里"不能做什么"（如不能虚构预算、不能因客户感兴趣就判高意向等）；
- **输入 / 输出 JSON 结构**：可直接被程序解析，用于串联下一个 Skill；
- **验收标准**：直接引用 Specs §7 对应指标的合格标准，便于测试时逐项打分；
- **示例**：完整的输入→输出示例，可直接用于验证 Skill 是否跑通。

## 如何验证

1. 任选一个 SKILL.md，把其中的规则和 JSON 结构作为 system prompt，把"示例"里的输入喂给任意 LLM，检查输出是否符合该 Skill 的"验收标准"表格；
2. 按 Workflow 调用顺序把 6 个 Skill 串起来，用 Specs §7.10 建议的 3 个不同行业客户样例整体跑一遍，按 §7 的 100 分制评分表打分；
3. 也可参考仓库内的 `prototype/` HTML 文件了解界面交互设计；W2 实际可运行入口是 `app.py`，前端不直接持有模型 API Key。

## W2 运行对应关系

```text
app.py
  → src/agent.py
    → MockProvider
      → src/skills.py
        → customer_profile → need_analysis → opportunity_judgement
          → follow_up → communication → daily_report
```

真实模型或 HermesAgent 可以在后续通过 `BusinessAgentProvider` 接口替换，不改变网页层和公开报告结构。
