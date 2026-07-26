import { Sparkles } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "注册 · 砺知智能" };

export default function RegisterPage() {
  return (
    <main className="auth-shell">
      <section className="auth-brand-panel">
        <Link className="brand" href="/">
          <span className="brand-mark">砺</span>
          <span>砺知智能</span>
        </Link>
        <h1>
          创建账号,
          <br />
          让智能体和你一起成长。
        </h1>
        <p>
          <Sparkles size={15} /> 六位电商专家 · 私有记忆 · 审核后的可靠知识
        </p>
      </section>
      <section className="auth-card">
        <h2>创建账号</h2>
        <p>注册即可获得跨设备的专属记忆与更连贯的协作体验。</p>
        <AuthForm mode="register" />
      </section>
    </main>
  );
}
