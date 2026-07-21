"""Provider-neutral business agent with OpenAI and deterministic Mock modes."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv

from .mock_customers import get_mock_customers
from .prompt import SYSTEM_PROMPT, build_user_prompt
from .schema import REPORT_JSON_SCHEMA, BusinessReport, validate_report
from .skills import run_mock_skills_pipeline

load_dotenv()


def _parse_json_response(content: str) -> dict[str, Any]:
    """Parse JSON returned with optional reasoning or Markdown wrappers."""
    cleaned = content.strip()
    if "</think>" in cleaned:
        cleaned = cleaned.split("</think>", 1)[1].strip()
    cleaned = cleaned.replace("```json", "").replace("```JSON", "").replace("```", "").strip()

    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
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
    raise RuntimeError("MiniMax 返回内容不是有效 JSON，请检查模型输出或提示词。")


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

    @abstractmethod
    def generate(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> BusinessReport:
        raise NotImplementedError


class OpenAIProvider(BusinessAgentProvider):
    """OpenAI Responses API adapter using the same public report schema."""

    def __init__(self) -> None:
        from openai import OpenAI

        self.client = OpenAI()
        self.model = _setting("OPENAI_MODEL", "gpt-5.4-mini")

    def generate(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> BusinessReport:
        response = self.client.responses.create(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=build_user_prompt(customer_input, mock_customers),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "zhike_business_report",
                    "strict": True,
                    "schema": REPORT_JSON_SCHEMA,
                }
            },
        )
        return validate_report(json.loads(response.output_text))


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

    def generate(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> BusinessReport:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(customer_input, mock_customers),
                },
            ],
            temperature=0.2,
            max_completion_tokens=2048,
        )
        content = response.choices[0].message.content or ""
        payload = _parse_json_response(content)
        return validate_report(payload)


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

    def generate(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> BusinessReport:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_user_prompt(customer_input, mock_customers),
                },
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        try:
            payload = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "NVIDIA NIM 返回内容不是有效 JSON，请检查模型是否支持 JSON 输出。"
            ) from exc
        return validate_report(payload)


class MockProvider(BusinessAgentProvider):
    """Local provider that executes the submitted Skills workflow without a key."""

    def generate(
        self, customer_input: str, mock_customers: list[dict[str, Any]]
    ) -> BusinessReport:
        return validate_report(run_mock_skills_pipeline(customer_input, mock_customers))


def _select_provider(force_mock: bool = False) -> tuple[BusinessAgentProvider, str]:
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
        _setting_any(("MINIMAX_API_KEY", "APP_KEY"))
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


def runtime_mode(force_mock: bool = False) -> str:
    """Return a user-facing provider label without exposing credentials."""
    _, mode = _select_provider(force_mock=force_mock)
    return mode
