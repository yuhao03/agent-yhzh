# 实施路线

## 本轮深度升级(2026-07):越用越聪明的电商多专家智能体

目标:在保持"治理型知识库"底座不变的前提下,把单节点助手升级为**分类知识驱动的多专家(子 Agent)编排系统**,并补齐多协议模型接入与真实多用户体系。

### 1. 多协议 LLM 网关

- `services/llm_gateway.py` 基于 httpx 直连第三方服务,支持三种协议:
  - `chat_completions_v1`(OpenAI `POST {base}/chat/completions`)
  - `messages_v1`(Anthropic `POST {base}/messages`,`x-api-key` + `anthropic-version`)
  - `responses_v1`(OpenAI Responses `POST {base}/responses`,`instructions` + `input`)
- `ModelProviderConfig` 新增 `api_protocol` 字段(迁移 0003);服务商与协议解耦,任意 base_url 可选任意协议。
- 连接测试、子 Agent 回答统一走网关;SSRF 防护、密钥加密、审计不变。Embedding 仍走 litellm(OpenAI 兼容)或本地哈希降级。

### 2. 知识分类体系(自动归类)

- `services/taxonomy.py` 内置电商为主的六大分类:`ecommerce_product_copy` 商品文案、`ecommerce_listing` 平台运营与 Listing、`ecommerce_marketing` 营销策划、`ecommerce_service` 客服与售后、`ecommerce_analysis` 选品与市场分析、`general` 通用。
- `KnowledgeItem` / `KnowledgeCandidate` 新增 `category` 列;交互事件与文档切块在进入候选池时自动分类(关键词打分,配置模型后可用 LLM 精分,失败降级关键词)。
- 管理员审核候选时可修正分类;检索支持分类过滤+加权,子 Agent 优先命中本域知识,空结果时回退全域。

### 3. Supervisor + 子 Agent 编排(LangGraph)

- `agent.py` 重构为 supervisor 图:`supervisor` 节点捕获交互并做意图路由(LLM 分类,无模型时关键词降级),按 `route` 分发到六个专家节点。
- 专家注册表在 `services/subagents.py`:商品文案专家、平台运营专家、营销策划专家、客服售后专家、选品分析专家、通用助手;每个专家绑定自己的知识分类、人格化 system prompt 与温度。
- 专家节点:按分类检索知识 + 用户私有记忆 + 运行时模型配置 → 走多协议网关生成回答;配置模型后即使知识库为空也能回答(明确标注"暂无已确认知识"),无模型时保持原有确定性降级文案。
- 图状态携带 `route`/`category`,通过 AG-UI 状态同步给前端展示"当前专家"。

### 4. 真实多用户体系

- 新增 `identity` 数据域:`user_accounts`(scrypt 密码哈希、状态、租户内邮箱唯一)与 `auth_sessions`(token 只存 SHA-256 哈希、有效期、可撤销)。
- `/api/v1/auth/*`:注册、登录、登出、当前用户;仍由 Next 服务端以 `AGENT_SERVICE_TOKEN` 服务间调用。登录用户请求携带 `X-Auth-Token`,后端逐请求校验会话并以账号 ID 作为身份;匿名访客模式保留(体验后引导注册)。
- 账号 ID 继续走既有 `user_ref_hash` 加盐哈希进入学习管道与私有记忆,原有隔离/同意/脱敏不变量全部保留。
- 管理台新增用户管理:列表、启用/禁用,全部写审计。

### 5. 前端重设计(Next.js 16 + CopilotKit v2 + Tailwind 4,框架不变)

- 用户端:`/` 营销首页(登录/注册入口)+ 新增 `/chat` 全屏工作台(专家场景入口、对话主区、当前专家指示、记忆与隐私面板)。
- 新增 `/login`、`/register` 页面与 `/api/user/auth/*` 路由;`user-session.ts` 会话升级为"访客 | 登录"双态,登录态附带 `X-Auth-Token`。
- 管理台:新增"用户管理"视图;知识/候选全面接入分类(筛选、审核表单、图谱按分类着色);模型配置增加协议选择;详情抽屉结构化渲染;概览增加分类分布。

### 6. 质量门槛

- 新增 pytest:网关三协议(httpx MockTransport)、意图路由与自动分类、注册/登录/会话校验、分类检索回退。
- 全量 `make test`(ruff + mypy + pytest + next lint + next build)通过后才推送。
- 既有不变量必须保持:管理端未授权 404、同意与脱敏服务端强制、多用户阈值、私有记忆隔离、SQLite 无 Docker 降级、密钥加密与掩码。

### 7. 深度审查与加固(2026-07-27,已完成)

上述 1-6 已全部落地。多智能体交叉审查后修复的缺陷与补齐项:

