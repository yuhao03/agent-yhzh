"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  type RowData,
  type SortingState,
  type Table as TableInstance,
  useReactTable,
} from "@tanstack/react-table";
import {
  BarChart3,
  BookOpenText,
  FileText,
  GitFork,
  History,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  Network,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { KnowledgeGraph } from "@/components/knowledge-graph";
import { ModelSettings } from "@/components/model-settings";
import { QualityChart } from "@/components/quality-chart";
import type {
  AdminDashboardPayload,
  AuditEvent,
  CategoryOption,
  KnowledgeCandidate,
  KnowledgeDocument,
  KnowledgeItem,
  KnowledgeRelation,
  UserAccount,
} from "@/lib/types";

type View = "overview" | "candidates" | "knowledge" | "graph" | "documents" | "relations" | "users" | "models" | "audits";
type Density = "compact" | "comfortable";

const candidateHelper = createColumnHelper<KnowledgeCandidate>();
const knowledgeHelper = createColumnHelper<KnowledgeItem>();
const documentHelper = createColumnHelper<KnowledgeDocument>();
const relationHelper = createColumnHelper<KnowledgeRelation>();
const auditHelper = createColumnHelper<AuditEvent>();
const userHelper = createColumnHelper<UserAccount>();

const FALLBACK_CATEGORIES: CategoryOption[] = [
  { slug: "general", name: "通用知识", description: "" },
];

function categoryName(categories: CategoryOption[], slug: string) {
  return categories.find((category) => category.slug === slug)?.name ?? slug;
}

export function AdminDashboard({ data, error }: { data: AdminDashboardPayload | null; error: string }) {
  const router = useRouter();
  const [view, setView] = useState<View>("overview");
  const [reviewing, setReviewing] = useState<KnowledgeCandidate | null>(null);
  const [creating, setCreating] = useState(false);
  const [showRelationForm, setShowRelationForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const [panelError, setPanelError] = useState("");
  const [toast, setToast] = useState("");
  const [filter, setFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [density, setDensity] = useState<Density>("comfortable");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);
  const [namingView, setNamingView] = useState(false);
  const [viewName, setViewName] = useState("");
  const toastTimer = useRef<number | null>(null);

  const categories = data?.categories?.length ? data.categories : FALLBACK_CATEGORIES;

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(""), 3200);
  }, []);
  useEffect(() => () => { if (toastTimer.current) window.clearTimeout(toastTimer.current); }, []);

  const switchView = useCallback((next: View) => {
    setView(next);
    setFilter("");
    setTypeFilter("all");
    setSorting([]);
    setPanelError("");
    setNamingView(false);
    setViewName("");
  }, []);

  useEffect(() => {
    if (!(detail || reviewing || creating || showRelationForm || namingView)) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== "Escape") return;
      if (detail) setDetail(null);
      else if (reviewing) { setReviewing(null); setActionError(""); }
      else if (creating) { setCreating(false); setActionError(""); }
      else if (showRelationForm) { setShowRelationForm(false); setActionError(""); }
      else if (namingView) { setNamingView(false); setViewName(""); }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [detail, reviewing, creating, showRelationForm, namingView]);

  const filteredKnowledge = useMemo(
    () => (data?.knowledge ?? []).filter((item) => typeFilter === "all" || item.category === typeFilter),
    [data?.knowledge, typeFilter],
  );
  const filteredCandidates = useMemo(
    () => (data?.candidates ?? []).filter((item) => typeFilter === "all" || item.category === typeFilter),
    [data?.candidates, typeFilter],
  );

  const candidateColumns = useMemo(() => [
    candidateHelper.accessor("title", { header: "候选知识", cell: (info) => <span className="cell-title">{info.getValue()}</span> }),
    candidateHelper.accessor("category", { header: "分类", cell: (info) => <span className="category-pill">{categoryName(categories, info.getValue())}</span> }),
    candidateHelper.accessor("status", { header: "状态", cell: (info) => <Status value={info.getValue()} /> }),
    candidateHelper.accessor("occurrence_count", { header: "出现次数" }),
    candidateHelper.accessor("distinct_user_count", { header: "独立用户" }),
    candidateHelper.accessor("score", { header: "可信分", cell: (info) => `${Math.round(info.getValue() * 100)}%` }),
    candidateHelper.display({ id: "actions", header: "操作", cell: (info) => <button className="promote-button" onClick={() => { setActionError(""); setReviewing(info.row.original); }} type="button">审核</button> }),
  ], [categories]);
  const knowledgeColumns = useMemo(() => [
    knowledgeHelper.accessor("title", { header: "名称", cell: (info) => <button className="table-link" onClick={() => openDetail(info.row.original.id)} type="button">{info.getValue()}</button> }),
    knowledgeHelper.accessor("content", { header: "确认内容", cell: (info) => <span className="cell-content">{info.getValue()}</span> }),
    knowledgeHelper.accessor("category", { header: "分类", cell: (info) => <span className="category-pill">{categoryName(categories, info.getValue())}</span> }),
    knowledgeHelper.accessor("knowledge_type", { header: "类型" }),
    knowledgeHelper.accessor("version", { header: "版本", cell: (info) => `v${info.getValue()}` }),
    knowledgeHelper.accessor("source_kind", { header: "来源" }),
    knowledgeHelper.accessor("status", { header: "状态", cell: (info) => <Status value={info.getValue()} /> }),
  ], [categories]);
  const documentColumns = useMemo(() => [
    documentHelper.accessor("filename", { header: "文档", cell: (info) => <span className="cell-title">{info.getValue()}</span> }),
    documentHelper.accessor("mime_type", { header: "类型" }),
    documentHelper.accessor("byte_size", { header: "大小", cell: (info) => `${Math.ceil(info.getValue() / 1024)} KB` }),
    documentHelper.accessor("parser_status", { header: "解析状态", cell: (info) => <Status value={info.getValue()} /> }),
    documentHelper.accessor("created_at", { header: "上传时间", cell: (info) => formatTime(info.getValue()) }),
  ], []);
  const relationColumns = useMemo(() => [
    relationHelper.accessor("relation_type", { header: "关系类型", cell: (info) => <span className="cell-title">{info.getValue()}</span> }),
    relationHelper.accessor("source_id", { header: "源知识", cell: (info) => titleFor(data, info.getValue()) }),
    relationHelper.accessor("target_id", { header: "目标知识", cell: (info) => titleFor(data, info.getValue()) }),
    relationHelper.accessor("confidence", { header: "置信度", cell: (info) => `${Math.round(info.getValue() * 100)}%` }),
    relationHelper.accessor("status", { header: "状态", cell: (info) => <Status value={info.getValue()} /> }),
  ], [data]);
  const auditColumns = useMemo(() => [
    auditHelper.accessor("created_at", { header: "时间", cell: (info) => formatTime(info.getValue()) }),
    auditHelper.accessor("actor_ref", { header: "操作者" }),
    auditHelper.accessor("action", { header: "动作" }),
    auditHelper.accessor("object_type", { header: "对象" }),
    auditHelper.accessor("object_id", { header: "对象 ID", cell: (info) => <span className="mono">{info.getValue()?.slice(0, 12) ?? "-"}</span> }),
  ], []);
  const toggleUserStatus = useCallback(async (account: UserAccount) => {
    const next = account.status === "disabled" ? "active" : "disabled";
    if (next === "disabled" && !window.confirm(`确认禁用 ${account.email}?其所有登录会话将立即失效。`)) return;
    const response = await fetch(`/api/admin/backend/users/${account.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: next }),
    });
    if (!response.ok) setPanelError("用户状态更新失败,请稍后再试。");
    else {
      setPanelError("");
      showToast(next === "disabled" ? `已禁用 ${account.email},其登录会话已全部失效。` : `已启用 ${account.email}。`);
      router.refresh();
    }
  }, [router, showToast]);

  const userColumns = useMemo(() => [
    userHelper.accessor("email", { header: "邮箱", cell: (info) => <span className="cell-title">{info.getValue()}</span> }),
    userHelper.accessor("display_name", { header: "昵称" }),
    userHelper.accessor("status", { header: "状态", cell: (info) => <Status value={info.getValue()} /> }),
    userHelper.accessor("last_login_at", { header: "最近登录", cell: (info) => (info.getValue() ? formatTime(info.getValue()!) : "从未登录") }),
    userHelper.accessor("created_at", { header: "注册时间", cell: (info) => formatTime(info.getValue()) }),
    userHelper.display({
      id: "actions",
      header: "操作",
      cell: (info) => {
        const account = info.row.original;
        const disabled = account.status === "disabled";
        return (
          <button
            className={disabled ? "promote-button" : "danger-button"}
            onClick={() => void toggleUserStatus(account)}
            type="button"
          >
            {disabled ? "启用" : "禁用"}
          </button>
        );
      },
    }),
  ], [toggleUserStatus]);

  const tables = {
    candidates: useGrid(filteredCandidates, candidateColumns, filter, sorting, setSorting),
    knowledge: useGrid(filteredKnowledge, knowledgeColumns, filter, sorting, setSorting),
    documents: useGrid(data?.documents ?? [], documentColumns, filter, sorting, setSorting),
    relations: useGrid(data?.relations ?? [], relationColumns, filter, sorting, setSorting),
    audits: useGrid(data?.audits ?? [], auditColumns, filter, sorting, setSorting),
    users: useGrid(data?.users ?? [], userColumns, filter, sorting, setSorting),
  };

  async function logout() {
    await fetch("/api/admin/session", { method: "DELETE" });
    router.replace("/admin/login");
    router.refresh();
  }

  async function openDetail(id: string) {
    const response = await fetch(`/api/admin/backend/knowledge/${id}`);
    if (response.ok) setDetail(await response.json() as Record<string, unknown>);
  }

  async function submitKnowledge(event: FormEvent<HTMLFormElement>, mode: "promote" | "create") {
    event.preventDefault();
    setSaving(true);
    setActionError("");
    const values = new FormData(event.currentTarget);
    const payload = {
      title: String(values.get("title") ?? "").trim(),
      content: String(values.get("content") ?? "").trim(),
      knowledge_type: String(values.get("knowledge_type") ?? "faq"),
      category: String(values.get("category") ?? "general"),
      sensitivity: "internal",
      agent_scope: [String(values.get("agent_scope") ?? "default").trim() || "default"],
      properties: {},
      publish: true,
      review_reason: String(values.get("review_reason") ?? "管理员核验后发布").trim(),
    };
    const endpoint = mode === "promote" && reviewing
      ? `/api/admin/candidates/${reviewing.id}/promote`
      : "/api/admin/knowledge";
    const response = await fetch(endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setSaving(false);
    if (!response.ok) { setActionError("保存失败，请检查字段与后端状态。"); return; }
    setReviewing(null);
    setCreating(false);
    showToast(mode === "promote" ? "候选已审核通过并发布为正式知识。" : "知识已发布。");
    router.refresh();
  }

  async function rejectCandidate(reason: string) {
    if (!reviewing) return;
    setSaving(true);
    setActionError("");
    const response = await fetch(`/api/admin/backend/candidates/${reviewing.id}/reject`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    setSaving(false);
    if (!response.ok) { setActionError("驳回失败，请稍后再试。"); return; }
    setReviewing(null);
    showToast("候选已驳回，不会进入正式知识库。");
    router.refresh();
  }

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setSaving(true);
    setPanelError("");
    const form = new FormData(formElement);
    const response = await fetch("/api/admin/backend/documents", { method: "POST", body: form });
    setSaving(false);
    if (!response.ok) setPanelError("导入失败，请使用 txt、md、html、pdf 或 docx 文件。");
    else {
      formElement.reset();
      showToast("文档已上传，解析结果会进入候选池等待审核。");
      router.refresh();
    }
  }

  async function submitRelation(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    const values = new FormData(event.currentTarget);
    const payload = {
      source_id: values.get("source_id"), target_id: values.get("target_id"),
      relation_type: values.get("relation_type"), direction: "directed",
      weight: 1, confidence: 1, evidence_quote: values.get("evidence_quote"), publish: true,
    };
    const response = await fetch("/api/admin/backend/relations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    setSaving(false);
    if (response.ok) { setShowRelationForm(false); showToast("知识关系已创建。"); router.refresh(); }
    else setActionError("关系创建失败，请确认两个知识条目不同且证据完整。");
  }

  async function saveCurrentView() {
    const name = viewName.trim();
    if (!name) return;
    setPanelError("");
    const response = await fetch("/api/admin/backend/views", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, view_type: view === "graph" ? "graph" : view === "overview" ? "dashboard" : "grid", configuration: { view, filter, typeFilter, density, sorting }, is_shared: false }) });
    if (!response.ok) { setPanelError("视图保存失败，请稍后再试。"); return; }
    setNamingView(false);
    setViewName("");
    showToast(`视图「${name}」已保存。`);
    router.refresh();
  }

  const stats = data?.stats;
  const statCards = [
    ["已发布", stats?.published_knowledge ?? 0], ["草稿", stats?.draft_knowledge ?? 0],
    ["待审核", stats?.pending_review ?? 0], ["互动信号", stats?.interaction_events ?? 0],
    ["文档", stats?.documents ?? 0], ["关系", stats?.relations ?? 0],
  ];

  return <main className="admin-shell">
    <aside className="admin-sidebar">
      <div className="brand"><span className="brand-mark">砺</span><span>知识控制台</span></div>
      <nav className="admin-nav">
        <Nav icon={LayoutDashboard} label="运营总览" active={view === "overview"} onClick={() => switchView("overview")} />
        <Nav icon={MessageSquareText} label="候选审核" active={view === "candidates"} onClick={() => switchView("candidates")} />
        <Nav icon={BookOpenText} label="知识资产" active={view === "knowledge"} onClick={() => switchView("knowledge")} />
        <Nav icon={GitFork} label="关系图谱" active={view === "graph"} onClick={() => switchView("graph")} />
        <Nav icon={FileText} label="文档导入" active={view === "documents"} onClick={() => switchView("documents")} />
        <Nav icon={Network} label="关系管理" active={view === "relations"} onClick={() => switchView("relations")} />
        <Nav icon={Users} label="用户管理" active={view === "users"} onClick={() => switchView("users")} />
        <Nav icon={Settings2} label="模型配置" active={view === "models"} onClick={() => switchView("models")} />
        <Nav icon={History} label="审计日志" active={view === "audits"} onClick={() => switchView("audits")} />
      </nav>
      <div className="admin-sidebar-foot">内部管理系统<br />普通用户无入口、无接口权限</div>
    </aside>
    <section className="admin-main">
      <header className="admin-header"><div><h1>知识成长工作台</h1><p>空库起步，用户信号经脱敏、聚合和审核后才会成为正式知识。</p></div><button className="logout-button" onClick={logout} type="button"><LogOut size={15} /> 退出</button></header>
      {error ? <div className="error-banner">{error}</div> : null}
      <section className="stats-grid stats-six">{statCards.map(([label, value]) => <article className="stat-card" key={label}><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong></article>)}</section>

      {view === "overview" ? <section className="overview-grid">
        <article className="admin-panel chart-panel"><div className="panel-toolbar"><div><h2>近 14 天知识质量趋势</h2><p>互动、候选和正式发布的变化。</p></div><BarChart3 color="#147a52" /></div><QualityChart data={data?.trends ?? []} /></article>
        <article className="admin-panel governance-panel"><div className="panel-toolbar"><div><h2>治理闭环</h2><p>所有增长都经过同一条受控路径。</p></div><ShieldCheck color="#147a52" /></div><div className="governance-steps"><span>1 用户同意</span><span>2 自动脱敏</span><span>3 自动归类</span><span>4 多用户聚合</span><span>5 管理员审核</span><span>6 发布与版本化</span></div><div className="boundary-note"><strong>用户侧边界</strong><p>普通用户只感受到回答更贴合，不可浏览、搜索或导出知识库；私有记忆只能由本人查看和删除。</p></div></article>
        <article className="admin-panel category-panel"><div className="panel-toolbar"><div><h2>知识分类分布</h2><p>子 Agent 按分类检索,分布越均衡覆盖越全面。</p></div></div><CategoryDistribution categories={categories} stats={stats?.categories ?? {}} /></article>
      </section> : null}

      {view !== "overview" ? <section className="admin-panel">
        <div className="panel-toolbar admin-grid-toolbar"><div><h2>{viewTitle(view)}</h2><p>{viewDescription(view)}</p></div><div className="toolbar-actions">
          {!["graph", "models"].includes(view) ? <label className="search-box"><Search size={15} /><input aria-label="筛选表格" onChange={(event) => setFilter(event.target.value)} placeholder="筛选当前视图" value={filter} /></label> : null}
          {["knowledge", "candidates"].includes(view) ? <select aria-label="知识分类筛选" onChange={(event) => setTypeFilter(event.target.value)} value={typeFilter}><option value="all">全部分类</option>{categories.map((category) => <option key={category.slug} value={category.slug}>{category.name}</option>)}</select> : null}
          {!["graph", "models"].includes(view) ? <button className="icon-action" onClick={() => setDensity(density === "compact" ? "comfortable" : "compact")} title="切换密度" type="button"><SlidersHorizontal size={16} /></button> : null}
          {namingView
            ? <form className="save-view-form" onSubmit={(event) => { event.preventDefault(); void saveCurrentView(); }}>
                <input aria-label="视图名称" autoFocus maxLength={60} onChange={(event) => setViewName(event.target.value)} placeholder="视图名称" value={viewName} />
                <button className="secondary-action" disabled={!viewName.trim()} type="submit">保存</button>
                <button className="cancel-button" onClick={() => { setNamingView(false); setViewName(""); }} type="button">取消</button>
              </form>
            : <button className="secondary-action" onClick={() => setNamingView(true)} type="button">保存视图</button>}
          {view === "knowledge" ? <button className="promote-button" onClick={() => { setActionError(""); setCreating(true); }} type="button">+ 新增知识</button> : null}
          {view === "relations" ? <button className="promote-button" onClick={() => { setActionError(""); setShowRelationForm(true); }} type="button">+ 新增关系</button> : null}
        </div></div>
        {panelError ? <div className="error-banner panel-error">{panelError}</div> : null}
        {view === "candidates" ? <DataTable density={density} table={tables.candidates} /> : null}
        {view === "knowledge" ? <DataTable density={density} table={tables.knowledge} /> : null}
        {view === "users" ? <DataTable density={density} table={tables.users} /> : null}
        {view === "graph" && data ? <KnowledgeGraph categories={categories} graph={data.graph} onSelectNode={(id) => void openDetail(id)} /> : null}
        {view === "documents" ? <><form className="upload-row" onSubmit={uploadDocument}><input accept=".txt,.md,.html,.htm,.pdf,.docx" name="file" required type="file" /><button className="promote-button" disabled={saving} type="submit">{saving ? "导入中…" : "上传并解析"}</button><span>解析结果先进入候选池，不会自动发布。</span></form><DataTable density={density} table={tables.documents} /></> : null}
        {view === "relations" ? <DataTable density={density} table={tables.relations} /> : null}
        {view === "models" ? <ModelSettings configs={data?.modelConfigs ?? []} onChanged={() => router.refresh()} /> : null}
        {view === "audits" ? <DataTable density={density} table={tables.audits} /> : null}
      </section> : null}
      {data?.views.length ? <div className="saved-views"><strong>已保存视图</strong>{data.views.map((item) => <button key={item.id} onClick={() => { const config = item.configuration as { view?: View; filter?: string; typeFilter?: string; density?: Density; sorting?: SortingState }; if (config.view) setView(config.view); setFilter(config.filter ?? ""); setTypeFilter(config.typeFilter ?? "all"); setDensity(config.density ?? "comfortable"); setSorting(config.sorting ?? []); }} type="button">{item.name}</button>)}</div> : null}
    </section>

    {toast ? <div className="action-toast" role="status">{toast}</div> : null}
    {reviewing ? <KnowledgeFormModal candidate={reviewing} categories={categories} error={actionError} mode="promote" onClose={() => { setReviewing(null); setActionError(""); }} onReject={(reason) => void rejectCandidate(reason)} onSubmit={(event) => submitKnowledge(event, "promote")} saving={saving} /> : null}
    {creating ? <KnowledgeFormModal categories={categories} error={actionError} mode="create" onClose={() => { setCreating(false); setActionError(""); }} onSubmit={(event) => submitKnowledge(event, "create")} saving={saving} /> : null}
    {showRelationForm && data ? <RelationModal items={data.knowledge} onClose={() => { setShowRelationForm(false); setActionError(""); }} onSubmit={submitRelation} saving={saving} error={actionError} /> : null}
    {detail ? <div className="detail-backdrop" onClick={() => setDetail(null)} role="presentation"><aside className="detail-drawer" onClick={(event) => event.stopPropagation()}><button aria-label="关闭详情" className="drawer-close" onClick={() => setDetail(null)} type="button">×</button><KnowledgeDetailView categories={categories} detail={detail} /></aside></div> : null}
  </main>;
}

type KnowledgeDetailPayload = {
  item?: KnowledgeItem;
  versions?: Array<{ id: string; version: number; change_kind: string; actor_ref: string; created_at: string }>;
  evidence?: Array<{ id: string; source_kind: string; quote: string; confidence: number; created_at: string }>;
  reviews?: Array<{ id: string; decision: string | null; reason: string | null; reviewer_ref: string | null; created_at: string }>;
  relations?: Array<{ id: string; relation_type: string; status: string }>;
};

function KnowledgeDetailView({ categories, detail }: { categories: CategoryOption[]; detail: Record<string, unknown> }) {
  const payload = detail as KnowledgeDetailPayload;
  const item = payload.item;
  if (!item) return <p className="drawer-empty">详情加载失败。</p>;
  return <div className="detail-content">
    <header className="detail-head">
      <h2>{item.title}</h2>
      <div className="detail-meta">
        <span className="category-pill">{categoryName(categories, item.category)}</span>
        <Status value={item.status} />
        <span className="detail-version">v{item.version}</span>
        <span className="detail-source">{item.source_kind}</span>
      </div>
    </header>
    <section className="detail-section"><h3>已核验内容</h3><p className="detail-body-text">{item.content}</p></section>
    {payload.evidence?.length ? <section className="detail-section"><h3>证据({payload.evidence.length})</h3><ul>{payload.evidence.slice(0, 6).map((entry) => <li key={entry.id}><em>{entry.source_kind}</em> · 置信 {Math.round(entry.confidence * 100)}%<p>{entry.quote.slice(0, 220)}{entry.quote.length > 220 ? "…" : ""}</p></li>)}</ul></section> : null}
    {payload.reviews?.length ? <section className="detail-section"><h3>审核记录</h3><ul>{payload.reviews.slice(0, 6).map((entry) => <li key={entry.id}><em>{entry.decision ?? "待定"}</em> · {entry.reviewer_ref ?? "-"} · {formatTime(entry.created_at)}<p>{entry.reason ?? ""}</p></li>)}</ul></section> : null}
    {payload.versions?.length ? <section className="detail-section"><h3>版本历史</h3><ul>{payload.versions.slice(0, 8).map((entry) => <li key={entry.id}><em>v{entry.version}</em> · {entry.change_kind} · {entry.actor_ref} · {formatTime(entry.created_at)}</li>)}</ul></section> : null}
    {payload.relations?.length ? <section className="detail-section"><h3>关联关系({payload.relations.length})</h3><ul>{payload.relations.slice(0, 8).map((entry) => <li key={entry.id}><em>{entry.relation_type}</em> · {entry.status}</li>)}</ul></section> : null}
  </div>;
}

function CategoryDistribution({ categories, stats }: { categories: CategoryOption[]; stats: Record<string, number> }) {
  const total = Object.values(stats).reduce((sum, value) => sum + value, 0);
  if (!total) return <div className="empty-state"><div><strong>知识库还是空的</strong>随着用户使用与审核发布，分类分布会在这里呈现。</div></div>;
  const max = Math.max(...Object.values(stats), 1);
  return <div className="category-bars">
    {categories.map((category) => {
      const value = stats[category.slug] ?? 0;
      return <div className="category-bar-row" key={category.slug}>
        <span className="category-bar-label">{category.name}</span>
        <div className="category-bar-track"><div className="category-bar-fill" style={{ width: `${Math.max(4, (value / max) * 100)}%`, opacity: value ? 1 : 0.25 }} /></div>
        <span className="category-bar-value">{value}</span>
      </div>;
    })}
  </div>;
}

type GridOptions<TData extends RowData> = Parameters<typeof useReactTable<TData>>[0];

function useGrid<TData extends RowData>(data: TData[], columns: GridOptions<TData>["columns"], filter: string, sorting: SortingState, setSorting: (value: SortingState | ((old: SortingState) => SortingState)) => void) {
  // TanStack Table returns mutable helpers by design.
  // eslint-disable-next-line react-hooks/incompatible-library
  return useReactTable({ data, columns, state: { globalFilter: filter, sorting }, onSortingChange: setSorting, getCoreRowModel: getCoreRowModel(), getFilteredRowModel: getFilteredRowModel(), getSortedRowModel: getSortedRowModel() });
}

function Nav({ icon: Icon, label, active, onClick }: { icon: typeof LayoutDashboard; label: string; active: boolean; onClick: () => void }) {
  return <button className={`admin-nav-item ${active ? "active" : ""}`} onClick={onClick} title={label} type="button"><Icon size={18} /><span>{label}</span></button>;
}
function Status({ value }: { value: string }) { return <span className={`status-pill status-${value}`}>{({ pending_review: "待审核", observed: "观察中", published: "已发布", completed: "已完成", processing: "处理中", queued: "排队中", failed: "失败", draft: "草稿", active: "正常", disabled: "已禁用", promoted: "已转正", rejected: "已驳回" } as Record<string, string>)[value] ?? value}</span>; }
function formatTime(value: string) { return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); }
function titleFor(data: AdminDashboardPayload | null, id: string) { return data?.knowledge.find((item) => item.id === id)?.title ?? id.slice(0, 8); }
function viewTitle(view: View) { return ({ candidates: "互动候选池", knowledge: "知识资产表", graph: "知识关系图谱", documents: "文档导入与解析", relations: "显式关系管理", users: "用户账号管理", models: "LLM 与 Embedding 配置", audits: "不可变审计记录", overview: "运营总览" } as Record<View, string>)[view]; }
function viewDescription(view: View) { return ({ candidates: "自动归类后,达到次数与独立用户阈值即进入人工审核。", knowledge: "支持按分类筛选、排序、密度、保存视图及查看版本证据。", graph: "实线为显式关系，虚线仅作为辅助探索;节点颜色对应知识分类。", documents: "文档被切块、自动归类、向量化并转成待审核候选。", relations: "每条正式关系都必须带证据与置信度。", users: "注册用户列表;禁用后其全部登录会话立即失效,操作写入审计。", models: "配置服务地址、接口协议与密钥,支持 chat completions / messages / responses 三种协议。", audits: "记录管理动作、对象和操作者，便于追责与排查。", overview: "观察系统成长与治理健康度。" } as Record<View, string>)[view]; }

function KnowledgeFormModal({ candidate, categories, error, mode, onClose, onReject, onSubmit, saving }: { candidate?: KnowledgeCandidate; categories: CategoryOption[]; error: string; mode: "promote" | "create"; onClose: () => void; onReject?: (reason: string) => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; saving: boolean }) {
  const [showReject, setShowReject] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  return <div className="modal-backdrop" role="presentation"><section aria-modal="true" className="knowledge-modal" role="dialog"><div className="modal-header"><div><h2>{mode === "promote" ? "审核候选知识" : "手工新增知识"}</h2><p>{mode === "promote" ? "核对候选内容与证据后修订为标准答案，或驳回不合适的候选。" : "填写已经核验、可直接用于回答用户的标准内容。"}</p></div><button aria-label="关闭" onClick={onClose} type="button">×</button></div>
    {mode === "promote" && candidate ? <div className="candidate-meta">
      <div className="candidate-meta-row">
        <span>出现 {candidate.occurrence_count} 次</span>
        <span>独立用户 {candidate.distinct_user_count} 人</span>
        <span>可信分 {Math.round(candidate.score * 100)}%</span>
        <span>来源 {({ faq: "用户互动", document: "文档解析" } as Record<string, string>)[candidate.candidate_type] ?? candidate.candidate_type}</span>
        <span className="category-pill">{categoryName(categories, candidate.category)}</span>
      </div>
      {candidate.evidence_summary ? <p className="candidate-evidence"><strong>证据摘要</strong>{candidate.evidence_summary}</p> : null}
    </div> : null}
    <form className="knowledge-form" onSubmit={onSubmit}>
    <label htmlFor="knowledge-title">知识标题</label><input defaultValue={candidate?.title ?? ""} id="knowledge-title" name="title" required />
    <label htmlFor="knowledge-content">已核验的标准答案</label><textarea defaultValue={candidate?.content ?? ""} id="knowledge-content" name="content" required rows={7} />
    {mode === "promote" ? <small className="field-hint">已预填候选内容,请在此基础上核验、修订后再发布。</small> : null}
    <div className="form-grid"><div><label htmlFor="knowledge-category">知识分类</label><select defaultValue={candidate?.category ?? "general"} id="knowledge-category" name="category">{categories.map((category) => <option key={category.slug} value={category.slug}>{category.name}</option>)}</select></div><div><label htmlFor="knowledge-type">知识类型</label><select defaultValue="faq" id="knowledge-type" name="knowledge_type"><option value="faq">FAQ</option><option value="process">流程</option><option value="policy">规则</option><option value="case">案例</option></select></div><div><label htmlFor="agent-scope">生效范围</label><input defaultValue="default" id="agent-scope" name="agent_scope" required /></div></div>
    {mode === "promote" ? <><label htmlFor="review-reason">审核依据</label><textarea defaultValue="已核对候选证据，内容准确且适合发布。" id="review-reason" name="review_reason" required rows={3} /></> : null}
    {mode === "promote" && showReject ? <div className="reject-panel">
      <label htmlFor="reject-reason">驳回理由</label>
      <textarea id="reject-reason" onChange={(event) => setRejectReason(event.target.value)} placeholder="说明证据不足、内容不准确或不适合发布的原因" rows={3} value={rejectReason} />
      <div className="modal-actions">
        <button className="cancel-button" onClick={() => setShowReject(false)} type="button">取消驳回</button>
        <button className="danger-button" disabled={saving || rejectReason.trim().length < 3} onClick={() => onReject?.(rejectReason.trim())} type="button">{saving ? "处理中…" : "确认驳回"}</button>
      </div>
    </div> : null}
    {error ? <p className="login-error">{error}</p> : null}<div className="modal-actions"><button className="cancel-button" onClick={onClose} type="button">取消</button>{mode === "promote" && !showReject ? <button className="danger-button" onClick={() => setShowReject(true)} type="button">驳回…</button> : null}<button className="promote-button" disabled={saving} type="submit">{saving ? "保存中…" : "确认发布"}</button></div>
  </form></section></div>;
}

function RelationModal({ items, onClose, onSubmit, saving, error }: { items: KnowledgeItem[]; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; saving: boolean; error: string }) {
  return <div className="modal-backdrop"><section className="knowledge-modal"><div className="modal-header"><div><h2>新增知识关系</h2><p>关系必须有清晰证据，避免自动猜测成为正式事实。</p></div><button onClick={onClose} type="button">×</button></div><form className="knowledge-form" onSubmit={onSubmit}><label>源知识</label><select name="source_id" required>{items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><label>目标知识</label><select name="target_id" required>{items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><label>关系类型</label><input defaultValue="关联" name="relation_type" required /><label>证据说明</label><textarea name="evidence_quote" required rows={4} />{error ? <p className="login-error">{error}</p> : null}<div className="modal-actions"><button className="cancel-button" onClick={onClose} type="button">取消</button><button className="promote-button" disabled={saving}>保存关系</button></div></form></section></div>;
}

const TABLE_PAGE_SIZE = 100;

function DataTable<TData extends RowData>({ table, density }: { table: TableInstance<TData>; density: Density }) {
  const [limit, setLimit] = useState(TABLE_PAGE_SIZE);
  const rows = table.getRowModel().rows;
  if (!rows.length) return <div className="empty-state"><div><strong>当前没有数据</strong>数据会随着真实使用与管理操作逐步增长。</div></div>;
  const visibleRows = rows.slice(0, limit);
  return <div className={`data-table-wrap density-${density}`}><table className="data-table"><thead>{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id}><button className="sort-header" onClick={header.column.getToggleSortingHandler()} type="button">{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}{header.column.getIsSorted() === "asc" ? " ↑" : header.column.getIsSorted() === "desc" ? " ↓" : ""}</button></th>)}</tr>)}</thead><tbody>{visibleRows.map((row) => <tr key={row.id}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table>
    {rows.length > limit ? <div className="table-foot"><span>已显示 {visibleRows.length} / {rows.length} 条</span><button className="load-more-button" onClick={() => setLimit(limit + TABLE_PAGE_SIZE)} type="button">加载更多</button></div> : null}
  </div>;
}
