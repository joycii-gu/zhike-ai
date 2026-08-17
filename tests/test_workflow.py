"""Tests for real Skills orchestration without making any external API call."""

from unittest.mock import patch

from src.agent import SynScaleProvider, _parse_json_response, _select_provider
from src.mock_customers import get_mock_customers
from src.skills import SKILL_ORDER, load_skill_definition, skill_files
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


def test_account_daily_report_context_never_includes_w2_mock_customers() -> None:
    """Normal account reports must not silently inherit W2 demo customers."""

    seen_daily_prompt: list[str] = []

    def model_call(system: str, user: str) -> dict:
        if "Skill 7" in user:
            seen_daily_prompt.append(user)
        return fake_model_call(system, user)

    run_chained_workflow(
        model_call,
        "赵总正在评估 AI 客户跟进工具，预算与决策人待确认。",
        [{"客户": "赵总", "行业": "企业服务", "当前阶段": "方案评估", "优先级": "中"}],
    )

    assert len(seen_daily_prompt) == 1
    assert "王经理" not in seen_daily_prompt[0]
    assert "陈老师" not in seen_daily_prompt[0]
    assert "赵总" in seen_daily_prompt[0]


def test_all_public_skills_are_registered_and_loaded_by_runtime() -> None:
    """Public Skill folders must match the seven-step runtime workflow."""
    expected = (
        "customer_info_parse",
        "customer_profile",
        "need_analysis",
        "opportunity_judgement",
        "follow_up",
        "communication",
        "daily_report",
    )
    assert SKILL_ORDER == expected
    assert tuple(skill_files()) == expected
    assert all(load_skill_definition(name).strip() for name in expected)

    observed_prompts: list[str] = []

    def checking_call(system: str, user: str) -> dict:
        observed_prompts.append(user)
        return fake_model_call(system, user)

    result = run_chained_workflow(
        checking_call,
        "李总想了解 AI 如何帮助销售团队做客户跟进，并希望下周沟通。",
        get_mock_customers(),
    )
    assert len(result["trace"]) == 7
    assert all("<public_skill_definition>" in prompt for prompt in observed_prompts)


def test_step_failure_falls_back_without_breaking_report() -> None:
    call_count = 0

    def unstable_call(system: str, user: str) -> dict:
        nonlocal call_count
        call_count += 1
        if call_count in (3, 4):
            raise RuntimeError("simulated provider error")
        return fake_model_call(system, user)

    result = run_chained_workflow(
        unstable_call,
        "赵总希望整理企业服务客户需求并降低信息分散问题。",
        get_mock_customers(),
        allow_local_fallback=True,
    )
    assert any(item["status"] == "fallback" for item in result["trace"])
    assert all(result["report"].values())


def test_transient_skill_failure_retries_before_fallback() -> None:
    call_count = 0

    def transient_call(system: str, user: str) -> dict:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("transient provider error")
        return fake_model_call(system, user)

    result = run_chained_workflow(
        transient_call,
        "李总希望了解 AI 客户跟进方案，并希望下周沟通。",
        get_mock_customers(),
    )
    assert all(item["status"] == "api" for item in result["trace"])
    assert result["trace"][1]["detail"].startswith("首次输出未通过校验")


def test_local_workflow_has_a_full_trace() -> None:
    result = run_local_workflow("陈老师希望提高课程顾问跟进效率。", get_mock_customers())
    assert len(result["trace"]) == 7
    assert all(item["status"] == "local" for item in result["trace"])


def test_structured_skill_response_is_not_mistaken_for_fallback() -> None:
    def structured_model_call(_system: str, user: str) -> dict:
        if "Skill 1" in user:
            return {"facts": {"customer_name": "李总"}, "inferences": [], "unknowns": [], "evidence": []}
        return {
            "行动重点": ["确认客户预算范围", "准备演示材料"],
            "风险提示": "预算尚未确认",
        }

    result = run_chained_workflow(
        structured_model_call,
        "李总希望下周沟通 AI 客户跟进方案，预算暂未确定。",
        get_mock_customers(),
    )
    assert all(item["status"] == "api" for item in result["trace"])
    assert "行动重点" in result["report"]["follow_up_plan"]


