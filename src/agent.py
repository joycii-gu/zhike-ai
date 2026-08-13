"""Provider-neutral business agent with SynScale, MiniMax and local fallback modes."""

from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv

from .mock_customers import get_mock_customers
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import REPORT_FIELDS, REPORT_JSON_SCHEMA, BusinessReport, validate_report
from .skills import run_mock_skills_pipeline
from .workflow import AgentRunResult, run_chained_workflow, run_local_workflow

load_dotenv()


def _parse_json_response(content: Any) -> dict[str, Any]:
    """Parse JSON returned with optional reasoning or Markdown wrappers."""
    if isinstance(content, list):
        content = "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in content
        )
    if not isinstance(content, str):
        raise RuntimeError("模型返回内容为空或格式不支持，请检查模型输出。")
    cleaned = content.strip()
    # MiniMax may return a closed or truncated reasoning block.
    if "</think>" in cleaned:
        cleaned = cleaned.split("</think>", 1)[1].strip()
    elif "<think>" in cleaned:
        # Keep the remainder when the provider truncates an unclosed block;
        # the JSON scanner below can still locate a complete object.
        cleaned = cleaned.replace("<think>", "", 1).strip()
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL | re.IGNORECASE).strip()
    cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()

    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            nested = json.loads(payload)
            if isinstance(nested, dict):
                return nested
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    raise RuntimeError("模型返回内容不是有效 JSON，请检查模型输出或提示词。")


def _normalize_report_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize wrapped, nested, or Chinese-labelled model responses."""
    aliases = {
        "customer_profile": "customer_profile", "customerprofile": "customer_profile", "客户档案": "customer_profile",
        "need_analysis": "need_analysis", "needanalysis": "need_analysis", "客户需求分析": "need_analysis",
        "opportunity_assessment": "opportunity_assessment", "opportunityassessment": "opportunity_assessment", "业务机会判断": "opportunity_assessment",
        "follow_up_plan": "follow_up_plan", "followupplan": "follow_up_plan", "跟进建议": "follow_up_plan",
        "communication_script": "communication_script", "communicationscript": "communication_script", "沟通话术": "communication_script",
        "daily_report": "daily_report", "dailyreport": "daily_report", "业务日报": "daily_report",
    }

    def canonical(key: Any) -> str | None:
        text = str(key).strip().lower().replace(" ", "").replace("-", "_")
        if text in aliases:
            return aliases[text]
        for label, field in aliases.items():
            if not label.isascii() and label in text:
                return field
        return None

    normalized: dict[str, Any] = {}

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                field = canonical(key)
                if field and field not in normalized and value is not None:
                    normalized[field] = (
                        value
                        if isinstance(value, str)
                        else json.dumps(value, ensure_ascii=False)
                    )
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, str):
            try:
                nested = json.loads(node)
            except (TypeError, json.JSONDecodeError):
                return
            if isinstance(nested, (dict, list)):
                visit(nested)

    visit(payload)
    return {**payload, **normalized}


def _complete_missing_fields(
    payload: dict[str, Any], customer_input: str, mock_customers: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fill only missing model fields locally, avoiding a second API call."""
    missing = [field for field in REPORT_FIELDS if not str(payload.get(field, "")).strip()]
    if not missing:
        return payload
    local_report = run_mock_skills_pipeline(customer_input, mock_customers)
    completed = dict(payload)
    for field in missing:
        completed[field] = local_report[field]
    return completed


def _setting(name: str, default: str = "") -> str:
    """Read configuration from environment first, then Streamlit Secrets."""
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        secret_value = st.secrets.get(name, default)
        return str(secret_value).strip()
    except Exception:
        return default


def _setting_any(names: tuple[str, ...], default: str = "") -> str:
    """Read the first configured value, supporting platform aliases."""
    for name in names:
        value = _setting(name)
        if value:
            return value
    return default


