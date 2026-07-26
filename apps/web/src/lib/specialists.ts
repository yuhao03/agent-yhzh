import {
  BarChart3,
  Headset,
  LineChart,
  MessageCircleHeart,
  PenLine,
  Store,
} from "lucide-react";

/** 与后端 services/subagents.py 的注册表保持一致。 */
export const SPECIALISTS = [
  {
    slug: "copywriter",
    name: "商品文案专家",
    icon: PenLine,
    description: "标题、卖点、详情页与带货脚本",
    prompt: "帮我给一款新品写商品标题和三个核心卖点,先问我要产品信息。",
  },
  {
    slug: "listing_optimizer",
    name: "平台运营专家",
    icon: Store,
    description: "Listing、关键词、类目与平台规则",
    prompt: "帮我优化一条商品 Listing 的标题和关键词布局,先问我平台和品类。",
  },
  {
    slug: "marketing_planner",
    name: "营销策划专家",
    icon: BarChart3,
    description: "大促节奏、直播企划与投放策略",
    prompt: "帮我策划一场大促活动方案,先了解我的商品和预算。",
  },
  {
    slug: "service_agent",
    name: "客服售后专家",
    icon: Headset,
    description: "售后话术、退换货与差评处理",
    prompt: "帮我写一条安抚差评买家并引导修改评价的话术。",
  },
  {
    slug: "market_analyst",
    name: "选品分析专家",
    icon: LineChart,
    description: "选品、竞品拆解与定价测算",
    prompt: "帮我分析一个类目值不值得进入,先问我目标平台和预算。",
  },
  {
    slug: "generalist",
    name: "通用助手",
    icon: MessageCircleHeart,
    description: "电商之外的问题也可以交给我",
    prompt: "我有一个非电商的问题想请教你。",
  },
] as const;

export type SpecialistSlug = (typeof SPECIALISTS)[number]["slug"];
