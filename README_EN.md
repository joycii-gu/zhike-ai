# ZhiKe AI

## An AI Business Agent for Salespeople and Client-facing Professionals

> Dishui Lake Global OPC AI Challenge · S3 Global Youth Development Program · W2 Semifinal · X Innovation Track

### 1. Overview

ZhiKe AI is an AI business agent for salespeople, client managers, course consultants, business service consultants, other client-facing professionals, and small business operators. It turns fragmented customer notes and communication records into customer profiles, need analysis, business opportunity assessment, follow-up suggestions, communication scripts, and daily business reports.

ZhiKe AI is not a generic chatbot built around open-ended conversations. It is also not a traditional CRM focused primarily on storing customer data. It is a structured AI workflow designed for everyday customer follow-up tasks, with multiple Skills processing information in sequence and clear labels separating facts, inferences, and unknowns.

The Chinese name “ZhiKe” originally referred to a person responsible for receiving visitors, understanding their purpose, and arranging the appropriate response. The project adapts that role into an AI assistant that helps client-facing professionals understand customers and convert scattered information into clear business actions.

### 2. Core Workflow

**Customer Input → Customer Profile → Need Analysis → Opportunity Assessment → Follow-up Suggestions → Communication Script → Daily Business Report**

- **Customer Input:** Accept customer notes, chat records, or call summaries.
- **Customer Profile:** Extract identity, industry, role, needs, budget signals, and current stage.
- **Need Analysis:** Separate explicit needs, potential pain points, and open questions.
- **Opportunity Assessment:** Evaluate opportunity level using intent, budget, timing, decision conditions, and risks.
- **Follow-up Suggestions:** Recommend timing, discussion priorities, preparation materials, and next actions.
- **Communication Script:** Generate editable messages for chat, phone calls, or meeting invitations.
- **Daily Business Report:** Summarize priority customers, tasks, risks, and next-day actions.

### 3. W2 Web Demo

Users can paste raw WeChat conversations, call notes, meeting records, or quick business notes directly. No prior summarization or spreadsheet formatting is required. The page also offers an input-type selector and optional fields for the customer salutation, communication channel, and planned follow-up time. Missing information is labeled as “unknown / to be confirmed.”

The W2 goal is a runnable web prototype that validates the core workflow, not a complete commercial system. Its intended scope includes:

- entering customer notes or communication records;
- generating a business processing report with one button;
- producing a customer profile, need analysis, opportunity assessment, follow-up suggestions, communication script, and daily business report;
- combining the current customer with two or three in-memory mock customers to demonstrate cross-customer aggregation, priority ranking, task consolidation, and global risk alerts;
- using mock data only for the W2 demonstration, without a real database, historical records, or persistent multi-customer management.

W2 does not include user accounts, a database, cross-session persistence, live CRM integration, automatic WeChat access, business card OCR, calendar synchronization, multi-user permissions, or payments.

### 4. Highlights

1. **Structured business workflow:** Replaces open-ended Q&A and repeated prompting with a defined business process.
2. **Reduced hallucination risk:** Separates facts, inferences, and unknowns instead of presenting missing information as fact.
3. **Multi-step Skills pipeline:** Makes each processing stage easier to evaluate, debug, and improve independently.
4. **Cross-customer daily report demonstration:** Uses in-memory mock data to validate aggregation, ranking, task, and risk logic.
5. **Clear expansion path:** Can evolve from an individual productivity tool into team and business service scenarios.

### 5. Quick Start

Once the W2 Demo includes `app.py` and `requirements.txt`, run:

```bash
cd zhike-ai
pip install -r requirements.txt
streamlit run app.py
```

After startup, open the local URL shown in the terminal to try the demo.

### 6. Project Structure

The following is the target W2 submission structure. Actual completion status should be verified against the repository.

```text
zhike-ai/
├── README.md
├── README_EN.md
├── app.py
├── requirements.txt
├── skills/
│   ├── README.md
│   ├── customer_profile/SKILL.md
│   ├── need_analysis/SKILL.md
│   ├── opportunity_judgement/SKILL.md
│   ├── follow_up/SKILL.md
│   ├── communication/SKILL.md
│   └── daily_report/SKILL.md
├── docs/
│   ├── 01_project_specs.md
│   ├── 02_skills_workflow.md
│   ├── 03_prototype_usage.md
│   ├── 04_demo_case.md
│   ├── 05_evaluation.md
│   └── 06_roadmap.md
├── examples/
│   ├── case_01_training_customer.md
│   ├── case_02_course_consultant.md
│   ├── case_03_enterprise_service.md
│   └── evaluation_result.md
├── src/
│   ├── agent.py
│   ├── skills.py
│   ├── prompt.py
│   ├── schema.py
│   ├── mock_customers.py
│   └── __init__.py
└── prototype/
    ├── README.md
    └── zhike_prototype.html
```

The `skills/` directory contains the reviewable Skill definitions. `src/skills.py` executes their input/output boundaries in Mock mode; the HTML file is a reference interface, while `app.py` remains the W2 main entry point.

### 7. Evaluation

The project uses a 100-point evaluation framework. Detailed scoring rules and acceptance thresholds are documented in [`docs/05_evaluation.md`](docs/05_evaluation.md).

| Criterion | Evaluation focus |
|---|---|
| Information extraction completeness | Completeness and correctness of key facts |
| Customer profile structure | Consistent, readable, and verifiable fields |
| Need analysis accuracy | Evidence-based needs, pain points, and barriers |
| Opportunity assessment rationality | Alignment among rating, evidence, and risks |
| Follow-up suggestion actionability | Clear action, owner, timing, and objective |
| Communication script usability | Natural, relevant, and free of unsupported promises |
| Daily report completeness | Cross-customer aggregation, ranking, tasks, and risks |
| User operation simplicity | Low-friction completion of the core workflow |

Example evaluation results must be recorded from actual Demo runs. Target scores are not presented as achieved results in advance.

### 8. W2 / W3 / W4 Roadmap

| Stage | Goal |
|---|---|
| W2 | Deliver a web demo and validate the end-to-end core workflow and evaluation framework |
| W3 | Add real multi-customer management, follow-up history, and Agent memory |
| W4 | Integrate WeChat, CRM, calendars, and business card OCR under appropriate permissions and compliance controls, creating a deployable business application |

### 9. Current Status

This project is currently a W2 prototype. It focuses on validating the core workflow and evaluation criteria. It does not claim to be a full CRM, an enterprise system, or a fully integrated external business platform. The repository contents and a runnable demonstration remain the source of truth for completion status.

## Documents

- [Project Specs](docs/01_project_specs.md)
- [Core Skills / Workflow](docs/02_skills_workflow.md)
- [Prototype Usage](docs/03_prototype_usage.md)
- [Demo Case](docs/04_demo_case.md)
- [Evaluation](docs/05_evaluation.md)
- [Roadmap](docs/06_roadmap.md)
- [Chinese README](README.md)

## Competition Information

- **Stage:** S3 Global Youth Development Program · W2 Semifinal
- **Track:** track-103 — X Innovation Track / Team-defined
- **Stage task:** Submit the key Skills / Workflow defined in the Specs and run the product Prototype
- **Product positioning:** An AI business processing agent for salespeople and client-facing professionals
- **Core workflow:** Customer Input → Customer Profile → Need Analysis → Opportunity Assessment → Follow-up Suggestions → Communication Script → Daily Business Report
- **W2 entry point:** Streamlit web demo (`app.py`)
- **W2 runtime mode:** Mock Skills Workflow, runnable without an API key
- **Submission directory:** `zhike-ai/`
