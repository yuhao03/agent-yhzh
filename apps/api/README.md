# agent-yhzh API

FastAPI + LangGraph + AG-UI 后端。依赖由 uv 管理，虚拟环境位于 `apps/api/.venv`。

```bash
uv sync
uv run python main.py
```

本地无 Docker 调试可复制 `.env.sqlite.example`；正式环境使用根目录 `.env.example` 中的 PostgreSQL + pgvector 配置。

核心接口：

- `/ag-ui`：CopilotKit/AG-UI Agent 流式端点。
- `/api/v1/user/*`：普通用户互动信号与本人私有记忆，不返回知识库内容。
- `/api/v1/admin/*`：仅管理员服务身份可访问的候选、知识、文档、关系、统计、审计和图谱接口。
- `/api/v1/admin/model-configs`：模型连接 CRUD、加密密钥掩码与连接测试；管理员后台配置优先于环境变量并即时生效。
- `/metrics`：仅运维密钥可访问的 Prometheus 指标。
- `/api/v1/admin/docs`：受保护的 OpenAPI 文档；默认不存在公开 `/docs` 和 `/openapi.json`。

验证：

```bash
uv run ruff check .
uv run mypy agent_yhzh --ignore-missing-imports
uv run pytest
uv run python scripts/evaluate_retrieval.py
```
