"use client";

import { KeyRound, Loader2, Mail, UserRound } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");
    const values = new FormData(event.currentTarget);
    const response = await fetch("/api/user/auth", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        action: mode,
        email: String(values.get("email") ?? ""),
        password: String(values.get("password") ?? ""),
        displayName: String(values.get("displayName") ?? ""),
      }),
    }).catch(() => null);
    setSubmitting(false);
    if (!response) {
      setError("网络异常,请稍后再试。");
      return;
    }
    const data = (await response.json().catch(() => null)) as {
      error?: string;
    } | null;
    if (!response.ok) {
      setError(data?.error ?? "操作失败,请稍后再试。");
      return;
    }
    router.push("/chat");
    router.refresh();
  }

  return (
    <form className="auth-form" onSubmit={submit}>
      {mode === "register" ? (
        <label>
          <span>昵称</span>
          <div className="input-with-icon">
            <UserRound size={15} />
            <input
              autoComplete="nickname"
              maxLength={60}
              name="displayName"
              placeholder="团队会看到的名字"
            />
          </div>
        </label>
      ) : null}
      <label>
        <span>邮箱</span>
        <div className="input-with-icon">
          <Mail size={15} />
          <input
            autoComplete="email"
            name="email"
            placeholder="you@example.com"
            required
            type="email"
          />
        </div>
      </label>
      <label>
        <span>密码</span>
        <div className="input-with-icon">
          <KeyRound size={15} />
          <input
            autoComplete={mode === "register" ? "new-password" : "current-password"}
            minLength={mode === "register" ? 8 : 1}
            name="password"
            placeholder={mode === "register" ? "至少 8 位,含字母和数字" : "输入密码"}
            required
            type="password"
          />
        </div>
      </label>
      {error ? <p className="auth-error">{error}</p> : null}
      <button className="auth-submit" disabled={submitting} type="submit">
        {submitting ? <Loader2 className="spin" size={16} /> : null}
        {mode === "register" ? "创建账号" : "登录"}
      </button>
      <p className="auth-switch">
        {mode === "register" ? (
          <>
            已有账号?<Link href="/login">直接登录</Link>
          </>
        ) : (
          <>
            还没有账号?<Link href="/register">立即注册</Link>
          </>
        )}
        <Link className="auth-guest" href="/chat">
          先以访客身份体验 →
        </Link>
      </p>
    </form>
  );
}
