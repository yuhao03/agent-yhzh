import {
  ArrowRight,
  BrainCircuit,
  LockKeyhole,
  Sparkles,
  UserRound,
} from "lucide-react";
import Link from "next/link";
import { cookies } from "next/headers";

import { SPECIALISTS } from "@/lib/specialists";
import { USER_COOKIE, isAuthTokenExpired, readUserSession } from "@/lib/user-session";

const capabilities = [
  {
    icon: BrainCircuit,
    title: "越用越懂业务",
    description: "从真实问题和反馈中发现高价值信息,经确认后归入分类知识库,专家回答持续变准。",
  },
  {
    icon: LockKeyhole,
    title: "内部能力不外露",
    description: "普通用户只获得答案,不会看到知识条目、关系图或内部检索过程。",
  },
  {
    icon: Sparkles,
    title: "多专家自动分派",
    description: "文案、运营、营销、客服、选品,不同问题自动路由给对应专家,思路更聚焦。",
  },
];

export default async function Home() {
  const cookieStore = await cookies();
  const session = readUserSession(cookieStore.get(USER_COOKIE)?.value);
  const member =
    session?.authToken && !isAuthTokenExpired(session)
      ? session.displayName || session.email || "已登录"
      : null;

  return (
    <main className="user-shell">
      <nav className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark">砺</span>
          <span>砺知智能</span>
        </Link>
        <div className="topbar-actions">
          {member ? (
            <Link className="member-entry" href="/chat">
              <UserRound size={14} /> {member}
            </Link>
          ) : (
            <>
              <Link className="admin-entry" href="/login">
                登录
              </Link>
              <Link className="register-entry" href="/register">
                注册
              </Link>
            </>
          )}
        </div>
      </nav>

      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow">
            <Sparkles size={15} /> 电商多专家 · 持续学习型智能体
          </span>
          <h1>
            一支越用越聪明的
            <span>电商专家团队。</span>
          </h1>
          <p>
            商品文案、Listing 优化、营销策划、客服售后、选品分析——问题自动分派给对应专家;
            知识库从零起步,每一次真实使用都在让回答更可靠。
          </p>
          <Link className="primary-cta" href="/chat">
            进入工作台 <ArrowRight size={18} />
          </Link>
        </div>

        <div className="growth-visual" aria-label="智能成长过程">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="brain-core">
            <BrainCircuit size={42} />
            <span>持续学习</span>
          </div>
          <span className="signal signal-one">真实问题</span>
          <span className="signal signal-two">自动归类</span>
          <span className="signal signal-three">专家分派</span>
          <span className="signal signal-four">人工确认</span>
        </div>
      </section>

      <section className="specialist-grid">
        {SPECIALISTS.map(({ slug, name, icon: Icon, description }) => (
          <Link className="specialist-tile" href="/chat" key={slug}>
            <span className="icon-box">
              <Icon size={19} />
            </span>
            <strong>{name}</strong>
            <p>{description}</p>
          </Link>
        ))}
      </section>

      <section className="capability-grid">
        {capabilities.map(({ icon: Icon, title, description }) => (
          <article className="capability-card" key={title}>
            <span className="icon-box">
              <Icon size={20} />
            </span>
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>

      <section className="assistant-section">
        <div>
          <span className="eyebrow">现在就试试</span>
          <h2>告诉我你正在解决什么问题</h2>
          <p>
            答案有帮助或需要纠正,都可以直接告诉我。你的反馈会进入受控的改进流程,
            注册后偏好与积累长期保留。
          </p>
        </div>
        <div className="assistant-cta-panel">
          <Link className="primary-cta" href="/chat">
            开始对话 <ArrowRight size={18} />
          </Link>
          <Link className="ghost-cta" href="/register">
            创建账号,让它记住你
          </Link>
        </div>
      </section>
    </main>
  );
}