class BusinessAgentProvider(ABC):
    """Provider interface reserved for API and future HermesAgent adapters."""

    def generate(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> BusinessReport:
        """Keep the W2 public API while W3 exposes execution traces separately."""
        return self.generate_with_trace(customer_input, mock_customers)["report"]

    @abstractmethod
    def generate_with_trace(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> AgentRunResult:
        raise NotImplementedError


class OpenAIProvider(BusinessAgentProvider):
    """OpenAI Responses API adapter using the same public report schema."""

    def __init__(self) -> None:
        from openai import OpenAI

        self.client = OpenAI()
        self.model = _setting("OPENAI_MODEL", "gpt-5.4-mini")

    def _call_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_completion_tokens=2048,
            response_format={"type": "json_object"},
        )
        return _parse_json_response(response.choices[0].message.content or "")

    def generate_with_trace(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> AgentRunResult:
        return run_chained_workflow(
            self._call_json, customer_input, mock_customers, runtime_label="OpenAI API"
        )


class MiniMaxProvider(BusinessAgentProvider):
    """MiniMax OpenAI-compatible Chat Completions adapter."""

    def __init__(self) -> None:
        from openai import OpenAI

        minimax_key = _setting("MINIMAX_API_KEY")
        platform_key = _setting("APP_KEY")
        api_key = minimax_key or platform_key
        default_base_url = (
            "https://api.minimaxi.com/v1"
            if minimax_key
            else "https://ai.synnovator.com/v1"
        )
        base_url = _setting_any(("MINIMAX_BASE_URL", "BASE_URL"), default_base_url)
        model = _setting_any(("MINIMAX_MODEL", "MODEL_ID"), "MiniMax-M2.7")
        if not api_key:
            raise RuntimeError("未找到 MINIMAX_API_KEY，请在 .env 或 Streamlit Secrets 中配置。")
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=90.0,
            max_retries=2,
        )
        self.model = model

    def _call_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_completion_tokens=2048,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return _parse_json_response(content)

    def generate_with_trace(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> AgentRunResult:
        return run_chained_workflow(
            self._call_json, customer_input, mock_customers, runtime_label="MiniMax API"
        )


class SynScaleProvider(BusinessAgentProvider):
    """Optional SynScale OpenAI-compatible adapter."""

    def __init__(self) -> None:
        from openai import OpenAI

        api_key = _setting("SYNSCALE_API_KEY")
        if not api_key:
            raise RuntimeError("未找到 SYNSCALE_API_KEY，请在 .env 或 Streamlit Secrets 中配置。")

        self.model = _setting("SYNSCALE_MODEL", "deepseek-v4-flash")
        self.client = OpenAI(
            api_key=api_key,
            base_url=_setting("SYNSCALE_BASE_URL", "http://synscale.onesyn.ai/v1"),
            timeout=90.0,
            max_retries=2,
        )

    def _call_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=1200,
        )
        return _parse_json_response(response.choices[0].message.content or "")

    def generate_with_trace(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> AgentRunResult:
        return run_chained_workflow(
            self._call_json,
            customer_input,
            mock_customers,
            runtime_label=f"SynScale API · {self.model}",
        )


class NvidiaNimProvider(BusinessAgentProvider):
    """NVIDIA NIM adapter using its OpenAI-compatible Chat Completions API."""

    def __init__(self) -> None:
        from openai import OpenAI

        api_key = _setting("NVIDIA_API_KEY")
        base_url = _setting(
            "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
        )
        model = _setting("NVIDIA_MODEL")
        if not api_key:
            raise RuntimeError("未找到 NVIDIA_API_KEY，请在 .env 或环境变量中配置。")
        if not model:
            raise RuntimeError(
                "未找到 NVIDIA_MODEL，请配置所选 NVIDIA NIM 模型 ID。"
            )
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def _call_json(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return _parse_json_response(response.choices[0].message.content or "")

    def generate_with_trace(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> AgentRunResult:
        return run_chained_workflow(
            self._call_json, customer_input, mock_customers, runtime_label="NVIDIA NIM API"
        )


class MockProvider(BusinessAgentProvider):
    """Local provider that executes the submitted Skills workflow without a key."""

    def generate_with_trace(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> AgentRunResult:
        return run_local_workflow(customer_input, mock_customers)


def _select_provider(force_mock: bool = False) -> tuple[BusinessAgentProvider, str]:
    if not force_mock and _setting("SYNSCALE_API_KEY"):
        return SynScaleProvider(), "SynScale API"
    if not force_mock and _setting_any(("MINIMAX_API_KEY", "APP_KEY")):
        return MiniMaxProvider(), "MiniMax API"
    if not force_mock and _setting("NVIDIA_API_KEY"):
        return NvidiaNimProvider(), "NVIDIA NIM API"
    if not force_mock and _setting("OPENAI_API_KEY"):
        return OpenAIProvider(), "OpenAI API"
    return MockProvider(), "Mock Skills Workflow"


def has_api_provider() -> bool:
    """Whether a model provider is configured through env or cloud secrets."""
    return bool(
        _setting("SYNSCALE_API_KEY")
        or _setting_any(("MINIMAX_API_KEY", "APP_KEY"))
        or _setting("NVIDIA_API_KEY")
        or _setting("OPENAI_API_KEY")
    )


def business_agent(
    customer_input: str, *, force_mock: bool = False
) -> BusinessReport:
    """Generate a full report through the selected provider."""
    normalized = customer_input.strip()
    if len(normalized) < 8:
        raise ValueError("请输入至少 8 个字符的客户信息或沟通记录。")
    provider, _ = _select_provider(force_mock=force_mock)
    return provider.generate(normalized, get_mock_customers())


def business_agent_with_trace(
    customer_input: str, *, force_mock: bool = False
) -> AgentRunResult:
    """Run the W3 Agent and return both business report and actual Skills trace."""
    normalized = customer_input.strip()
    if len(normalized) < 8:
        raise ValueError("请输入至少 8 个字符的客户信息或沟通记录。")
    provider, _ = _select_provider(force_mock=force_mock)
    return provider.generate_with_trace(normalized, get_mock_customers())


def runtime_mode(force_mock: bool = False) -> str:
    """Return a user-facing provider label without exposing credentials."""
    _, mode = _select_provider(force_mock=force_mock)
    return mode
