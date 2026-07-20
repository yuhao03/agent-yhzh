"use client";

import { CheckCircle2, KeyRound, PlugZap, RotateCcw, Server, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";

import type { ModelProviderConfig } from "@/lib/types";

export function ModelSettings({
  configs,
  onChanged,
}: {
  configs: ModelProviderConfig[];
  onChanged: () => void;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(configs[0]?.id ?? null);
  const [creating, setCreating] = useState(configs.length === 0);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const selected = creating ? null : configs.find((config) => config.id === selectedId) ?? null;

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const values = new FormData(event.currentTarget);
    const apiKey = String(values.get("api_key") ?? "").trim();
    const payload: Record<string, unknown> = {
      name: String(values.get("name") ?? "").trim(),
      provider: values.get("provider"),
      base_url: String(values.get("base_url") ?? "").trim() || null,
      chat_model: String(values.get("chat_model") ?? "").trim(),
      embedding_model: String(values.get("embedding_model") ?? "").trim() || null,
      temperature: Number(values.get("temperature") ?? 0.2),
      max_tokens: Number(values.get("max_tokens") ?? 4096),
      timeout_seconds: Number(values.get("timeout_seconds") ?? 60),
      enabled: values.get("enabled") === "on",
      is_default: values.get("is_default") === "on",
    };
    if (apiKey) payload.api_key = apiKey;
    const endpoint = selected
      ? `/api/admin/backend/model-configs/${selected.id}`
      : "/api/admin/backend/model-configs";
    const response = await fetch(endpoint, {
      method: selected ? "PATCH" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!response.ok) {
      const detail = await response.json().catch(() => null) as { error?: string } | null;
      setMessage(detail?.error ?? "保存失败，请检查地址与模型参数。");
      return;
    }
    const saved = await response.json() as ModelProviderConfig;
    setSelectedId(saved.id);
    setCreating(false);
    setMessage("配置已加密保存，新的 Agent 请求会立即使用该配置。");
    onChanged();
  }

  async function testConnection() {
    if (!selected) return;
    setSaving(true);
    setMessage("正在请求模型服务…");
    const response = await fetch(`/api/admin/backend/model-configs/${selected.id}/test`, {
      method: "POST",
    });
    const result = await response.json() as { success?: boolean; message?: string; error?: string; latency_ms?: number };
    setSaving(false);
    setMessage(
      result.message
        ? `${result.message}${result.latency_ms != null ? `（${result.latency_ms} ms）` : ""}`
        : result.error ?? "连接测试失败。",
    );
    onChanged();
  }

  return <div className="model-settings-layout">
    <aside className="model-config-list">
      <div className="model-list-heading"><strong>模型连接</strong><button onClick={() => { setCreating(true); setSelectedId(null); setMessage(""); }} type="button">+ 新建</button></div>
      {configs.map((config) => <button className={`model-config-card ${!creating && selectedId === config.id ? "active" : ""}`} key={config.id} onClick={() => { setCreating(false); setSelectedId(config.id); setMessage(""); }} type="button">
        <span className="model-config-icon"><Server size={17} /></span>
        <span><strong>{config.name}</strong><small>{config.provider} · {config.chat_model}</small></span>
        {config.is_default ? <em>默认</em> : null}
      </button>)}
      {!configs.length ? <div className="model-empty">还没有模型配置。系统当前使用环境变量或离线降级回答。</div> : null}
    </aside>

    <section className="model-config-editor">
      <div className="model-editor-title"><div><h3>{selected ? "编辑模型连接" : "新增模型连接"}</h3><p>配置只在服务端使用，API Key 不会发送给浏览器。</p></div>{selected?.enabled ? <span className="model-active"><CheckCircle2 size={14} /> 已启用</span> : null}</div>
      <form className="model-config-form" key={selected?.id ?? "new"} onSubmit={save}>
        <div className="model-form-grid">
          <label><span>配置名称</span><input defaultValue={selected?.name ?? "主模型"} name="name" required /></label>
          <label><span>服务商</span><select defaultValue={selected?.provider ?? "openai_compatible"} name="provider"><option value="openai_compatible">OpenAI 兼容接口</option><option value="openai">OpenAI</option><option value="azure">Azure OpenAI</option><option value="anthropic">Anthropic</option><option value="ollama">Ollama</option></select></label>
          <label className="wide"><span>API Base URL</span><div className="input-with-icon"><PlugZap size={15} /><input defaultValue={selected?.base_url ?? ""} name="base_url" placeholder="例如 https://api.example.com/v1" /></div><small>官方 OpenAI 可留空；兼容接口和 Ollama 请填写完整服务地址。</small></label>
          <label><span>聊天模型</span><input defaultValue={selected?.chat_model ?? "gpt-4.1-mini"} name="chat_model" placeholder="模型 ID" required /></label>
          <label><span>Embedding 模型</span><input defaultValue={selected?.embedding_model ?? "local/hash-1536"} name="embedding_model" placeholder="可使用 local/hash-1536" /></label>
          <label className="wide"><span>API Key</span><div className="input-with-icon"><KeyRound size={15} /><input autoComplete="new-password" name="api_key" placeholder={selected?.api_key_configured ? `已配置 ${selected.api_key_hint ?? "••••••"}；留空表示不更换` : "本地 Ollama 可留空"} type="password" /></div></label>
          <label><span>Temperature</span><input defaultValue={selected?.temperature ?? 0.2} max="2" min="0" name="temperature" step="0.1" type="number" /></label>
          <label><span>最大输出 Token</span><input defaultValue={selected?.max_tokens ?? 4096} min="1" name="max_tokens" type="number" /></label>
          <label><span>超时（秒）</span><input defaultValue={selected?.timeout_seconds ?? 60} max="600" min="1" name="timeout_seconds" type="number" /></label>
        </div>
        <div className="model-checks"><label><input defaultChecked={selected?.enabled ?? true} name="enabled" type="checkbox" />启用该连接</label><label><input defaultChecked={selected?.is_default ?? true} name="is_default" type="checkbox" />设为当前空间默认模型</label></div>
        <div className="model-security-note"><ShieldCheck size={18} /><span><strong>密钥安全</strong>API Key 使用服务端加密密钥加密后入库，读取接口只返回掩码；修改、测试和切换都会写入审计日志。</span></div>
        {selected?.last_test_message ? <div className={`connection-result result-${selected.last_test_status ?? "unknown"}`}>{selected.last_test_message}{selected.last_tested_at ? <small>{new Date(selected.last_tested_at).toLocaleString("zh-CN")}</small> : null}</div> : null}
        {message ? <p className="model-message">{message}</p> : null}
        <div className="model-actions">{selected ? <button className="test-connection" disabled={saving} onClick={() => void testConnection()} type="button"><RotateCcw size={15} />测试连接</button> : null}<button className="promote-button" disabled={saving} type="submit">{saving ? "处理中…" : "保存配置"}</button></div>
      </form>
    </section>
  </div>;
}
