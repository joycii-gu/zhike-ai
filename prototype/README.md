# Prototype 参考界面

`zhike_prototype.html` 是知客 ZhiKe AI 的交互与视觉参考原型，来源于 S3W2 Skills 设计稿。

## 重要边界

- W2 的主运行入口是项目根目录的 `app.py`（Streamlit Demo）。
- 本 HTML 文件不作为 W2 的唯一运行入口，也不替代 Streamlit Demo。
- 文件中的浏览器端 API 调用仅用于展示前端交互思路，提交前不得在其中写入真实 API Key。
- 如需启用真实模型，应将 API 调用迁移到后端 Provider，并通过环境变量管理密钥。

## 与主 Prototype 的关系

HTML 原型保留了工作流步骤、示例案例、Skill 卡片和业务日报的交互思路；实际可运行的 W2 版本由 `app.py` 调用 `src/agent.py`，Mock 模式通过 `src/skills.py` 按 Skills 顺序执行。
