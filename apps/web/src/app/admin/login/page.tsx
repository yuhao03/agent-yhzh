import Link from "next/link";

import { AdminLoginForm } from "@/components/admin-login-form";

export default function AdminLoginPage() {
  return (
    <main className="login-shell">
      <section className="login-brand-panel">
        <Link className="brand" href="/">
          <span className="brand-mark">砺</span>
          <span>砺知智能</span>
        </Link>
        <div>
          <h1>让知识成长，始终处于人的控制之下。</h1>
          <p>
            管理员工作台用于审核互动中发现的候选经验、维护已发布知识和查看关系图谱。这里不会对普通用户开放。
          </p>
        </div>
        <small>ADMIN CONTROL PLANE · INTERNAL ONLY</small>
      </section>
      <section className="login-form-panel">
        <div className="login-card">
          <h2>管理员登录</h2>
          <p>请输入管理员访问密钥进入内部知识工作台。</p>
          <AdminLoginForm />
          <Link className="back-link" href="/">← 返回用户端</Link>
        </div>
      </section>
    </main>
  );
}