- **图谱分类着色**:`KnowledgeGraphNode` 补 `category` 字段(此前被 response_model 剥离,着色全灰);Cytoscape 边选择器改 `edge[?inferred]`(此前显式边也被画成虚线);图谱增加分类图例,节点点击直达详情抽屉。
- **会话安全**:用户侧与管理台 Cookie 签名密钥默认值改为 `change-me-*` 前缀,生产守卫真正生效;前端持久化后端 `expires_at`,会员 Cookie 与后端 30 天会话对齐,过期自动降级访客并提示重新登录;记忆面板 401 兜底。
- **认证加固**:登录对不存在账号执行 dummy scrypt 校验(消除计时枚举);login/register 按 IP 限流(可配,默认 30/15 次每分钟);`hmac.compare_digest` 两侧强制 UTF-8 编码(畸形头不再 500)。
- **SSRF 补漏**:`validate_model_base_url` 用 `socket.inet_aton` 识别 `2130706433`/`127.1`/`0x7f000001` 类非点分字面量并走私网检查;DNS 重绑定仍列上线前补齐。
- **协议兼容**:messages_v1 温度在网关侧 clamp ≤1,创建配置时温度>1 直接 422。
- **分类闭环**:category 全线校验必须为六分类之一(422 拒未知);实现 LLM 精分类(候选创建与文档切块两条入库路径,未配置模型/失败降级关键词,与 docstring 承诺一致);supervisor 的 category 状态与路由到的专家对齐(不再各算各的)。
- **审核流补全**:审核弹窗回填候选内容并展示出现次数/独立用户数/证据摘要;新增驳回入口(必填理由);候选池支持分类筛选;视图间筛选/排序状态隔离;已保存视图恢复排序;状态 pill 中文补全;操作成功 toast;弹窗 Escape 关闭。
- **移动端可达性**:/chat 改 100dvh;≤1180px 记忆面板转抽屉;≤860px 专家栏转横向 chip;专家卡改 button 语义可点击发送示例问题;管理台大列表前端分页(每页 100)。
- 后端测试 23 → 38 个,全部通过;前端 lint + build 通过;真实浏览器验证注册/登录/过期降级/管理台/图谱分类/对话路由(客服售后专家)全链路。

## 已落地的可运行闭环

1. 普通用户端和管理员后台使用同一个 Next.js 工程，但权限、路由和数据获取完全分离。
2. FastAPI/LangGraph 后端通过 AG-UI 接入 CopilotKit；用户端不直接请求管理员 API。
3. PostgreSQL + pgvector 作为正式知识底座，SQLite 只作为无 Docker 的本地预览降级。
4. 系统允许空库启动；用户明确同意后，问题、纠正和反馈先成为脱敏互动事件，再由 Celery/本地异步降级按规范化文本聚合为候选。
5. 候选必须同时达到出现次数和独立用户数阈值才进入待审核，管理员必须填写核验后的标准答案与审核依据，不能把用户问题直接当知识发布。
6. 发布后，普通用户再次提问会命中正式知识，但不会看到条目、ID、来源、图谱或检索过程。
7. 管理员可查看 Grid View、手工新增知识、保存视图、查看 ECharts 趋势、导入文档，并在 Cytoscape 图谱中查看显式关系和同类型辅助关系。
8. 每次正式知识变化都会留下版本、审核、审计和 Outbox 记录；普通用户私有记忆位于独立数据域，可由本人删除、清空或等待过期。

## 已落地的大规模知识基础

1. 文档支持本地或 S3/MinIO 对象存储，解析 txt、md、html、pdf、docx，切块后生成 embedding 和候选证据。
2. PostgreSQL 建立全文 GIN 与 pgvector HNSW 索引；检索融合词法、向量、轻量 rerank 和关系扩展，SQLite 提供可测试降级。
3. 正式知识具备证据、版本号、发布/撤回状态、审核记录、关系证据和审计事件。
4. Celery 处理互动聚合、文档解析、Outbox 和隐私数据清理；开发环境无 Redis 时安全降级为进程内后台任务。
5. 管理台支持候选审核、文档导入、关系管理、详情治理记录、审计查询和质量趋势。
6. 模型配置中心支持租户/知识空间级 LLM 与 Embedding 连接，API Key 加密入库、只读掩码、连接测试和无需重启的运行时切换。

## 已落地的可观测与评测

1. Prometheus 暴露受保护指标，结构化日志默认启用；配置 OTLP 后自动接入 FastAPI/SQLAlchemy trace，Langfuse 参数已预留。
2. 已建立权限、脱敏、多用户阈值、私有记忆隔离、文档导入和混合检索回归测试，并提供 Golden retrieval 数据集与执行脚本。
3. 保持单 Agent 架构；只有评测出现明确瓶颈时才拆分 Ingestion、Research、Curator Agent。

## 上线前必须替换/补齐

1. 使用企业 OIDC/OAuth2 替换本地管理员口令，并将所有 `change-me-*` 密钥放入密钥管理系统。
   `CONFIG_ENCRYPTION_KEY` 必须由密钥管理系统托管并建立轮换/备份流程，否则历史 API Key 将无法解密。
2. 接入生产 embedding 与 rerank 服务；本地哈希向量只用于离线开发和可重复测试。
3. 在对象存储入口增加病毒扫描、文件内容安全策略和大文件异步限流。
4. 对 policy 等高风险类型增加双人审批和职责分离；当前版本强制人工审核但仍是单人决策。
5. 建立真实业务 Golden Set，持续测召回率、忠实度、泄露率、拒答准确率和审核转化率。

## 不可突破的约束

- 知识后台仅管理员可见；未授权访问返回 404。
- 用户侧提示词、响应和工具结果不得包含知识条目结构或内部检索上下文。
- 原始用户 ID 不进入公共知识域，只保存加盐哈希。
- 用户私有记忆、公共知识和运行时 checkpoint 使用不同表/Schema。
- 互动信号不自动成为正式知识，高风险内容必须人工审核。
