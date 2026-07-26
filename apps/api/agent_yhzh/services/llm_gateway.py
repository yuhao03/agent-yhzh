"""多协议 LLM 网关。

同一个 RuntimeModelConfig 可以选择三种上游协议之一:

- ``chat_completions_v1``: OpenAI 兼容 ``POST {base}/chat/completions``
- ``messages_v1``:        Anthropic 兼容 ``POST {base}/messages``
- ``responses_v1``:       OpenAI Responses ``POST {base}/responses``

服务商(provider)只影响默认协议与默认 base_url,不再决定报文格式,
因此任意第三方兼容服务都可以显式选择协议接入。
"""

from typing import Any

import httpx

from agent_yhzh.services.model_config import RuntimeModelConfig


API_PROTOCOLS = ("chat_completions_v1", "messages_v1", "responses_v1")

ANTHROPIC_VERSION = "2023-06-01"

_DEFAULT_BASE_URLS = {
    "chat_completions_v1": "https://api.openai.com/v1",
    "messages_v1": "https://api.anthropic.com/v1",
    "responses_v1": "https://api.openai.com/v1",
}

_PROTOCOL_PATHS = {
    "chat_completions_v1": "/chat/completions",
    "messages_v1": "/messages",
    "responses_v1": "/responses",
}


class LLMGatewayError(RuntimeError):
    """上游模型服务调用失败(报文已脱敏)。"""


_LITELLM_PROVIDER_PREFIXES = {
    "openai": "openai",
    "openai_compatible": "openai",
    "azure": "azure",
    "anthropic": "anthropic",
    "ollama": "ollama",
}


def default_protocol_for_provider(provider: str) -> str:
    return "messages_v1" if provider == "anthropic" else "chat_completions_v1"


def provider_model_name(runtime: RuntimeModelConfig) -> str:
    """上游报文里应使用的裸模型名。

    ``RuntimeModelConfig.chat_model`` 可能带有 LiteLLM 风格的服务商前缀
    (例如 ``openai/gpt-5.4-mini``),与本项目 ``litellm_model_name`` 的命名约定一致。
    但各原生协议端点期望裸模型名,原样发送会被上游当成未知模型拒绝。这里剥掉
    与当前 provider 对应的前缀,作为 ``litellm_model_name`` 的逆操作;其他形式的
    斜杠(如 OpenRouter 的 ``vendor/model``)会被保留。
    """
    model = (runtime.chat_model or "").strip()
    expected = _LITELLM_PROVIDER_PREFIXES.get(runtime.provider, runtime.provider)
    head, separator, tail = model.partition("/")
    if separator and tail and head == expected:
        return tail
    return model


def resolve_protocol(runtime: RuntimeModelConfig) -> str:
    protocol = (runtime.api_protocol or "").strip()
    if protocol in API_PROTOCOLS:
        return protocol
    return default_protocol_for_provider(runtime.provider)


def _endpoint(runtime: RuntimeModelConfig, protocol: str) -> str:
    base = (runtime.base_url or _DEFAULT_BASE_URLS[protocol]).rstrip("/")
    return f"{base}{_PROTOCOL_PATHS[protocol]}"


def _split_system(messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
    system_parts = [
        str(message.get("content", ""))
        for message in messages
        if message.get("role") == "system"
    ]
    rest = [message for message in messages if message.get("role") != "system"]
    return "\n\n".join(part for part in system_parts if part), rest


def _build_request(
    runtime: RuntimeModelConfig,
    protocol: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> tuple[dict[str, str], dict[str, Any]]:
    headers = {"Content-Type": "application/json"}
    model = provider_model_name(runtime)
    if protocol == "messages_v1":
        if runtime.api_key:
            headers["x-api-key"] = runtime.api_key
        headers["anthropic-version"] = ANTHROPIC_VERSION
        system, rest = _split_system(messages)
        payload: dict[str, Any] = {
            "model": model,
            "messages": rest,
            "max_tokens": max_tokens,
            # Anthropic messages 协议温度上限为 1,超出会被上游直接拒绝。
            "temperature": min(temperature, 1.0),
        }
        if system:
            payload["system"] = system
        return headers, payload
    if runtime.api_key:
        headers["Authorization"] = f"Bearer {runtime.api_key}"
    if protocol == "responses_v1":
        system, rest = _split_system(messages)
        payload = {
            "model": model,
            "input": rest,
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if system:
            payload["instructions"] = system
        return headers, payload
    return headers, {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }


def _extract_text(protocol: str, data: dict[str, Any]) -> str:
    if protocol == "chat_completions_v1":
        choices = data.get("choices") or []
        if not choices:
            raise LLMGatewayError("provider_returned_no_choices")
        message = choices[0].get("message") or {}
        return str(message.get("content") or "")
    if protocol == "messages_v1":
        blocks = data.get("content") or []
        texts = [
            str(block.get("text", ""))
            for block in blocks
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        if not blocks:
            raise LLMGatewayError("provider_returned_no_content")
        return "\n".join(part for part in texts if part)
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    texts = []
    for item in data.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if isinstance(block, dict) and block.get("type") == "output_text":
                texts.append(str(block.get("text", "")))
    if not texts and not (data.get("output") or []):
        raise LLMGatewayError("provider_returned_no_output")
    return "\n".join(part for part in texts if part)


def _sanitize(message: str, api_key: str | None) -> str:
    if api_key:
        message = message.replace(api_key, "[secret]")
    return message[:500]


async def chat_complete(
    runtime: RuntimeModelConfig,
    messages: list[dict[str, str]],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    """调用上游模型返回纯文本回答;所有协议错误统一为 LLMGatewayError。"""
    protocol = resolve_protocol(runtime)
    headers, payload = _build_request(
        runtime,
        protocol,
        messages,
        temperature if temperature is not None else runtime.temperature,
        max_tokens if max_tokens is not None else runtime.max_tokens,
    )
    url = _endpoint(runtime, protocol)
    try:
        async with httpx.AsyncClient(
            timeout=runtime.timeout_seconds, transport=transport
        ) as client:
            response = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as error:
        raise LLMGatewayError(
            _sanitize(f"upstream_unreachable: {error}", runtime.api_key)
        ) from error
    if response.status_code >= 400:
        raise LLMGatewayError(
            _sanitize(
                f"upstream_status_{response.status_code}: {response.text}",
                runtime.api_key,
            )
        )
    try:
        data = response.json()
    except ValueError as error:
        raise LLMGatewayError("upstream_returned_invalid_json") from error
    if not isinstance(data, dict):
        raise LLMGatewayError("upstream_returned_invalid_json")
    return _extract_text(protocol, data)


def is_llm_configured(runtime: RuntimeModelConfig | None) -> bool:
    return bool(runtime and (runtime.api_key or runtime.base_url))
