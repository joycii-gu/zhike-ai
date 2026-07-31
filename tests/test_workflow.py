"""Tests for real Skills orchestration without making any external API call."""

from unittest.mock import patch

from src.agent import SynScaleProvider, _select_provider
from src.mock_customers import get_mock_customers
from src.workflow import run_chained_workflow, run_local_workflow


def fake_model_call(_system: str, user: str) -> dict:
    if "Skill 1" in user:
        return {"facts": {"customer_name": "李总", "needs": ["了解客户跟进能力"]}, "inferences": [], "unknowns": [], "evidence": ["李总希望下周沟通"]}
    return {"output": "**结构化业务输出**\n- 基于上游 Skill 结果生成。"}


def test_chained_workflow_calls_all_seven_skills() -> None:
    result = run_chained_workflow(
        fake_model_call,
        "李总想了解 AI 如何帮助销售团队做客户跟进，希望下周沟通。",
        get_mock_customers(),
    )
    assert len(result["trace"]) == 7
    assert all(item["status"] == "api" for item in result["trace"])
    assert all(result["report"].values())


def test_step_failure_falls_back_without_breaking_report() -> None:
    call_count = 0

    def unstable_call(system: str, user: str) -> dict:
        nonlocal call_count
        call_count += 1
        if call_count == 3:
            raise RuntimeError("simulated provider error")
        return fake_model_call(system, user)

    result = run_chained_workflow(
        unstable_call,
        "赵总希望整理企业服务客户需求并降低信息分散问题。",
        get_mock_customers(),
    )
    assert any(item["status"] == "fallback" for item in result["trace"])
    assert all(result["report"].values())


def test_local_workflow_has_a_full_trace() -> None:
    result = run_local_workflow("陈老师希望提高课程顾问跟进效率。", get_mock_customers())
    assert len(result["trace"]) == 7
    assert all(item["status"] == "local" for item in result["trace"])


def test_synscale_is_preferred_when_configured() -> None:
    values = {"SYNSCALE_API_KEY": "test-synscale-key"}

    def fake_setting(name: str, default: str = "") -> str:
        return values.get(name, default)

    with patch("src.agent._setting", side_effect=fake_setting):
        provider, label = _select_provider()

    assert isinstance(provider, SynScaleProvider)
    assert label == "SynScale API"


if __name__ == "__main__":
    test_chained_workflow_calls_all_seven_skills()
    test_step_failure_falls_back_without_breaking_report()
    test_local_workflow_has_a_full_trace()
    test_synscale_is_preferred_when_configured()
    print("W3 workflow regression tests passed")
