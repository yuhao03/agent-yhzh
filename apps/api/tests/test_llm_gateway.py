import json

import httpx
import pytest
from pydantic import ValidationError

from agent_yhzh.schemas import ModelProviderConfigCreate
from agent_yhzh.services.llm_gateway import (
    LLMGatewayError,
    chat_complete,
    provider_model_name,
    resolve_protocol,
)
from agent_yhzh.services.model_config import RuntimeModelConfig


def runtime_for(protocol: str, **overrides) -> RuntimeModelConfig:
    values = {
        "provider": "openai_compatible",
        "api_protocol": protocol,
        "base_url": "https://llm.example.com/v1",
        "chat_model": "test-model",
        "embedding_model": None,
        "api_key": "sk-secret-key",
        "temperature": 0.2,
        "max_tokens": 128,
        "timeout_seconds": 10,
        "source": "database",
    }
    values.update(overrides)
    return RuntimeModelConfig(**values)


MESSAGES = [
    {"role": "system", "content": "你是助手"},
    {"role": "user", "content": "你好"},
]


async def test_chat_completions_protocol_request_and_parse():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("authorization")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "chat-ok"}}]}
        )

    answer = await chat_complete(
        runtime_for("chat_completions_v1"),
        MESSAGES,
        transport=httpx.MockTransport(handler),
    )
    assert answer == "chat-ok"
    assert captured["url"] == "https://llm.example.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-secret-key"
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["messages"][0]["role"] == "system"


async def test_messages_protocol_extracts_system_and_parses_blocks():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["api_key"] = request.headers.get("x-api-key")
        captured["version"] = request.headers.get("anthropic-version")
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "messages-ok"}]}
        )

    answer = await chat_complete(
        runtime_for("messages_v1"),
        MESSAGES,
        transport=httpx.MockTransport(handler),
    )
    assert answer == "messages-ok"
    assert captured["url"] == "https://llm.example.com/v1/messages"
    assert captured["api_key"] == "sk-secret-key"
    assert captured["version"]
    assert captured["payload"]["system"] == "你是助手"
    assert all(
        message["role"] != "system" for message in captured["payload"]["messages"]
    )
    assert "max_tokens" in captured["payload"]


async def test_responses_protocol_instructions_and_output_parse():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": "responses-ok"}],
                    }
                ]
            },
        )

    answer = await chat_complete(
        runtime_for("responses_v1"),
        MESSAGES,
        transport=httpx.MockTransport(handler),
    )
    assert answer == "responses-ok"
    assert captured["url"] == "https://llm.example.com/v1/responses"
    assert captured["payload"]["instructions"] == "你是助手"
    assert captured["payload"]["input"][0]["role"] == "user"
    assert "max_output_tokens" in captured["payload"]


async def test_messages_protocol_clamps_temperature():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200, json={"content": [{"type": "text", "text": "ok"}]}
        )

    await chat_complete(
        runtime_for("messages_v1", temperature=1.8),
        MESSAGES,
        transport=httpx.MockTransport(handler),
    )
    assert captured["payload"]["temperature"] <= 1


def test_messages_protocol_config_rejects_temperature_above_one():
    with pytest.raises(ValidationError):
        ModelProviderConfigCreate(
            name="anthropic-config",
            provider="anthropic",
            api_protocol="messages_v1",
            chat_model="claude-test",
            temperature=1.5,
        )


async def test_upstream_error_is_sanitized():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom sk-secret-key boom")

    with pytest.raises(LLMGatewayError) as excinfo:
        await chat_complete(
            runtime_for("chat_completions_v1"),
            MESSAGES,
            transport=httpx.MockTransport(handler),
        )
    assert "sk-secret-key" not in str(excinfo.value)
    assert "upstream_status_500" in str(excinfo.value)


def test_protocol_fallback_by_provider():
    assert (
        resolve_protocol(runtime_for("", provider="anthropic")) == "messages_v1"
    )
    assert (
        resolve_protocol(runtime_for("", provider="openai"))
        == "chat_completions_v1"
    )
    assert resolve_protocol(runtime_for("responses_v1")) == "responses_v1"


def test_provider_model_name_strips_matching_litellm_prefix():
    # openai/openai_compatible 前缀映射到 openai,应被剥掉。
    assert (
        provider_model_name(
            runtime_for(
                "chat_completions_v1",
                provider="openai",
                chat_model="openai/gpt-5.4-mini",
            )
        )
        == "gpt-5.4-mini"
    )
    assert (
        provider_model_name(
            runtime_for(
                "chat_completions_v1",
                provider="openai_compatible",
                chat_model="openai/gpt-4o",
            )
        )
        == "gpt-4o"
    )
    assert (
        provider_model_name(
            runtime_for(
                "messages_v1", provider="anthropic", chat_model="anthropic/claude-3"
            )
        )
        == "claude-3"
    )


def test_provider_model_name_preserves_bare_and_vendor_names():
    # 无前缀的裸模型名原样保留。
    assert (
        provider_model_name(
            runtime_for(
                "chat_completions_v1", provider="openai", chat_model="gpt-5.4-mini"
            )
        )
        == "gpt-5.4-mini"
    )
    # 非当前 provider 的 vendor/model(如 OpenRouter 命名)保持原样。
    assert (
        provider_model_name(
            runtime_for(
                "chat_completions_v1",
                provider="openai_compatible",
                chat_model="meta-llama/llama-3",
            )
        )
        == "meta-llama/llama-3"
    )


async def test_chat_completions_sends_bare_model_on_wire():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content)
        return httpx.Response(
            200, json={"choices": [{"message": {"content": "ok"}}]}
        )

    await chat_complete(
        runtime_for(
            "chat_completions_v1", provider="openai", chat_model="openai/gpt-5.4-mini"
        ),
        MESSAGES,
        transport=httpx.MockTransport(handler),
    )
    assert captured["payload"]["model"] == "gpt-5.4-mini"
