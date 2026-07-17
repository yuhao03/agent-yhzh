# agent-yhzh API

FastAPI + LangGraph + AG-UI 后端。依赖由 uv 管理，虚拟环境位于 `apps/api/.venv`。

```bash
uv sync
uv run python main.py
```

本地无 Docker 调试可复制 `.env.sqlite.example`；正式环境使用根目录 `.env.example` 中的 PostgreSQL + pgvector 配置。

核心接口：

- `/ag-ui`：CopilotKit/AG-UI Agent 流式端点。
- `/api/v1/user/*`：普通用户互动信号，不返回知识库内容。
- `/api/v1/admin/*`：仅管理员可访问的候选、知识、统计和图谱接口。
