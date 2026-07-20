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
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { KnowledgeGraph } from "@/components/knowledge-graph";
import { QualityChart } from "@/components/quality-chart";
import type {
  AdminDashboardPayload,
  AuditEvent,
  KnowledgeCandidate,
  KnowledgeDocument,
  KnowledgeItem,
  KnowledgeRelation,
} from "@/lib/types";

type View = "overview" | "candidates" | "knowledge" | "graph" | "documents" | "relations" | "audits";
type Density = "compact" | "comfortable";

const candidateHelper = createColumnHelper<KnowledgeCandidate>();
const knowledgeHelper = createColumnHelper<KnowledgeItem>();
const documentHelper = createColumnHelper<KnowledgeDocument>();
const relationHelper = createColumnHelper<KnowledgeRelation>();
const auditHelper = createColumnHelper<AuditEvent>();

export function AdminDashboard({ data, error }: { data: AdminDashboardPayload | null; error: string }) {
  const router = useRouter();
  const [view, setView] = useState<View>("overview");
  const [reviewing, setReviewing] = useState<KnowledgeCandidate | null>(null);
  const [creating, setCreating] = useState(false);
  const [showRelationForm, setShowRelationForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");
  const [filter, setFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [density, setDensity] = useState<Density>("comfortable");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null);

  const filteredKnowledge = useMemo(
    () => (data?.knowledge ?? []).filter((item) => typeFilter === "all" || item.knowledge_type === typeFilter),
    [data?.knowledge, typeFilter],
  );

  const candidateColumns = useMemo(() => [
    candidateHelper.accessor("title", { header: "候选知识", cell: (info) => <span className="cell-title">{info.getValue()}</span> }),
    candidateHelper.accessor("candidate_type", { header: "类型" }),
    candidateHelper.accessor("status", { header: "状态", cell: (info) => <Status value={info.getValue()} /> }),
    candidateHelper.accessor("occurrence_count", { header: "出现次数" }),
    candidateHelper.accessor("distinct_user_count", { header: "独立用户" }),
    candidateHelper.accessor("score", { header: "可信分", cell: (info) => `${Math.round(info.getValue() * 100)}%` }),
    candidateHelper.display({ id: "actions", header: "操作", cell: (info) => <button className="promote-button" onClick={() => setReviewing(info.row.original)} type="button">审核</button> }),
  ], []);
  const knowledgeColumns = useMemo(() => [
    knowledgeHelper.accessor("title", { header: "名称", cell: (info) => <button className="table-link" onClick={() => openDetail(info.row.original.id)} type="button">{info.getValue()}</button> }),
    knowledgeHelper.accessor("content", { header: "确认内容", cell: (info) => <span className="cell-content">{info.getValue()}</span> }),
    knowledgeHelper.accessor("knowledge_type", { header: "类型" }),
    knowledgeHelper.accessor("version", { header: "版本", cell: (info) => `v${info.getValue()}` }),
    knowledgeHelper.accessor("source_kind", { header: "来源" }),
    knowledgeHelper.accessor("status", { header: "状态", cell: (info) => <Status value={info.getValue()} /> }),
  ], []);
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

  const tables = {
    candidates: useGrid(data?.candidates ?? [], candidateColumns, filter, sorting, setSorting),
    knowledge: useGrid(filteredKnowledge, knowledgeColumns, filter, sorting, setSorting),
    documents: useGrid(data?.documents ?? [], documentColumns, filter, sorting, setSorting),
    relations: useGrid(data?.relations ?? [], relationColumns, filter, sorting, setSorting),
    audits: useGrid(data?.audits ?? [], auditColumns, filter, sorting, setSorting),
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
    router.refresh();
  }

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    const form = new FormData(event.currentTarget);
    const response = await fetch("/api/admin/backend/documents", { method: "POST", body: form });
    setSaving(false);
    if (!response.ok) setActionError("导入失败，请使用 txt、md、html、pdf 或 docx 文件。");
    else router.refresh();
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
    if (response.ok) { setShowRelationForm(false); router.refresh(); }
    else setActionError("关系创建失败，请确认两个知识条目不同且证据完整。");
  }

  async function saveCurrentView() {
    const name = window.prompt("给当前视图命名");
    if (!name) return;
    await fetch("/api/admin/backend/views", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, view_type: view === "graph" ? "graph" : view === "overview" ? "dashboard" : "grid", configuration: { view, filter, typeFilter, density, sorting }, is_shared: false }) });
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
        <Nav icon={LayoutDashboard} label="运营总览" active={view === "overview"} onClick={() => setView("overview")} />
        <Nav icon={MessageSquareText} label="候选审核" active={view === "candidates"} onClick={() => setView("candidates")} />
        <Nav icon={BookOpenText} label="知识资产" active={view === "knowledge"} onClick={() => setView("knowledge")} />
        <Nav icon={GitFork} label="关系图谱" active={view === "graph"} onClick={() => setView("graph")} />
        <Nav icon={FileText} label="文档导入" active={view === "documents"} onClick={() => setView("documents")} />
        <Nav icon={Network} label="关系管理" active={view === "relations"} onClick={() => setView("relations")} />
        <Nav icon={History} label="审计日志" active={view === "audits"} onClick={() => setView("audits")} />
      </nav>
      <div className="admin-sidebar-foot">内部管理系统<br />普通用户无入口、无接口权限</div>
    </aside>
    <section className="admin-main">
      <header className="admin-header"><div><h1>知识成长工作台</h1><p>空库起步，用户信号经脱敏、聚合和审核后才会成为正式知识。</p></div><button className="logout-button" onClick={logout} type="button"><LogOut size={15} /> 退出</button></header>
      {error ? <div className="error-banner">{error}</div> : null}
      <section className="stats-grid stats-six">{statCards.map(([label, value]) => <article className="stat-card" key={label}><span className="stat-label">{label}</span><strong className="stat-value">{value}</strong></article>)}</section>

      {view === "overview" ? <section className="overview-grid">
        <article className="admin-panel chart-panel"><div className="panel-toolbar"><div><h2>近 14 天知识质量趋势</h2><p>互动、候选和正式发布的变化。</p></div><BarChart3 color="#147a52" /></div><QualityChart data={data?.trends ?? []} /></article>
        <article className="admin-panel governance-panel"><div className="panel-toolbar"><div><h2>治理闭环</h2><p>所有增长都经过同一条受控路径。</p></div><ShieldCheck color="#147a52" /></div><div className="governance-steps"><span>1 用户同意</span><span>2 自动脱敏</span><span>3 多用户聚合</span><span>4 管理员审核</span><span>5 发布与版本化</span><span>6 审计与回滚依据</span></div><div className="boundary-note"><strong>用户侧边界</strong><p>普通用户只感受到回答更贴合，不可浏览、搜索或导出知识库；私有记忆只能由本人查看和删除。</p></div></article>
      </section> : null}

      {view !== "overview" ? <section className="admin-panel">
        <div className="panel-toolbar admin-grid-toolbar"><div><h2>{viewTitle(view)}</h2><p>{viewDescription(view)}</p></div><div className="toolbar-actions">
          {!["graph"].includes(view) ? <label className="search-box"><Search size={15} /><input aria-label="筛选表格" onChange={(event) => setFilter(event.target.value)} placeholder="筛选当前视图" value={filter} /></label> : null}
          {view === "knowledge" ? <select aria-label="知识类型筛选" onChange={(event) => setTypeFilter(event.target.value)} value={typeFilter}><option value="all">全部类型</option><option value="faq">FAQ</option><option value="process">流程</option><option value="policy">规则</option><option value="case">案例</option></select> : null}
          {!["graph"].includes(view) ? <button className="icon-action" onClick={() => setDensity(density === "compact" ? "comfortable" : "compact")} title="切换密度" type="button"><SlidersHorizontal size={16} /></button> : null}
          <button className="secondary-action" onClick={saveCurrentView} type="button">保存视图</button>
          {view === "knowledge" ? <button className="promote-button" onClick={() => setCreating(true)} type="button">+ 新增知识</button> : null}
          {view === "relations" ? <button className="promote-button" onClick={() => setShowRelationForm(true)} type="button">+ 新增关系</button> : null}
        </div></div>
        {view === "candidates" ? <DataTable density={density} table={tables.candidates} /> : null}
        {view === "knowledge" ? <DataTable density={density} table={tables.knowledge} /> : null}
        {view === "graph" && data ? <KnowledgeGraph graph={data.graph} /> : null}
        {view === "documents" ? <><form className="upload-row" onSubmit={uploadDocument}><input accept=".txt,.md,.html,.htm,.pdf,.docx" name="file" required type="file" /><button className="promote-button" disabled={saving} type="submit">{saving ? "导入中…" : "上传并解析"}</button><span>解析结果先进入候选池，不会自动发布。</span></form><DataTable density={density} table={tables.documents} /></> : null}
        {view === "relations" ? <DataTable density={density} table={tables.relations} /> : null}
        {view === "audits" ? <DataTable density={density} table={tables.audits} /> : null}
      </section> : null}
      {data?.views.length ? <div className="saved-views"><strong>已保存视图</strong>{data.views.map((item) => <button key={item.id} onClick={() => { const config = item.configuration as { view?: View; filter?: string; typeFilter?: string; density?: Density }; if (config.view) setView(config.view); setFilter(config.filter ?? ""); setTypeFilter(config.typeFilter ?? "all"); setDensity(config.density ?? "comfortable"); }} type="button">{item.name}</button>)}</div> : null}
    </section>

    {reviewing ? <KnowledgeFormModal candidate={reviewing} error={actionError} mode="promote" onClose={() => setReviewing(null)} onSubmit={(event) => submitKnowledge(event, "promote")} saving={saving} /> : null}
    {creating ? <KnowledgeFormModal error={actionError} mode="create" onClose={() => setCreating(false)} onSubmit={(event) => submitKnowledge(event, "create")} saving={saving} /> : null}
    {showRelationForm && data ? <RelationModal items={data.knowledge} onClose={() => setShowRelationForm(false)} onSubmit={submitRelation} saving={saving} error={actionError} /> : null}
    {detail ? <div className="detail-backdrop" onClick={() => setDetail(null)} role="presentation"><aside className="detail-drawer" onClick={(event) => event.stopPropagation()}><button aria-label="关闭详情" onClick={() => setDetail(null)} type="button">×</button><h2>知识详情与治理记录</h2><pre>{JSON.stringify(detail, null, 2)}</pre></aside></div> : null}
  </main>;
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
function Status({ value }: { value: string }) { return <span className={`status-pill status-${value}`}>{({ pending_review: "待审核", observed: "观察中", published: "已发布", completed: "已完成", processing: "处理中", queued: "排队中", failed: "失败", draft: "草稿" } as Record<string, string>)[value] ?? value}</span>; }
function formatTime(value: string) { return new Intl.DateTimeFormat("zh-CN", { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); }
function titleFor(data: AdminDashboardPayload | null, id: string) { return data?.knowledge.find((item) => item.id === id)?.title ?? id.slice(0, 8); }
function viewTitle(view: View) { return ({ candidates: "互动候选池", knowledge: "知识资产表", graph: "知识关系图谱", documents: "文档导入与解析", relations: "显式关系管理", audits: "不可变审计记录", overview: "运营总览" } as Record<View, string>)[view]; }
function viewDescription(view: View) { return ({ candidates: "达到次数与独立用户阈值后进入人工审核。", knowledge: "支持筛选、排序、密度、保存视图及查看版本证据。", graph: "实线为显式关系，虚线仅作为辅助探索。", documents: "文档被切块、向量化并转成待审核候选。", relations: "每条正式关系都必须带证据与置信度。", audits: "记录管理动作、对象和操作者，便于追责与排查。", overview: "观察系统成长与治理健康度。" } as Record<View, string>)[view]; }

function KnowledgeFormModal({ candidate, error, mode, onClose, onSubmit, saving }: { candidate?: KnowledgeCandidate; error: string; mode: "promote" | "create"; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; saving: boolean }) {
  return <div className="modal-backdrop" role="presentation"><section aria-modal="true" className="knowledge-modal" role="dialog"><div className="modal-header"><div><h2>{mode === "promote" ? "审核候选知识" : "手工新增知识"}</h2><p>填写已经核验、可直接用于回答用户的标准内容。</p></div><button aria-label="关闭" onClick={onClose} type="button">×</button></div><form className="knowledge-form" onSubmit={onSubmit}>
    <label htmlFor="knowledge-title">知识标题</label><input defaultValue={candidate?.title ?? ""} id="knowledge-title" name="title" required />
    <label htmlFor="knowledge-content">已核验的标准答案</label><textarea id="knowledge-content" name="content" required rows={7} />
    <div className="form-grid"><div><label htmlFor="knowledge-type">知识类型</label><select defaultValue="faq" id="knowledge-type" name="knowledge_type"><option value="faq">FAQ</option><option value="process">流程</option><option value="policy">规则</option><option value="case">案例</option></select></div><div><label htmlFor="agent-scope">生效范围</label><input defaultValue="default" id="agent-scope" name="agent_scope" required /></div></div>
    {mode === "promote" ? <><label htmlFor="review-reason">审核依据</label><textarea defaultValue="已核对候选证据，内容准确且适合发布。" id="review-reason" name="review_reason" required rows={3} /></> : null}
    {error ? <p className="login-error">{error}</p> : null}<div className="modal-actions"><button className="cancel-button" onClick={onClose} type="button">取消</button><button className="promote-button" disabled={saving} type="submit">{saving ? "保存中…" : "确认发布"}</button></div>
  </form></section></div>;
}

function RelationModal({ items, onClose, onSubmit, saving, error }: { items: KnowledgeItem[]; onClose: () => void; onSubmit: (event: FormEvent<HTMLFormElement>) => void; saving: boolean; error: string }) {
  return <div className="modal-backdrop"><section className="knowledge-modal"><div className="modal-header"><div><h2>新增知识关系</h2><p>关系必须有清晰证据，避免自动猜测成为正式事实。</p></div><button onClick={onClose} type="button">×</button></div><form className="knowledge-form" onSubmit={onSubmit}><label>源知识</label><select name="source_id" required>{items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><label>目标知识</label><select name="target_id" required>{items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select><label>关系类型</label><input defaultValue="关联" name="relation_type" required /><label>证据说明</label><textarea name="evidence_quote" required rows={4} />{error ? <p className="login-error">{error}</p> : null}<div className="modal-actions"><button className="cancel-button" onClick={onClose} type="button">取消</button><button className="promote-button" disabled={saving}>保存关系</button></div></form></section></div>;
}

function DataTable<TData extends RowData>({ table, density }: { table: TableInstance<TData>; density: Density }) {
  if (!table.getRowModel().rows.length) return <div className="empty-state"><div><strong>当前没有数据</strong>数据会随着真实使用与管理操作逐步增长。</div></div>;
  return <div className={`data-table-wrap density-${density}`}><table className="data-table"><thead>{table.getHeaderGroups().map((group) => <tr key={group.id}>{group.headers.map((header) => <th key={header.id}><button className="sort-header" onClick={header.column.getToggleSortingHandler()} type="button">{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}{header.column.getIsSorted() === "asc" ? " ↑" : header.column.getIsSorted() === "desc" ? " ↓" : ""}</button></th>)}</tr>)}</thead><tbody>{table.getRowModel().rows.map((row) => <tr key={row.id}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>)}</tbody></table></div>;
}
