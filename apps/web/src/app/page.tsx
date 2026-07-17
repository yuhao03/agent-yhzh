import Link from "next/link";
import { ArrowRight, BrainCircuit, LockKeyhole, Sparkles } from "lucide-react";

import { UserAssistant } from "@/components/user-assistant";

const capabilities = [
  {
    icon: BrainCircuit,
    title: "越用越懂业务",
    description: "从真实问题和反馈中发现高价值信息，经确认后用于后续回答。",
  },
  {
    icon: LockKeyhole,
    title: "内部能力不外露",
    description: "普通用户只获得答案，不会看到知识条目、关系图或内部检索过程。",
  },
  {
    icon: Sparkles,
    title: "回答持续变可靠",
    description: "不确定时明确说明边界，已验证的信息会逐步带来更稳定的体验。",
  },
];

export default function Home() {
  return (
    <main className="user-shell">
      <nav className="topbar">
        <Link className="brand" href="/">
          <span className="brand-mark">砺</span>
          <span>砺知智能</span>
        </Link>
        <Link className="admin-entry" href="/admin/login">
          管理员入口
        </Link>
      </nav>

      <section className="hero-grid">
        <div className="hero-copy">
          <span className="eyebrow"><Sparkles size={15} /> 持续学习型智能助手</span>
          <h1>
            把每一次真实使用，
            <span>沉淀成下一次更好的回答。</span>
          </h1>
          <p>
            初始知识可以为空。系统会从问题、纠正和反馈中发现候选经验，经管理员审核后再成为可靠能力。
          </p>
          <a className="primary-cta" href="#assistant">
            开始提问 <ArrowRight size={18} />
          </a>
        </div>

        <div className="growth-visual" aria-label="智能成长过程">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <div className="brain-core">
            <BrainCircuit size={42} />
            <span>持续学习</span>
          </div>
          <span className="signal signal-one">真实问题</span>
          <span className="signal signal-two">有效纠正</span>
          <span className="signal signal-three">可靠回答</span>
          <span className="signal signal-four">人工确认</span>
        </div>
      </section>

      <section className="capability-grid">
        {capabilities.map(({ icon: Icon, title, description }) => (
          <article className="capability-card" key={title}>
            <span className="icon-box"><Icon size={20} /></span>
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>

      <section className="assistant-section" id="assistant">
        <div>
          <span className="eyebrow">现在就试试</span>
          <h2>告诉我你正在解决什么问题</h2>
          <p>答案有帮助或需要纠正，都可以直接告诉我。你的反馈会进入受控的改进流程。</p>
        </div>
        <UserAssistant />
      </section>
    </main>
  );
}