def test_follow_up_skill_json_array_is_normalized_as_api_output() -> None:
    """The public follow_up Skill contract intentionally returns an array."""
    payload = _parse_json_response(
        '[{"动作":"确认线上沟通时间","对象":"李总","优先级":"高"}]'
    )
    assert payload == {
        "output": [{"动作": "确认线上沟通时间", "对象": "李总", "优先级": "高"}]
    }

    def array_follow_up_call(_system: str, user: str) -> dict:
        if "Skill 1" in user:
            return {"facts": {"customer_name": "李总"}, "inferences": [], "unknowns": [], "evidence": []}
        if "Skill 5" in user:
            return _parse_json_response(
                '[{"动作":"确认线上沟通时间","对象":"李总","时点建议":"本周","沟通目标":"确认需求","准备材料":"问题清单","优先级":"高"}]'
            )
        return {"output": "- 已完成结构化输出"}

    result = run_chained_workflow(
        array_follow_up_call,
        "李总希望下周线上沟通 AI 客户跟进方案。",
        get_mock_customers(),
    )
    assert all(item["status"] == "api" for item in result["trace"])
    assert "确认线上沟通时间" in result["report"]["follow_up_plan"]


def test_follow_up_retry_uses_strict_object_contract() -> None:
    """A malformed first reply must receive a JSON-only repair prompt."""
    follow_up_attempts: list[str] = []

    def flaky_follow_up_call(_system: str, user: str) -> dict:
        if "Skill 1" in user:
            return {"facts": {"customer_name": "李总"}, "inferences": [], "unknowns": [], "evidence": []}
        if "Skill 5" in user:
            follow_up_attempts.append(user)
            if len(follow_up_attempts) == 1:
                raise RuntimeError("模型返回内容不是有效 JSON")
            assert "【结构化输出重试】" in user
            assert '"output"' in user
            return {"output": [{"动作": "确认线上沟通时间", "对象": "李总", "时点建议": "本周", "沟通目标": "确认需求", "准备材料": "问题清单", "优先级": "高"}]}
        return {"output": "- 已完成结构化输出"}

    result = run_chained_workflow(
        flaky_follow_up_call,
        "李总希望下周线上沟通 AI 客户跟进方案。",
        get_mock_customers(),
    )
    assert len(follow_up_attempts) == 2
    assert result["trace"][4]["status"] == "api"
    assert "确认线上沟通时间" in result["report"]["follow_up_plan"]


def test_synscale_is_preferred_when_configured() -> None:
    values = {
        "SYNSCALE_API_KEY": "test-synscale-key",
        "MINIMAX_API_KEY": "stale-minimax-key",
    }

    def fake_setting(name: str, default: str = "") -> str:
        return values.get(name, default)

    with patch("src.agent._setting", side_effect=fake_setting):
        provider, label = _select_provider()

    assert isinstance(provider, SynScaleProvider)
    assert label == "SynScale API"


def test_api_run_does_not_hide_a_skill_failure_with_local_output() -> None:
    def failing_call(_system: str, _user: str) -> dict:
        raise RuntimeError("provider unavailable")

    try:
        run_chained_workflow(
            failing_call,
            "李总希望下周沟通 AI 客户跟进方案，并关注预算与部署难度。",
            get_mock_customers(),
            runtime_label="SynScale API",
        )
    except RuntimeError as exc:
        assert "no local fallback" in str(exc)
    else:
        raise AssertionError("A failed API run must not return a local report")


if __name__ == "__main__":
    test_chained_workflow_calls_all_seven_skills()
    test_step_failure_falls_back_without_breaking_report()
    test_transient_skill_failure_retries_before_fallback()
    test_local_workflow_has_a_full_trace()
    test_structured_skill_response_is_not_mistaken_for_fallback()
    test_follow_up_skill_json_array_is_normalized_as_api_output()
    test_follow_up_retry_uses_strict_object_contract()
    test_synscale_is_preferred_when_configured()
    print("W3 workflow regression tests passed")
