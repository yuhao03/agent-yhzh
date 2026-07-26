import httpx
import pytest

from agent_yhzh.services import llm_gateway, subagents
from agent_yhzh.services.model_config import RuntimeModelConfig
from agent_yhzh.services.subagents import (
    generate_agent_answer,
    get_subagent,
    route_by_keywords,
    route_question,
)
from agent_yhzh.services.taxonomy import classify_text, classify_text_llm


def llm_runtime() -> RuntimeModelConfig:
    return RuntimeModelConfig(
        provider="openai_compatible",
        api_protocol="chat_completions_v1",
        base_url="https://llm.example.com/v1",
        chat_model="test-model",
        embedding_model=None,
        api_key="sk-secret-key",
        temperature=0.2,
        max_tokens=128,
        timeout_seconds=10,
        source="database",
    )


def patch_gateway_transport(
    monkeypatch: pytest.MonkeyPatch, handler
) -> None:
    transport = httpx.MockTransport(handler)
    original = llm_gateway.chat_complete

    async def patched(runtime, messages, **kwargs):
        kwargs["transport"] = transport
        return await original(runtime, messages, **kwargs)

    monkeypatch.setattr(llm_gateway, "chat_complete", patched)
    monkeypatch.setattr(subagents, "chat_complete", patched)


def slug_response(slug: str):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"choices": [{"message": {"content": slug}}]}
        )

    return handler


def error_response(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, text="boom")


def test_classify_text_ecommerce_domains():
    assert classify_text("帮我写一个商品详情页的卖点文案") == "ecommerce_product_copy"
    assert classify_text("亚马逊listing关键词怎么优化才能提升搜索排名") == "ecommerce_listing"
    assert classify_text("双11大促直播间的优惠券投放怎么策划") == "ecommerce_marketing"
    assert classify_text("买家要退货退款还给了差评怎么回复") == "ecommerce_service"
    assert classify_text("帮我做竞品分析看看这个类目的选品定价") in {
        "ecommerce_analysis",
        "ecommerce_listing",
    }
    assert classify_text("怎么学习弹钢琴") == "general"


def test_route_by_keywords_maps_to_specialists():
    assert route_by_keywords("写个商品文案").slug == "copywriter"
    assert route_by_keywords("退款纠纷话术").slug == "service_agent"
    assert route_by_keywords("随便聊聊历史").slug == "generalist"


async def test_route_question_without_llm_uses_keywords():
    spec, routed_by = await route_question("帮我策划一场促销活动", None)
    assert spec.slug == "marketing_planner"
    assert routed_by == "keywords"


async def test_route_question_llm_slug_is_adopted(monkeypatch: pytest.MonkeyPatch):
    patch_gateway_transport(monkeypatch, slug_response("copywriter."))
    spec, routed_by = await route_question("随便一个问题", llm_runtime())
    assert spec.slug == "copywriter"
    assert routed_by == "llm"


async def test_route_question_llm_invalid_slug_falls_back(
    monkeypatch: pytest.MonkeyPatch,
):
    patch_gateway_transport(monkeypatch, slug_response("unknown_agent"))
    spec, routed_by = await route_question("退款纠纷话术", llm_runtime())
    assert spec.slug == "service_agent"
    assert routed_by == "keywords"


async def test_route_question_gateway_error_falls_back(
    monkeypatch: pytest.MonkeyPatch,
):
    patch_gateway_transport(monkeypatch, error_response)
    spec, routed_by = await route_question("退款纠纷话术", llm_runtime())
    assert spec.slug == "service_agent"
    assert routed_by == "keywords"


async def test_classify_text_llm_adopts_valid_slug(monkeypatch: pytest.MonkeyPatch):
    patch_gateway_transport(monkeypatch, slug_response("ecommerce_service"))
    assert await classify_text_llm("怎么学习弹钢琴", llm_runtime()) == "ecommerce_service"


async def test_classify_text_llm_falls_back_on_gateway_error(
    monkeypatch: pytest.MonkeyPatch,
):
    patch_gateway_transport(monkeypatch, error_response)
    assert await classify_text_llm("买家要退货退款", llm_runtime()) == "ecommerce_service"


async def test_classify_text_llm_without_runtime_uses_keywords():
    assert await classify_text_llm("买家要退货退款", None) == "ecommerce_service"


async def test_generate_agent_answer_without_llm_and_knowledge():
    spec = get_subagent("copywriter")
    answer = await generate_agent_answer(spec, "写文案", [], [], None)
    assert "还没有足够可靠的信息" in answer
