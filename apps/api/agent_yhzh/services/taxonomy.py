"""电商为主的知识分类体系与自动归类。

分类既用于知识条目/候选的归档,也用于 supervisor 把问题路由给对应的子 Agent。
关键词打分保证离线可用且确定;配置了模型后可用 LLM 精分,失败时降级关键词。
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_yhzh.services.model_config import RuntimeModelConfig


@dataclass(frozen=True)
class KnowledgeCategory:
    slug: str
    name: str
    description: str
    keywords: tuple[str, ...]


GENERAL_CATEGORY = "general"

CATEGORIES: tuple[KnowledgeCategory, ...] = (
    KnowledgeCategory(
        slug="ecommerce_product_copy",
        name="商品文案",
        description="商品标题、卖点、详情页文案、主图文案与品牌故事。",
        keywords=(
            "文案", "卖点", "详情页", "主图", "标题党", "种草", "描述", "宣传语",
            "介绍", "品牌故事", "话术包装", "文描", "短视频脚本", "商品介绍",
        ),
    ),
    KnowledgeCategory(
        slug="ecommerce_listing",
        name="平台运营与Listing",
        description="商品发布、类目、关键词、SEO、平台规则与店铺运营。",
        keywords=(
            "listing", "seo", "关键词", "类目", "上架", "发布商品", "搜索排名",
            "标题优化", "平台规则", "违规", "店铺", "流量", "曝光", "亚马逊",
            "淘宝", "天猫", "拼多多", "京东", "shopee", "temu", "速卖通", "抖店",
        ),
    ),
    KnowledgeCategory(
        slug="ecommerce_marketing",
        name="营销策划",
        description="促销活动、直播、投放、会员运营与节日营销方案。",
        keywords=(
            "营销", "促销", "活动策划", "直播", "投放", "广告", "roi", "转化率",
            "优惠券", "满减", "会员", "复购", "私域", "拉新", "大促", "618",
            "双11", "双十一", "黑五", "推广",
        ),
    ),
    KnowledgeCategory(
        slug="ecommerce_service",
        name="客服与售后",
        description="售前售后话术、退换货、物流、差评与纠纷处理。",
        keywords=(
            "客服", "售后", "退货", "退款", "换货", "物流", "快递", "发货",
            "差评", "投诉", "纠纷", "话术", "催付", "咨询回复", "赔偿", "维权",
        ),
    ),
    KnowledgeCategory(
        slug="ecommerce_analysis",
        name="选品与市场分析",
        description="选品、竞品分析、定价、供应链与市场趋势判断。",
        keywords=(
            "选品", "竞品", "定价", "利润", "成本", "供应链", "货源", "市场分析",
            "趋势", "数据分析", "销量", "毛利", "进货", "爆款", "蓝海", "调研",
        ),
    ),
    KnowledgeCategory(
        slug=GENERAL_CATEGORY,
        name="通用知识",
        description="不属于电商专项的其他领域问题与通用经验。",
        keywords=(),
    ),
)

CATEGORY_SLUGS = tuple(category.slug for category in CATEGORIES)


def score_categories(text: str) -> dict[str, int]:
    """按关键词出现次数给每个分类打分(确定性,离线可用)。"""
    lowered = text.lower()
    scores: dict[str, int] = {}
    for category in CATEGORIES:
        if not category.keywords:
            continue
        score = sum(lowered.count(keyword.lower()) for keyword in category.keywords)
        if score:
            scores[category.slug] = score
    return scores


def classify_text(text: str) -> str:
    """返回最匹配的分类 slug;无电商信号时归入通用分类。"""
    scores = score_categories(text)
    if not scores:
        return GENERAL_CATEGORY
    return max(scores.items(), key=lambda entry: (entry[1], entry[0]))[0]


async def classify_text_llm(text: str, runtime: "RuntimeModelConfig | None") -> str:
    """配置了运行时模型时用 LLM 精分类;未配置或调用失败时降级关键词打分。"""
    from agent_yhzh.services.llm_gateway import (
        LLMGatewayError,
        chat_complete,
        is_llm_configured,
    )

    if not is_llm_configured(runtime):
        return classify_text(text)
    assert runtime is not None
    catalogue = "\n".join(
        f"- {category.slug}: {category.name}，{category.description}"
        for category in CATEGORIES
    )
    try:
        raw = await chat_complete(
            runtime,
            [
                {
                    "role": "system",
                    "content": (
                        "你是知识分类器。根据文本从下列分类中选择最贴切的一个，"
                        f"只输出该分类的 slug，不要输出其他内容。\n{catalogue}"
                    ),
                },
                {"role": "user", "content": text[:2000]},
            ],
            temperature=0,
            max_tokens=24,
        )
    except LLMGatewayError:
        return classify_text(text)
    slug = raw.strip().split()[0].strip("`'\"，。！？；：.,!?;:") if raw.strip() else ""
    return slug if slug in CATEGORY_SLUGS else classify_text(text)


def category_options() -> list[dict[str, str]]:
    return [
        {
            "slug": category.slug,
            "name": category.name,
            "description": category.description,
        }
        for category in CATEGORIES
    ]
