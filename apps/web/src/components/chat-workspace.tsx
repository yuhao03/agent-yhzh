"use client";

import {
  CopilotChat,
  UseAgentUpdate,
  useAgent,
  useConfigureSuggestions,
  useCopilotKit,
} from "@copilotkit/react-core/v2";
import { LogOut, NotebookPen, ShieldCheck, Sparkles, UserRound, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PrivacyControls } from "@/components/privacy-controls";
import { SPECIALISTS } from "@/lib/specialists";

type Member = { email: string; displayName: string } | null;

type AgentUiState = {
  active_agent?: string;
  active_agent_name?: string;
};

export function ChatWorkspace({
  member,
  memberExpired = false,
}: {
  member: Member;
  memberExpired?: boolean;
}) {
  const router = useRouter();
  const { copilotkit } = useCopilotKit();
  const { agent } = useAgent({ updates: [UseAgentUpdate.OnStateChanged] });
  const state = (agent?.state ?? {}) as AgentUiState;
  const activeSlug = state.active_agent;
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [notice, setNotice] = useState("");

  useConfigureSuggestions({
    suggestions: SPECIALISTS.map((specialist) => ({
      title: specialist.name.replace("专家", ""),
      message: specialist.prompt,
    })),
    available: "before-first-message",
  });

  useEffect(() => {
    if (!drawerOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setDrawerOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  async function askSpecialist(prompt: string) {
    if (!agent || agent.isRunning) return;
    agent.addMessage({ id: crypto.randomUUID(), role: "user", content: prompt });
    try {
      await copilotkit.runAgent({ agent });
    } catch {
      setNotice("消息发送失败,请稍后再试。");
    }
  }

  async function logout() {
    try {
      const response = await fetch("/api/user/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "logout" }),
      });
      if (!response.ok) throw new Error(`logout failed: ${response.status}`);
      router.push("/");
      router.refresh();
    } catch {
      setNotice("退出登录失败,请检查网络后重试。");
    }
  }

  return (
    <div className="workspace-shell">
      <header className="workspace-topbar">
        <Link className="brand" href="/">
          <span className="brand-mark">砺</span>
          <span>砺知智能</span>
        </Link>
        <div className="workspace-topbar-right">
          {activeSlug && state.active_agent_name ? (
            <span className="active-agent-chip">
              <Sparkles size={13} />
              {state.active_agent_name}正在服务
            </span>
          ) : null}
          <button
            aria-expanded={drawerOpen}
            className="memory-drawer-toggle"
            onClick={() => setDrawerOpen(true)}
            type="button"
          >
            <NotebookPen size={14} />
            记忆与隐私
          </button>
          {member ? (
            <span className="member-chip">
              <UserRound size={14} />
              {member.displayName || member.email}
              <button aria-label="退出登录" onClick={logout} title="退出登录" type="button">
                <LogOut size={14} />
              </button>
            </span>
          ) : (
            <span className="guest-actions">
              <Link href="/login">登录</Link>
              <Link className="guest-register" href="/register">
                注册
              </Link>
            </span>
          )}
        </div>
      </header>

      {memberExpired ? (
        <div className="session-expired-banner" role="status">
          登录已过期,当前以访客身份继续。<Link href="/login">重新登录</Link>
        </div>
      ) : null}
      {notice ? (
        <div className="workspace-notice" role="alert">
          {notice}
          <button aria-label="关闭提示" onClick={() => setNotice("")} type="button">
            <X size={13} />
          </button>
        </div>
      ) : null}

      <div className="workspace-body">
        <aside className="workspace-rail workspace-rail-left">
          <div className="rail-heading">
            <strong>专家团队</strong>
            <span>按问题自动分派</span>
          </div>
          <div className="specialist-list">
            {SPECIALISTS.map(({ slug, name, icon: Icon, description, prompt }) => (
              <button
                className={`specialist-card ${activeSlug === slug ? "active" : ""}`}
                key={slug}
                onClick={() => void askSpecialist(prompt)}
                type="button"
              >
                <span className="specialist-icon">
                  <Icon size={17} />
                </span>
                <span>
                  <strong>{name}</strong>
                  <small>{description}</small>
                </span>
              </button>
            ))}
          </div>
          {!member ? (
            <div className="guest-banner">
              <ShieldCheck size={15} />
              <p>
                当前是访客模式。<Link href="/register">注册</Link>
                后,你的偏好与积累会长期保留并跨设备同步。
              </p>
            </div>
          ) : null}
        </aside>

        <main className="workspace-chat">
          <div aria-label="专家团队" className="specialist-strip" role="group">
            {SPECIALISTS.map(({ slug, name, icon: Icon, prompt }) => (
              <button
                className={`specialist-chip ${activeSlug === slug ? "active" : ""}`}
                key={slug}
                onClick={() => void askSpecialist(prompt)}
                type="button"
              >
                <Icon size={13} />
                {name}
              </button>
            ))}
          </div>
          <CopilotChat
            labels={{
              chatInputPlaceholder: "描述你的问题,系统会自动分派给合适的专家…",
              welcomeMessageText: "你好,我是砺知智能。电商相关的问题会自动交给对应专家处理,你想解决什么问题?",
              chatDisclaimerText: "回答可能不完整,重要信息请结合实际情况确认。",
              modalHeaderTitle: "砺知智能助手",
            }}
          />
        </main>

        {drawerOpen ? (
          <button
            aria-label="关闭记忆与隐私面板"
            className="drawer-backdrop"
            onClick={() => setDrawerOpen(false)}
            type="button"
          />
        ) : null}
        <aside className={`workspace-rail workspace-rail-right ${drawerOpen ? "open" : ""}`}>
          <div className="rail-heading">
            <strong>记忆与隐私</strong>
            <span>由你掌控</span>
            <button
              aria-label="关闭面板"
              className="memory-drawer-close"
              onClick={() => setDrawerOpen(false)}
              type="button"
            >
              <X size={15} />
            </button>
          </div>
          <PrivacyControls />
        </aside>
      </div>
    </div>
  );
}
