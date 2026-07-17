"use client";

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  type RowData,
  type Table as TableInstance,
  useReactTable,
} from "@tanstack/react-table";
import {
  BookOpenText,
  BrainCircuit,
  GitFork,
  LayoutDashboard,
  LogOut,
  MessageSquareText,
  ShieldCheck,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { FormEvent, useMemo, useState } from "react";

import { KnowledgeGraph } from "@/components/knowledge-graph";
import type {
  AdminDashboardPayload,
  KnowledgeCandidate,
  KnowledgeItem,
} from "@/lib/types";

type View = "candidates" | "knowledge" | "graph";

const candidateHelper = createColumnHelper<KnowledgeCandidate>();
const knowledgeHelper = createColumnHelper<KnowledgeItem>();

export function AdminDashboard({
  data,
  error,
}: {
  data: AdminDashboardPayload | null;
  error: string;
}) {
  const router = useRouter();
  const [view, setView] = useState<View>("candidates");
  const [reviewing, setReviewing] = useState<KnowledgeCandidate | null>(null);
  const [creating, setCreating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState("");

  const candidateColumns = useMemo(
    () => [
      candidateHelper.accessor("title", {
        header: "候选知识",
        cell: (info) => <span className="cell-title">{info.getValue()}</span>,
      }),
      candidateHelper.accessor("content", {
        header: "互动内容",
        cell: (info) => <span className="cell-content">{info.getValue()}</span>,
      }),
      candidateHelper.accessor("status", {
        header: "状态",
        cell: (info) => (
          <span className={`status-pill status-${info.getValue()}`}>
            {info.getValue() === "pending_review" ? "待审核" : "观察中"}
          </span>
        ),
      }),
      candidateHelper.accessor("occurrence_count", { header: "出现次数" }),
      candidateHelper.accessor("distinct_user_count", { header: "用户数" }),
      candidateHelper.accessor("score", {
        header: "可信分",
        cell: (info) => `${Math.round(info.getValue() * 100)}%`,
      }),
      candidateHelper.display({
        id: "actions",
        header: "操作",
        cell: (info) => (
          <button
            className="promote-button"
            onClick={() => setReviewing(info.row.original)}
            type="button"
          >
            审核并发布
          </button>
        ),
      }),
    ],
    [],
  );

  const knowledgeColumns = useMemo(
    () => [
      knowledgeHelper.accessor("title", {
        header: "名称",
        cell: (info) => <span className="cell-title">{info.getValue()}</span>,
      }),
      knowledgeHelper.accessor("content", {
        header: "确认内容",
        cell: (info) => <span className="cell-content">{info.getValue()}</span>,
      }),
      knowledgeHelper.accessor("knowledge_type", { header: "类型" }),
      knowledgeHelper.accessor("agent_scope", {
        header: "生效范围",
        cell: (info) => info.getValue().join("、"),
      }),
      knowledgeHelper.accessor("source_kind", {
        header: "来源",
        cell: (info) => info.getValue() === "interaction" ? "用户互动" : "管理员录入",
      }),
      knowledgeHelper.accessor("status", {
        header: "状态",
        cell: () => <span className="status-pill status-published">已发布</span>,
      }),
    ],
    [],
  );

  // TanStack Table intentionally returns mutable helpers; React Compiler skips it.
  // eslint-disable-next-line react-hooks/incompatible-library
  const candidateTable = useReactTable({
    data: data?.candidates ?? [],
    columns: candidateColumns,
    getCoreRowModel: getCoreRowModel(),
  });
  const knowledgeTable = useReactTable({
    data: data?.knowledge ?? [],
    columns: knowledgeColumns,
    getCoreRowModel: getCoreRowModel(),
  });

  async function logout() {
    await fetch("/api/admin/session", { method: "DELETE" });
    router.replace("/admin/login");
    router.refresh();
  }

  async function submitKnowledge(
    event: FormEvent<HTMLFormElement>,
    mode: "promote" | "create",
  ) {
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
    };
    const endpoint = mode === "promote" && reviewing
      ? `/api/admin/candidates/${reviewing.id}/promote`
      : "/api/admin/knowledge";
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    setSaving(false);
    if (!response.ok) {
      setActionError("保存失败，请检查后端状态后重试。");
      return;
    }
    setReviewing(null);
    setCreating(false);
    setView("knowledge");
    router.refresh();
  }

  const stats = data?.stats;
  const statCards = [
    ["已发布知识", stats?.published_knowledge ?? 0],
    ["全部候选", stats?.candidates ?? 0],
    ["等待审核", stats?.pending_review ?? 0],
    ["互动信号", stats?.interaction_events ?? 0],
    ["隔离记忆", stats?.private_memories ?? 0],
  ];

  return (
    <main className="admin-shell">
      <aside className="admin-sidebar">
        <div className="brand">
          <span className="brand-mark">砺</span><span>知识控制台</span>
        </div>
        <nav className="admin-nav">
          <button aria-label="总览" className="admin-nav-item" onClick={() => setView("candidates")} title="总览" type="button"><LayoutDashboard size={18} /><span>总览</span></button>
          <button aria-label="候选审核" className={`admin-nav-item ${view === "candidates" ? "active" : ""}`} onClick={() => setView("candidates")} title="候选审核" type="button"><MessageSquareText size={18} /><span>候选审核</span></button>
          <button aria-label="知识资产" className={`admin-nav-item ${view === "knowledge" ? "active" : ""}`} onClick={() => setView("knowledge")} title="知识资产" type="button"><BookOpenText size={18} /><span>知识资产</span></button>
          <button aria-label="关系图谱" className={`admin-nav-item ${view === "graph" ? "active" : ""}`} onClick={() => setView("graph")} title="关系图谱" type="button"><GitFork size={18} /><span>关系图谱</span></button>
        </nav>
        <div className="admin-sidebar-foot">内部系统<br />普通用户不可访问</div>
      </aside>

      <section className="admin-main">
        <header className="admin-header">
          <div>
            <h1>知识成长工作台</h1>
            <p>从空库开始，互动信号只有经过审核才会成为正式知识。</p>
          </div>
          <button className="logout-button" onClick={logout} type="button"><LogOut size={15} /> 退出</button>
        </header>

        {error ? <div className="error-banner">{error}</div> : null}

        <section className="stats-grid">
          {statCards.map(([label, value]) => (
            <article className="stat-card" key={label}>
              <span className="stat-label">{label}</span>
              <strong className="stat-value">{value}</strong>
            </article>
          ))}
        </section>

        <section className="admin-panel">
          <div className="panel-toolbar">
            <div>
              <h2>{view === "candidates" ? "互动候选池" : view === "knowledge" ? "已发布知识" : "知识关系图谱"}</h2>
              <p>{view === "candidates" ? "聚合真实使用中的问题与纠正，达到阈值后进入人工审核。" : view === "knowledge" ? "只有这里发布的内容才能被用户侧智能体使用。" : "实线为显式关系，虚线为同类型知识的辅助关系。"}</p>
            </div>
            {view === "knowledge" ? (
              <button className="secondary-action" onClick={() => setCreating(true)} type="button">+ 手工新增</button>
            ) : view === "candidates" ? <ShieldCheck color="#147a52" size={23} /> : <BrainCircuit color="#147a52" size={23} />}
          </div>

          {view === "candidates" ? (
            candidateTable.getRowModel().rows.length ? (
              <DataTable table={candidateTable} />
            ) : (
              <Empty title="候选池目前为空" text="用户开始使用后，问题与反馈会逐步在这里形成候选知识。" />
            )
          ) : null}
          {view === "knowledge" ? (
            knowledgeTable.getRowModel().rows.length ? (
              <DataTable table={knowledgeTable} />
            ) : (
              <Empty title="知识库从零开始" text="先让用户真实使用，再从候选池审核发布第一条可靠知识。" />
            )
          ) : null}
          {view === "graph" && data ? <KnowledgeGraph graph={data.graph} /> : null}
        </section>
      </section>

      {reviewing ? (
        <KnowledgeFormModal
          candidate={reviewing}
          error={actionError}
          mode="promote"
          onClose={() => setReviewing(null)}
          onSubmit={(event) => submitKnowledge(event, "promote")}
          saving={saving}
        />
      ) : null}
      {creating ? (
        <KnowledgeFormModal
          error={actionError}
          mode="create"
          onClose={() => setCreating(false)}
          onSubmit={(event) => submitKnowledge(event, "create")}
          saving={saving}
        />
      ) : null}
    </main>
  );
}

function KnowledgeFormModal({
  candidate,
  error,
  mode,
  onClose,
  onSubmit,
  saving,
}: {
  candidate?: KnowledgeCandidate;
  error: string;
  mode: "promote" | "create";
  onClose: () => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  saving: boolean;
}) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section aria-modal="true" className="knowledge-modal" role="dialog">
        <div className="modal-header">
          <div>
            <h2>{mode === "promote" ? "审核候选知识" : "手工新增知识"}</h2>
            <p>{mode === "promote" ? "问题只是线索，请填写核验后的标准答案再发布。" : "手工录入的内容将直接作为已确认知识发布。"}</p>
          </div>
          <button aria-label="关闭审核表单" onClick={onClose} type="button">×</button>
        </div>
        <form className="knowledge-form" onSubmit={onSubmit}>
          <label htmlFor="knowledge-title">知识标题</label>
          <input defaultValue={candidate?.title ?? ""} id="knowledge-title" name="title" required />
          <label htmlFor="knowledge-content">已核验的标准答案</label>
          <textarea
            autoFocus
            id="knowledge-content"
            name="content"
            placeholder="填写可直接用于回答用户的、已经核验的内容…"
            required
            rows={7}
          />
          <div className="form-grid">
            <div>
              <label htmlFor="knowledge-type">知识类型</label>
              <select defaultValue="faq" id="knowledge-type" name="knowledge_type">
                <option value="faq">FAQ</option>
                <option value="process">流程</option>
                <option value="policy">规则</option>
                <option value="case">案例</option>
              </select>
            </div>
            <div>
              <label htmlFor="agent-scope">生效范围</label>
              <input defaultValue="default" id="agent-scope" name="agent_scope" required />
            </div>
          </div>
          {error ? <p className="login-error">{error}</p> : null}
          <div className="modal-actions">
            <button className="cancel-button" onClick={onClose} type="button">取消</button>
            <button className="promote-button" disabled={saving} type="submit">{saving ? "保存中…" : "确认发布"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function Empty({ title, text }: { title: string; text: string }) {
  return <div className="empty-state"><div><strong>{title}</strong>{text}</div></div>;
}

function DataTable<TData extends RowData>({ table }: { table: TableInstance<TData> }) {
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          {table.getHeaderGroups().map((group) => (
            <tr key={group.id}>{group.headers.map((header) => <th key={header.id}>{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</th>)}</tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>{row.getVisibleCells().map((cell) => <td key={cell.id}>{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}</tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
