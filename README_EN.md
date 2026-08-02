# ZhiKe AI

## A Goal-Driven AI Business Agent for Salespeople and Client-facing Professionals

> Dishui Lake Global OPC AI Challenge · S3 Global Youth Development Program · W3 Semifinal · X Innovation Track

ZhiKe AI helps salespeople, client managers, course consultants, business service consultants, and other client-facing professionals turn raw customer records into structured profiles, need analysis, opportunity assessment, follow-up plans, communication scripts, and daily business reports. In W3, it adds an in-session loop of **business goals → confirmed follow-up feedback → KPI progress → next actions**.

ZhiKe AI is neither a generic chatbot nor a data-storage-first CRM. It operationalizes customer-understanding and action-planning methods as an evaluable Skills workflow. KPI progress is driven only by user-confirmed business events; the model is not allowed to invent achieved results.

## Core Agent Loop

**Customer Input → Customer Profile → Need Analysis → Opportunity Assessment → Follow-up Plan → Communication Script → Daily Business Report → Follow-up Feedback → KPI and Action Adjustment**

- **Customer processing:** Converts unstructured notes into traceable business outputs while separating facts, inferences, and unknowns.
- **Feedback state:** The user confirms events such as an effective conversation, need confirmation, completed demo, or priority-customer advancement.
- **KPI action layer:** Calculates progress from confirmed events, flags execution risks, and maintains an in-session priority action queue.

## W3 Agent Demo

The current Streamlit application demonstrates a deliverable, interactive business Agent. It is not presented as a complete commercial system.

1. Set weekly or monthly business goals.
2. Paste customer notes and generate a seven-Skills business report.
3. Record a user-confirmed follow-up result in the **KPI & Actions** tab.
4. Review KPI progress, pace risks, and today's priority actions.

Live demo: <https://zhike-ai-demo.streamlit.app/>

### Scope and Data Boundaries

- KPI metrics only count feedback confirmed by the user in the current browser session. AI suggestions are never treated as achieved performance.
- This version has no database, cross-session persistence, accounts, multi-user permissions, or live CRM, WeChat, or calendar integration.
- W2 mock customers remain limited to the cross-customer daily-report demonstration. W3 customer state and KPI data are separate, in-session demo data.
- Scripts, opportunity assessments, and business recommendations remain subject to human review and final decision-making.

## Quick Start

```bash
cd zhike-ai
pip install -r requirements.txt
streamlit run app.py
```

W3 uses MiniMax as its default provider for report generation. When both MiniMax and SynScale are configured, MiniMax takes precedence and SynScale remains an optional fallback provider. Without a model key, or with **Force Mock Mode** enabled, the app runs the local Mock Skills Workflow for stable demonstrations and regression tests.

Local API configuration example. Never commit a real key to the repository:

```text
MINIMAX_API_KEY=your_minimax_key
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_MODEL=MiniMax-M2.7
```

For Streamlit Community Cloud, add the same fields in **App Settings → Secrets**. Optional SynScale fallback fields are listed in `.env.example`; never commit a real key.

## Project Structure

```text
zhike-ai/
├── app.py                         # Streamlit W3 Agent Demo
├── README.md
├── README_EN.md
├── requirements.txt
├── skills/                        # Reviewable business Skill definitions
├── src/
│   ├── agent.py                   # Model providers and report fallback layer
│   ├── workflow.py                # W3 seven-step Skills orchestration and trace
│   ├── skills.py                  # W2 local Skills pipeline / Mock fallback
│   ├── kpi_agent.py               # W3 deterministic KPI and session action layer
│   ├── prompt.py
│   ├── schema.py
│   └── mock_customers.py
├── tests/
│   ├── test_workflow.py           # W3 Skills orchestration and fallback tests
│   └── test_kpi_agent.py          # W3 KPI regression tests
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
│   ├── 10_w3_evaluation.md
│   └── 11_w3_test_evidence.md
└── prototype/                     # W2 reference interaction page
```

## Verification

```bash
python tests/test_kpi_agent.py
python tests/test_workflow.py
```

The regression tests confirm that repeated generation does not duplicate a customer, only user-confirmed feedback changes KPI values, and the KPI layer does not require an external model call.

## Documents

- [Project Specs](docs/01_project_specs.md)
- [Core Skills / Workflow](docs/02_skills_workflow.md)
- [W3 Agent Design](docs/07_w3_agent_design.md)
- [KPI Framework](docs/08_kpi_framework.md)
- [W3 Demo Script](docs/09_w3_demo_script.md)
- [W3 Evaluation](docs/10_w3_evaluation.md)
- [W3 Test Evidence](docs/11_w3_test_evidence.md)
- [Chinese README](README.md)

## Competition Information

- **Current stage:** S3 Global Youth Development Program · W3 Semifinal
- **Track:** X Innovation Track
- **W3 task:** Deliver a runnable Agent that integrates Skills and demonstrates interaction and user value.
- **Frozen W2 baseline:** Git tag `w2-final`, preserving the W2 prototype version.
