"""Regression tests for the W3 deterministic KPI layer."""

from src.kpi_agent import build_kpi_dashboard, default_session_state, ingest_customer, record_feedback


def test_feedback_drives_metrics() -> None:
    state = default_session_state()
    state, customer = ingest_customer(state, "李总想下周演示 AI 客户跟进能力，预算暂未明确。")
    before = build_kpi_dashboard(state)
    assert before["metrics"][0]["actual"] == 0
    state, _ = record_feedback(state, customer["id"], "need_confirmed")
    state, _ = record_feedback(state, customer["id"], "effective_communication")
    state, _ = record_feedback(state, customer["id"], "solution_meeting")
    after = build_kpi_dashboard(state)
    assert [metric["actual"] for metric in after["metrics"][:3]] == [1, 1, 1]
    assert after["customer_count"] == 1


def test_repeated_input_does_not_duplicate_customer() -> None:
    state = default_session_state()
    text = "赵总希望整理企业客户需求，正在了解 AI 工具。"
    state, first = ingest_customer(state, text)
    state, second = ingest_customer(state, text)
    assert first["id"] == second["id"]
    assert len(state["customers"]) == 1


def test_kpi_pace_and_audit_trail_are_traceable() -> None:
    state = default_session_state()
    state["business_goal"].update(
        {
            "period_total_workdays": 5,
            "remaining_workdays": 3,
            "effective_communications_target": 5,
        }
    )
    state, customer = ingest_customer(state, "周校长希望本周安排一次线上演示，预算尚未确认。")
    before = build_kpi_dashboard(state)
    effective = before["metrics"][1]
    assert effective["status"] == "节奏滞后"
    assert effective["daily_required"] == 1.7

    state, _ = record_feedback(state, customer["id"], "effective_communication", "已确认周五演示时间")
    after = build_kpi_dashboard(state)
    assert after["recent_feedback"][0]["customer_name"] == customer["name"]
    assert after["recent_feedback"][0]["note"] == "已确认周五演示时间"


if __name__ == "__main__":
    test_feedback_drives_metrics()
    test_repeated_input_does_not_duplicate_customer()
    test_kpi_pace_and_audit_trail_are_traceable()
    print("W3 KPI regression tests passed")
