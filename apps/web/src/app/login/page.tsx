import { Sparkles } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { AuthForm } from "@/components/auth-form";

export const metadata: Metadata = { title: "登录 · 砺知智能" };

export default function LoginPage() {
  return (
    <main className="auth-shell">
      <section className="auth-brand-panel">
        <Link className="brand" href="/">
          <span className="brand-mark">砺</span>
          <span>砺知智能</span>
        </Link>
        <h1>
          登录后,你的偏好与积累
          <br />
          都会被记住。
        </h1>
        <p>
          <Sparkles size={15} /> 专属记忆 · 越用越懂你的电商专家团队
        </p>
      </section>
      <section className="auth-card">
        <h2>欢迎回来</h2>
        <p>使用注册邮箱登录,继续你的工作台。</p>
        <AuthForm mode="login" />
      </section>
    </main>
  );
}
