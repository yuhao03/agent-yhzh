"use client";

import { FormEvent, useEffect, useState } from "react";

type Memory = {
  id: string;
  memory_type: string;
  content: string;
  expires_at: string | null;
};

export function PrivacyControls() {
  const [consent, setConsent] = useState(false);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    void fetch("/api/user/session")
      .then((response) => response.json())
      .then((data: { learningConsent: boolean }) => setConsent(data.learningConsent));
  }, []);

  async function loadMemories() {
    const response = await fetch("/api/user/memories", { cache: "no-store" });
    if (response.ok) setMemories(await response.json() as Memory[]);
  }

  async function toggleConsent(next: boolean) {
    const response = await fetch("/api/user/session", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ learningConsent: next }),
    });
    if (response.ok) {
      setConsent(next);
      setMessage(next ? "已同意：后续互动可在脱敏后进入受控学习流程。" : "已关闭：后续互动不会用于学习。");
      if (!next) setMemories([]);
    }
  }

  async function saveMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    const response = await fetch("/api/user/memories", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        memory_type: form.get("memory_type"),
        content: form.get("content"),
        consent: true,
        expires_in_days: 180,
      }),
    });
    if (response.ok) {
      formElement.reset();
      await loadMemories();
      setMessage("偏好已保存，只用于你的当前产品体验。");
    } else setMessage("请先开启学习与个性化同意。");
  }

  async function removeMemory(id: string) {
    await fetch(`/api/user/memories/${id}`, { method: "DELETE" });
    await loadMemories();
  }

  async function resetAll() {
    await fetch("/api/user/memories", { method: "DELETE" });
    setMemories([]);
    setMessage("你的私有记忆已清空。");
  }

  return <div className="privacy-controls">
    <button className="privacy-toggle" onClick={() => { const next = !open; setOpen(next); if (next) void loadMemories(); }} type="button">隐私与个性化设置</button>
    {open ? <div className="privacy-panel">
      <label className="consent-row"><input checked={consent} onChange={(event) => void toggleConsent(event.target.checked)} type="checkbox" /><span><strong>允许受控学习与个性化</strong><small>互动先脱敏，仅达到多用户阈值并经管理员审核后才会成为公共知识。个人偏好始终隔离保存。</small></span></label>
      <form className="memory-form" onSubmit={saveMemory}><select name="memory_type"><option value="preference">表达偏好</option><option value="workflow">工作习惯</option><option value="profile">个人背景</option></select><input disabled={!consent} name="content" placeholder="例如：回答尽量简洁，先给结论" required /><button disabled={!consent} type="submit">保存</button></form>
      <div className="memory-list">{memories.map((memory) => <div key={memory.id}><span>{memory.content}</span><button onClick={() => void removeMemory(memory.id)} type="button">删除</button></div>)}{!memories.length ? <small>还没有保存任何个人偏好。</small> : null}</div>
      {memories.length ? <button className="reset-memory" onClick={() => void resetAll()} type="button">清空全部个人记忆</button> : null}
      {message ? <p className="privacy-message">{message}</p> : null}
    </div> : null}
  </div>;
}
