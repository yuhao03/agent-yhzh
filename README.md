# agent-yhzh

一个从空知识库开始、在真实用户使用中逐步成长的智能体应用基线。

## 已串联的技术栈

- 普通用户前端：Next.js 16 + React 19 + CopilotKit v2。
- 管理员知识后台：Next.js Server Components、服务端会话、TanStack Table、Cytoscape。
- Agent 后端：uv 隔离环境、FastAPI、LangGraph、AG-UI、LiteLLM。
- 正式知识底座：PostgreSQL + pgvector，逻辑分离正式知识、候选、互动事件、关系和用户私有记忆。
- 异步任务基线：Redis + Celery。
- 无 Docker 本地预览：SQLite；正式部署仍使用 PostgreSQL + pgvector。

## 产品边界

普通用户只能使用智能助手，不存在知识库入口，也不能获取候选记录、知识原文、关系图谱或内部检索过程。管理员登录后才可以：

- 查看互动中逐步聚合的候选知识；
- 将问题线索编辑成“已核验标准答案”后发布；
- 手工录入正式知识；
- 查看知识 Grid View 与局部关系图谱；
- 观察空库如何随真实使用逐步成长。

用户只会感受到回答从“不知道”逐步变为“能够基于已确认信息作答”。

## 最快本地启动（不依赖 Docker）

```bash
make setup-local
make api-prod
make web-prod
```

打开：

- 普通用户端：<http://127.0.0.1:3000>
- 管理员登录：<http://127.0.0.1:3000/admin/login>
- FastAPI 文档：<http://127.0.0.1:8123/docs>

本地管理员访问密钥默认为 `change-me-admin-key`。正式环境必须更换，并建议接入 OIDC/OAuth2。

## PostgreSQL + pgvector 启动

```bash
make setup
make infra-up
make api-prod
make web-prod
```

若 Docker 提示 daemon 权限不足，将当前用户加入 docker 组后重新登录：

```bash
sudo usermod -aG docker "$USER"
```

这一步需要由机器管理员执行。本仓库不会自动修改系统权限。

## 配置模型

不配置模型密钥时，系统使用离线可验证回答，便于完整调试权限和知识成长闭环。需要模型生成时，在 `apps/api/.env` 中配置：

```dotenv
MODEL_NAME=openai/gpt-5.4-mini
OPENAI_API_KEY=你的密钥
```

## 知识成长闭环

```text
空知识库
  ↓
用户问题 / 纠正 / 反馈
  ↓
脱敏事件 + 去重聚合候选
  ↓ 达到出现次数阈值
管理员审核并填写标准答案
  ↓
正式知识 + 关系图谱
  ↓
后续回答获得增强
```

已发布候选不会因为用户再次提问而重新回到待审核状态。用户身份仅保存为加盐哈希，私有记忆与公共知识使用不同的数据域。

## 常用命令

```bash
make test       # 后端测试 + 前端 lint
make lint       # Ruff + ESLint
make worker     # Celery worker
make infra-down # 停止本项目基础设施
```

## 当前实现范围

- [x] 单仓库、uv 隔离环境和 Docker 基础设施
- [x] SQLite 本地调试降级，不污染系统 Python
- [x] 空库冷启动数据模型
- [x] 管理员/普通用户 API 权限边界
- [x] LangGraph AG-UI Agent 与 CopilotKit 串联
- [x] 候选聚合、人工审核、标准答案发布、再次检索回答
- [x] 管理员 Grid View、手工录入和局部知识图谱
- [ ] 文档上传、解析、chunk、embedding 和混合检索
- [ ] Celery 学习任务、冲突检测与高风险审批流
- [ ] Langfuse / OpenTelemetry / Prometheus 完整接入
- [ ] 多 Agent 评测后再决定是否拆分
