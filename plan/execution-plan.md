#   专家团 — 详细执行计划

> 本文档用于指导后续多智能体协作开发。基于设计文档的批判性审查，非照搬原报告。

---

## 一、设计文档批判性审查摘要

### 1.1 后端架构审查（报告4 + 报告6）

| 问题 | 原设计 | 审查结论 |
|------|--------|---------|
| 技术栈 | Node.js + Fastify + Drizzle ORM | **改为 Python + FastAPI + SQLAlchemy**。FastAPI 原生 async、SSE 支持好、Pydantic 校验强、生态成熟 |
| 数据库表数 | 12 张表 | **砍到 7 张**。`discussion_rounds`、`token_usage_logs`、`config_snapshots` 等可合并或推迟 |
| SSE 协议 | 报告4 定义了 12 种事件类型 | **MVP 砍到 5 种**：`thinking`、`message`、`artifact`、`error`、`done` |
| DiscussionExecutor | 完整状态机 + 暂停/恢复/取消 | **MVP 只做线性执行**，暂停/恢复为 phase-2 |
| ContextBuilder | Token 预算 + 角色精简 + 滚动摘要 + 片段检索 | **MVP 简化**：全局摘要 + 相关文件全文截断注入，不做向量检索 |
| AES-256-GCM 加密 | 报告4 和报告6 都提了但细节不同 | **采纳报告4 方案**，用 Python `cryptography` 库实现 |
| 降级策略 | 报告6 设计了多层降级 | **MVP 只做一层**：API 调用失败 → 重试一次 → 报错给用户 |

**关键矛盾**：报告4（架构师）强调"不要过度设计"，但自己定义了 12 张表和复杂的演进路径。报告6（自动化工程师）的实现细节反而更务实。以报告6 的务实精神为准。

### 1.2 前端架构审查（报告7 + 报告5 + 报告2）

| 问题 | 原设计 | 审查结论 |
|------|--------|---------|
| 服务端状态管理 | Zustand + TanStack Query 双层 | **MVP 只用 Zustand**。本地后端延迟极低，TanStack Query 的缓存/重试机制收益不大，增加复杂度 |
| 页面数量 | 7 个页面 | **MVP 砍到 4 页**：设置页、角色卡管理页、群聊创建页、讨论工作台页 |
| 动画系统 | 报告5 设计了呼吸动画、shimmer、轮次分隔线动画等 | **MVP 只保留**：骨架屏 shimmer、thinking→message 过渡、自动滚动。其余推迟 |
| 专家气质色 | 12 色系统 | **MVP 用 6 色**，够覆盖内置角色 |
| 表单校验 | React Hook Form + Zod | **保留**，这是正确选择 |
| Markdown 渲染 | react-markdown + remark-gfm | **保留**，讨论产出需要 |

**关键矛盾**：报告7（实用工程师）说"不做复杂组件库"，但报告5（创意工程师）设计了大量自定义动画组件。MVP 以报告7 的务实路线为准，动画细节推迟。

### 1.3 数据/产品审查（报告1 + 报告3 + 设计方案）

| 问题 | 原设计 | 审查结论 |
|------|--------|---------|
| MVP 功能数 | 13 项必做 | **砍到 8 项**（见下方 MVP 定义） |
| 工作模式 | 3 种：代码文档/纯文档/代码 | **MVP 只做代码文档模式**。这是价值最高的模式，纯文档和代码模式推迟 |
| 内置角色 | 7 个（主持人 + 6 专家） | **MVP 做 4 个**：主持人、产品经理、架构师、文档专家 |
| 讨论策略 | 3 种：快速/标准/严格评审 | **MVP 只做标准模式**（初步观点 + 交叉质询 + 汇总） |
| 讨论轮数 | 无明确上限建议 | **强制上限 5 轮**，主持人可在第 3 轮后推动收敛 |
| 文件处理管线 | 扫描→提取→摘要→关键词→检索 | **MVP 简化**：扫描→提取→全文截断注入（不做摘要和关键词检索） |
| 角色卡模板 | 定义了完整 JSON schema | **保留**，但简化 `constraints` 和 `outputStyle` 为可选字段 |
| Token 预估 | 报告1 设计了复杂预估模型 | **MVP 不做预估**，只设硬性上限（每轮 max_tokens、总轮数） |

**关键矛盾**：报告3（产品经理）说"不是让 AI 替你思考"，但设计方案的 MVP 闭环（配置模型→创建角色卡→创建群聊→加入共享资料→多专家讨论→生成产物→保存到指定目录）有 7 步，对新用户来说太长。需要简化首次体验路径。

---

## 二、最终技术栈决策

### 2.1 后端（Python）

| 组件 | 选型 | 理由 |
|------|------|------|
| Web 框架 | **FastAPI** | 原生 async、SSE 支持、Pydantic v2 校验、自动 OpenAPI 文档 |
| ORM | **SQLAlchemy 2.0** (async) | 成熟稳定、支持 SQLite 和 PostgreSQL、迁移工具 Alembic |
| 数据库 | **SQLite** (MVP) | 本地优先、零配置、单文件。后期可切 PostgreSQL |
| 加密 | **cryptography** (Fernet/AES) | Python 标准加密库，比手写 AES-GCM 安全 |
| SSE | **sse-starlette** | FastAPI 生态的 SSE 标准库 |
| LLM 调用 | **httpx** | 异步 HTTP 客户端，调用 OpenAI-compatible API |
| 日志 | **structlog** | 结构化日志，天然支持脱敏 |
| 配置 | **pydantic-settings** | 环境变量 + .env 文件管理 |
| 任务队列 | **不需要 MVP** | 讨论是同步 SSE 流，不需要 Celery/BullMQ |

### 2.2 前端（保留原选型，去掉 TanStack Query）

| 组件 | 选型 | 版本 |
|------|------|------|
| 框架 | React + TypeScript | 18.3 + 5.6 |
| 构建 | Vite | 5.4 |
| 路由 | React Router | v6.26 |
| 全局状态 | Zustand | 5.0 |
| 表单 | React Hook Form + Zod | 7.53 + 3.23 |
| 样式 | Tailwind CSS | 3.4 |
| Markdown | react-markdown + remark-gfm | 9.0 + 4.0 |
| HTTP | fetch API (原生) | — |

### 2.3 桌面壳

| 组件 | 选型 | 说明 |
|------|------|------|
| 桌面框架 | **Tauri 2.0** | Rust 壳 + WebView，比 Electron 轻量 |
| 后端进程 | Python FastAPI 作为 sidecar | Tauri 启动时拉起 Python 进程，通过 localhost 通信 |

---

## 三、数据库设计（7 张表，非原设计的 12 张）

```sql
-- 1. 模型服务商
CREATE TABLE providers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'openai-compatible',
    base_url TEXT NOT NULL,
    api_key_encrypted TEXT NOT NULL,  -- AES 加密后的密文
    default_model TEXT NOT NULL,
    default_temperature REAL DEFAULT 0.7,
    default_max_tokens INTEGER DEFAULT 4096,
    enabled INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 2. 角色卡
CREATE TABLE role_cards (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    expertise TEXT NOT NULL,        -- JSON array
    responsibilities TEXT NOT NULL, -- JSON array
    constraints TEXT,               -- JSON array, optional
    system_prompt TEXT NOT NULL,
    output_style TEXT,
    default_provider_id TEXT REFERENCES providers(id),
    default_model TEXT,
    temperature REAL DEFAULT 0.7,
    is_builtin INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 3. 专家群聊
CREATE TABLE rooms (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    goal TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'code_document',
    strategy TEXT NOT NULL DEFAULT 'standard',
    output_directory TEXT NOT NULL,
    round_limit INTEGER DEFAULT 5,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- 4. 群聊-角色关联（多对多）
CREATE TABLE room_participants (
    room_id TEXT REFERENCES rooms(id) ON DELETE CASCADE,
    role_card_id TEXT REFERENCES role_cards(id),
    provider_id TEXT REFERENCES providers(id),  -- 本次使用的 provider
    model_override TEXT,                         -- 本次使用的模型
    PRIMARY KEY (room_id, role_card_id)
);

-- 5. 共享数据源
CREATE TABLE shared_sources (
    id TEXT PRIMARY KEY,
    room_id TEXT REFERENCES rooms(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,  -- 'file' | 'folder' | 'text'
    path TEXT,                  -- 文件/文件夹路径
    content TEXT,               -- 粘贴的文本内容
    file_count INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

-- 6. 消息
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    room_id TEXT REFERENCES rooms(id) ON DELETE CASCADE,
    sender_type TEXT NOT NULL,  -- 'user' | 'expert' | 'orchestrator' | 'system'
    sender_id TEXT,             -- role_card_id for experts
    content TEXT NOT NULL,
    citations TEXT,             -- JSON array of {source_id, file, snippet}
    round INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

-- 7. 产出文件
CREATE TABLE artifacts (
    id TEXT PRIMARY KEY,
    room_id TEXT REFERENCES rooms(id) ON DELETE CASCADE,
    artifact_type TEXT NOT NULL,  -- 'markdown' | 'text' | 'code' | 'csv'
    title TEXT NOT NULL,
    file_path TEXT NOT NULL,
    summary TEXT,
    created_at TEXT NOT NULL
);
```

**砍掉的表**（原设计有但 MVP 不需要）：
- `discussion_rounds` → 合并到 `messages.round` 字段
- `token_usage_logs` → phase-2，MVP 只在日志中记录
- `config_snapshots` → 用 `room` 表本身 + participants 关联即可还原
- `knowledge_chunks` → MVP 不做向量检索，全文截断注入
- `citations` 独立表 → 合并到 `messages.citations` JSON 字段

---

## 四、MVP 功能定义（精简版）

### 4.1 MVP 必做（8 项，原 13 项砍了 5 项）

| # | 功能 | 说明 |
|---|------|------|
| 1 | Provider 配置与连接测试 | 添加 API Key、Base URL、测试连通性 |
| 2 | 角色卡 CRUD + 4 个内置角色 | 主持人、产品经理、架构师、文档专家 |
| 3 | 创建群聊 | 选角色、输入目标、选产出目录 |
| 4 | 文件上传 + 文件夹扫描 | 支持 .txt/.md/.json/.csv/.py/.ts/.js 等文本文件 |
| 5 | 标准模式讨论 | 初步观点 → 交叉质询 → 汇总，最多 5 轮 |
| 6 | 代码文档模式产出 | 生成结构化 Markdown 技术方案 |
| 7 | 产出保存到指定目录 | final-plan.md + discussion-log.md |
| 8 | 讨论记录持久化 | SQLite 存储，支持查看历史 |

### 4.2 MVP 推迟（明确不做）

| 功能 | 推迟理由 |
|------|---------|
| 纯文档模式 | 代码文档模式已覆盖核心价值 |
| 代码模式 | 同上 |
| 快速/严格评审策略 | 标准模式够用 |
| 向量检索 / 知识库 | 全文截断注入在 MVP 阶段够用 |
| 暂停/恢复讨论 | 线性执行够用 |
| 用户中途插话 | phase-2，MVP 讨论是全自动流程 |
| .docx/.xlsx/.pdf 解析 | 文本文件够用 |
| 费用统计 | 只做硬性 token 上限 |
| 多模型混用 | MVP 所有角色用同一个 provider |
| 角色卡导入导出 | phase-2 |
| 专家互相引用 | MVP 简化处理 |

---

## 五、API 设计（28 个端点）

### 5.1 Provider 管理

```
POST   /api/providers              创建 provider
GET    /api/providers              列出所有 providers
GET    /api/providers/{id}         获取单个
PUT    /api/providers/{id}         更新
DELETE /api/providers/{id}         删除
POST   /api/providers/{id}/test    测试连接
```

### 5.2 角色卡管理

```
POST   /api/role-cards             创建角色卡
GET    /api/role-cards             列出所有（支持 ?builtin=true 筛选）
GET    /api/role-cards/{id}        获取单个
PUT    /api/role-cards/{id}        更新（内置角色不可修改）
DELETE /api/role-cards/{id}        删除（内置角色不可删除）
POST   /api/role-cards/{id}/copy   复制角色卡
```

### 5.3 群聊管理

```
POST   /api/rooms                  创建群聊
GET    /api/rooms                  列出所有
GET    /api/rooms/{id}             获取单个（含参与者和消息）
DELETE /api/rooms/{id}             删除（级联删除关联数据）
```

### 5.4 共享数据

```
POST   /api/rooms/{id}/sources     添加数据源（上传文件/指定文件夹/粘贴文本）
GET    /api/rooms/{id}/sources     列出数据源
DELETE /api/sources/{id}           删除数据源
```

### 5.5 讨论引擎

```
POST   /api/rooms/{id}/start       启动讨论（SSE 流）
GET    /api/rooms/{id}/messages    获取讨论消息列表
GET    /api/rooms/{id}/messages/stream  SSE 实时消息流
```

### 5.6 产出

```
POST   /api/rooms/{id}/synthesize  生成最终产物
GET    /api/rooms/{id}/artifacts   列出产出文件
GET    /api/artifacts/{id}/content 获取产出内容
```

### 5.7 系统

```
GET    /api/health                 健康检查
GET    /api/config                 获取运行配置（脱敏后）
```

---

## 六、SSE 事件协议（5 种事件）

```
event: thinking
data: {"room_id":"...","role":"架构师","status":"思考中"}

event: message
data: {"id":"...","room_id":"...","sender_type":"expert","sender_id":"role_architect","content":"...","citations":[],"round":1}

event: artifact
data: {"id":"...","room_id":"...","type":"markdown","title":"技术方案","file_path":"..."}

event: error
data: {"room_id":"...","error":"API 调用失败: rate limit exceeded","recoverable":false}

event: done
data: {"room_id":"...","total_rounds":3,"total_messages":12,"artifact_count":1}
```

---

## 七、目录结构

```
expert-room/
├── backend/                        # Python 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app 入口
│   │   ├── config.py               # pydantic-settings 配置
│   │   ├── database.py             # SQLAlchemy engine + session
│   │   ├── models/                 # SQLAlchemy ORM 模型
│   │   │   ├── provider.py
│   │   │   ├── role_card.py
│   │   │   ├── room.py
│   │   │   ├── message.py
│   │   │   ├── shared_source.py
│   │   │   └── artifact.py
│   │   ├── schemas/                # Pydantic 请求/响应 schema
│   │   │   ├── provider.py
│   │   │   ├── role_card.py
│   │   │   ├── room.py
│   │   │   └── message.py
│   │   ├── routers/                # API 路由
│   │   │   ├── providers.py
│   │   │   ├── role_cards.py
│   │   │   ├── rooms.py
│   │   │   ├── sources.py
│   │   │   ├── discussion.py
│   │   │   └── artifacts.py
│   │   ├── services/               # 业务逻辑层
│   │   │   ├── provider_service.py
│   │   │   ├── role_card_service.py
│   │   │   ├── room_service.py
│   │   │   ├── file_ingestion.py   # 文件扫描与内容提取
│   │   │   ├── context_builder.py  # 上下文构建
│   │   │   ├── orchestrator.py     # 讨论调度
│   │   │   ├── model_client.py     # 统一模型调用
│   │   │   ├── artifact_writer.py  # 产出生成
│   │   │   └── crypto.py           # API Key 加解密
│   │   ├── seed/                   # 内置角色卡种子数据
│   │   │   └── builtin_roles.json
│   │   └── utils/
│   │       ├── logger.py           # structlog 配置 + 脱敏
│   │       └── file_filter.py      # 文件过滤规则
│   ├── alembic/                    # 数据库迁移
│   │   └── versions/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── requirements.txt
│   └── tests/
│       ├── test_providers.py
│       ├── test_role_cards.py
│       ├── test_rooms.py
│       ├── test_file_ingestion.py
│       ├── test_context_builder.py
│       ├── test_orchestrator.py
│       └── test_model_client.py
├── frontend/                       # React 前端
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   ├── pages/
│   │   │   ├── SettingsPage.tsx
│   │   │   ├── RoleCardsPage.tsx
│   │   │   ├── RoomCreatePage.tsx
│   │   │   └── DiscussionPage.tsx
│   │   ├── components/
│   │   │   ├── provider/
│   │   │   ├── role-card/
│   │   │   ├── room/
│   │   │   ├── discussion/
│   │   │   └── shared/
│   │   ├── hooks/
│   │   │   ├── useDiscussionSSE.ts
│   │   │   └── useProviders.ts
│   │   ├── stores/
│   │   │   ├── providerStore.ts
│   │   │   ├── roleCardStore.ts
│   │   │   └── roomStore.ts
│   │   ├── api/                    # HTTP 客户端封装
│   │   │   └── client.ts
│   │   ├── types/                  # TypeScript 类型定义
│   │   │   └── index.ts
│   │   └── styles/
│   │       └── globals.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── index.html
├── docs/                           # 项目文档
│   ├── api-contracts.md
│   ├── stage1-test.md
│   └── stage2-test.md
├── project/plan/                   # 计划文档
│   └── execution-plan.md           # 本文档
└── CLAUDE.md
```

---

## 八、分阶段开发计划

### 阶段 0：项目初始化与脚手架

**目标**：前后端项目能跑起来，数据库能迁移，Git 仓库建立。

**任务清单**：

| # | 任务 | 负责角色 | 产出 |
|---|------|---------|------|
| 0.1 | 初始化 Git 仓库，创建 main 分支 | — | `.gitignore`、`README.md` |
| 0.2 | 创建 Python 后端项目（pyproject.toml、目录结构） | 后端工程师 | 可运行的 FastAPI 空应用 |
| 0.3 | 配置 SQLAlchemy + Alembic + SQLite | 后端工程师 | 数据库连接可测试 |
| 0.4 | 创建 7 张表的 Alembic 迁移 | 后端工程师 | `alembic upgrade head` 成功 |
| 0.5 | 配置 structlog + 日志脱敏 | 后端工程师 | 日志输出格式正确 |
| 0.6 | 配置 pydantic-settings + .env | 后端工程师 | 配置加载可测试 |
| 0.7 | 创建 React 前端项目（Vite + TS + Tailwind） | 前端工程师 | 可运行的空应用 |
| 0.8 | 配置 React Router + Zustand | 前端工程师 | 路由和状态管理就绪 |
| 0.9 | 前后端连通性验证 | 全员 | `/api/health` 可从前端调用 |

**Git 操作**：
```bash
git checkout -b feature/stage0-scaffold
# ... 开发 ...
git add .
git commit -m "feat: 完成阶段0项目脚手架" -m "阶段0内容：
- Python FastAPI 后端项目初始化
- SQLAlchemy + Alembic + SQLite 配置
- 7 张数据库表迁移就绪
- structlog 日志系统 + 脱敏配置
- pydantic-settings 环境配置
- React + Vite + TypeScript 前端项目初始化
- Tailwind CSS + React Router + Zustand 配置
验证方式：详见 docs/stage0-test.md"
git push origin feature/stage0-scaffold
```

**验证方式**：
```bash
# 后端
cd backend && uvicorn app.main:app --reload
curl http://localhost:8000/api/health  # 返回 {"status": "ok"}

# 前端
cd frontend && npm run dev
# 浏览器打开 http://localhost:5173 显示空页面

# 数据库
cd backend && alembic upgrade head
sqlite3 expert_room.db ".tables"  # 显示 7 张表
```

---

### 阶段 1：Provider 管理 + 角色卡管理

**目标**：用户能配置 API Key 并管理角色卡。

**任务清单**：

| # | 任务 | 负责角色 | 产出 |
|---|------|---------|------|
| 1.1 | Provider CRUD API（6 个端点） | 后端工程师 | 完整的 Provider 管理接口 |
| 1.2 | API Key AES 加解密服务 | 后端工程师 | `crypto.py`，密文存储，日志脱敏 |
| 1.3 | Provider 连接测试（调用模型 API） | 后端工程师 | `/test` 端点返回连通性 |
| 1.4 | 角色卡 CRUD API（6 个端点） | 后端工程师 | 完整的角色卡管理接口 |
| 1.5 | 内置角色卡种子数据（4 个角色） | 数据工程师 | `builtin_roles.json` |
| 1.6 | 种子数据自动加载（应用启动时） | 后端工程师 | 启动时自动插入内置角色 |
| 1.7 | 设置页 UI（Provider 管理） | 前端工程师 | 表单 + 列表 + 测试连接按钮 |
| 1.8 | 角色卡管理页 UI | 前端工程师 | 列表 + 新建/编辑/复制/删除 |
| 1.9 | 角色卡预览（显示 system prompt） | 前端工程师 | 预览弹窗 |

**Git 操作**：
```bash
git checkout -b feature/stage1-provider-roles
# ... 开发 ...
git commit -m "feat: 完成阶段1 Provider与角色卡管理" -m "阶段1内容：
- Provider CRUD API（6 端点）+ AES 加解密
- Provider 连通性测试端点
- 角色卡 CRUD API（6 端点）+ 内置角色种子数据
- 设置页 UI（Provider 管理表单和列表）
- 角色卡管理页 UI（列表、新建、编辑、复制、删除、预览）
验证方式：详见 docs/stage1-test.md"
git push origin feature/stage1-provider-roles
```

**验证方式**：
```bash
# Provider CRUD
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","base_url":"https://api.openai.com/v1","api_key":"sk-...","default_model":"gpt-4o"}'
curl http://localhost:8000/api/providers
curl -X POST http://localhost:8000/api/providers/{id}/test

# 角色卡
curl http://localhost:8000/api/role-cards  # 返回 4 个内置角色
curl http://localhost:8000/api/role-cards?builtin=true
```

---

### 阶段 2：群聊创建 + 文件处理

**目标**：用户能创建群聊、上传文件、指定文件夹。

**任务清单**：

| # | 任务 | 负责角色 | 产出 |
|---|------|---------|------|
| 2.1 | 群聊 CRUD API（4 个端点） | 后端工程师 | Room 管理接口 |
| 2.2 | 群聊参与者关联管理 | 后端工程师 | room_participants 多对多处理 |
| 2.3 | 文件上传 API（multipart/form-data） | 后端工程师 | 文件保存到临时目录 |
| 2.4 | 文件夹扫描服务 | 后端工程师 | 递归扫描 + 过滤规则（排除 node_modules 等） |
| 2.5 | 文件内容提取（.txt/.md/.json/.csv/.py/.ts/.js） | 后端工程师 | 文本文件读取，编码检测 |
| 2.6 | 共享数据源 CRUD API | 后端工程师 | source 管理接口 |
| 2.7 | 群聊创建页 UI | 前端工程师 | 表单：目标、模式、选角色、选 provider、产出目录 |
| 2.8 | 文件上传组件 | 前端工程师 | 拖拽上传 + 文件夹选择（Tauri 文件对话框） |
| 2.9 | 群聊列表页 UI | 前端工程师 | 显示历史群聊、状态、快速进入 |

**Git 操作**：
```bash
git checkout -b feature/stage2-room-sources
# ... 开发 ...
git commit -m "feat: 完成阶段2群聊创建与文件处理" -m "阶段2内容：
- 群聊 CRUD API + 参与者关联管理
- 文件上传 API + 文件夹扫描服务
- 文件内容提取（txt/md/json/csv/py/ts/js）
- 共享数据源 CRUD API
- 群聊创建页 UI（目标、模式、角色选择、产出目录）
- 文件上传组件（拖拽 + 文件夹选择）
- 群聊列表页 UI
验证方式：详见 docs/stage2-test.md"
git push origin feature/stage2-room-sources
```

**验证方式**：
```bash
# 创建群聊
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name":"测试群聊","goal":"设计登录模块","mode":"code_document","participant_role_ids":["role_pm","role_architect"],"output_directory":"/tmp/output"}'

# 上传文件
curl -X POST http://localhost:8000/api/rooms/{id}/sources \
  -F "source_type=file" \
  -F "file=@README.md"

# 指定文件夹
curl -X POST http://localhost:8000/api/rooms/{id}/sources \
  -H "Content-Type: application/json" \
  -d '{"source_type":"folder","path":"/path/to/project"}'
```

---

### 阶段 3：讨论引擎（核心）

**目标**：多专家能按标准模式进行讨论并产生消息流。

**任务清单**：

| # | 任务 | 负责角色 | 产出 |
|---|------|---------|------|
| 3.1 | ModelClient 统一调用封装 | 后端工程师 | 支持 OpenAI-compatible API，错误处理，重试 |
| 3.2 | ContextBuilder 上下文构建 | 数据工程师 + 后端工程师 | system prompt 组装 + 资料注入 + 滚动摘要 |
| 3.3 | Orchestrator 讨论调度 | 后端工程师 | 轮次管理、发言顺序、收敛判断 |
| 3.4 | 讨论启动 API（SSE 流） | 后端工程师 | `/start` 端点，SSE 事件推送 |
| 3.5 | 消息持久化 | 后端工程师 | 每条消息写入 messages 表 |
| 3.6 | 讨论工作台页 UI | 前端工程师 | 多专家对话展示、轮次标识、进度条 |
| 3.7 | SSE Hook（useDiscussionSSE） | 前端工程师 | 事件监听、断线重连、错误处理 |
| 3.8 | Thinking 状态动画 | 前端工程师 | 专家"思考中"动画效果 |
| 3.9 | 讨论完成检测 | 后端工程师 | 检测收敛或达到轮次上限，发送 done 事件 |

**Git 操作**：
```bash
git checkout -b feature/stage3-discussion-engine
# ... 开发 ...
git commit -m "feat: 完成阶段3讨论引擎" -m "阶段3内容：
- ModelClient 统一模型调用封装（OpenAI-compatible）
- ContextBuilder 上上下文构建（system prompt + 资料注入 + 滚动摘要）
- Orchestrator 讨论调度（轮次管理、发言顺序、收敛判断）
- 讨论启动 API + SSE 事件流推送
- 消息持久化到 messages 表
- 讨论工作台页 UI（多专家对话、轮次标识、进度条）
- useDiscussionSSE Hook（事件监听、断线重连）
- Thinking 状态动画
验证方式：详见 docs/stage3-test.md"
git push origin feature/stage3-discussion-engine
```

**验证方式**：
```bash
# 启动讨论
curl -X POST http://localhost:8000/api/rooms/{id}/start
# 观察 SSE 流输出 thinking/message 事件

# 查看消息
curl http://localhost:8000/api/rooms/{id}/messages
# 返回多轮讨论消息
```

---

### 阶段 4：产出生成 + 保存

**目标**：讨论结束后能生成最终 Markdown 产物并保存到指定目录。

**任务清单**：

| # | 任务 | 负责角色 | 产出 |
|---|------|---------|------|
| 4.1 | ArtifactWriter 产出生成 | 后端工程师 + 数据工程师 | 汇总讨论 → 生成结构化 Markdown |
| 4.2 | 产出文件写入指定目录 | 后端工程师 | 创建子目录、写入文件 |
| 4.3 | 讨论记录生成（discussion-log.md） | 后端工程师 | 格式化讨论历史为 Markdown |
| 4.4 | 产出 API（synthesize + 列表 + 内容） | 后端工程师 | 3 个端点 |
| 4.5 | 产物预览组件 | 前端工程师 | Markdown 渲染预览 |
| 4.6 | 产出文件列表展示 | 前端工程师 | 显示产出文件、一键打开目录 |
| 4.7 | 讨论完成后的 UI 状态切换 | 前端工程师 | 从讨论视图切换到产出预览 |

**Git 操作**：
```bash
git checkout -b feature/stage4-artifacts
# ... 开发 ...
git commit -m "feat: 完成阶段4产出生成与保存" -m "阶段4内容：
- ArtifactWriter 产出生成（汇总讨论 → 结构化 Markdown）
- 产出文件写入指定目录 + 子目录创建
- 讨论记录生成（discussion-log.md）
- 产出 API（synthesize、列表、内容获取 3 端点）
- 产物预览组件（Markdown 渲染）
- 产出文件列表展示
- 讨论完成 → 产出预览 UI 状态切换
验证方式：详见 docs/stage4-test.md"
git push origin feature/stage4-artifacts
```

**验证方式**：
```bash
# 生成产出
curl -X POST http://localhost:8000/api/rooms/{id}/synthesize

# 查看产出目录
ls /tmp/output/2026-05-29_测试群聊/
# 应包含: final-plan.md, discussion-log.md, room-config.json

# 查看产出内容
curl http://localhost:8000/api/rooms/{id}/artifacts
curl http://localhost:8000/api/artifacts/{id}/content
```

---

### 阶段 5：集成测试 + 体验优化 + 安全加固

**目标**：端到端流程跑通，安全检查通过，体验可用。

**任务清单**：

| # | 任务 | 负责角色 | 产出 |
|---|------|---------|------|
| 5.1 | 端到端流程测试 | 全员 | 从配置到产出的完整流程验证 |
| 5.2 | API Key 安全审计 | 后端工程师 | 确认密文存储、日志脱敏、不暴露给前端 |
| 5.3 | 文件路径安全校验 | 后端工程师 | 防止路径遍历攻击 |
| 5.4 | 错误处理完善 | 全员 | 统一错误响应格式、用户友好提示 |
| 5.5 | Token 硬性上限 | 后端工程师 | 每轮 max_tokens、总轮数限制 |
| 5.6 | Tauri 集成（Python sidecar 进程管理） | 后端工程师 | Tauri 启动/停止 Python 进程 |
| 5.7 | 前端打包 + Tauri 打包 | 前端工程师 | 可分发的桌面应用 |
| 5.8 | 基础文档（README、使用说明） | 文档专家 | 用户可上手的文档 |

**Git 操作**：
```bash
git checkout -b feature/stage5-integration
# ... 开发 ...
git commit -m "feat: 完成阶段5集成测试与安全加固" -m "阶段5内容：
- 端到端流程测试（配置→角色卡→群聊→讨论→产出）
- API Key 安全审计（密文存储、日志脱敏、前端不暴露）
- 文件路径安全校验（防路径遍历）
- 统一错误处理 + 用户友好提示
- Token 硬性上限（每轮 + 总轮数）
- Tauri 集成（Python sidecar 进程管理）
- 前端打包 + Tauri 打包
- 基础文档
验证方式：详见 docs/stage5-test.md"
git push origin feature/stage5-integration

# 打里程碑 tag
git tag -a v0.1.0-mvp -m "MVP 初版完成"
git push origin v0.1.0-mvp
```

---

## 九、内置角色卡设计（4 个，非原设计的 7 个）

### 9.1 主持人（Orchestrator）

```json
{
  "name": "主持人",
  "description": "控制讨论流程，推动专家发言和结论收敛",
  "expertise": ["流程管理", "冲突识别", "结论收敛"],
  "responsibilities": [
    "安排专家发言顺序",
    "识别讨论中的冲突和遗漏",
    "在信息足够时推动结论收敛",
    "要求专家补充缺失信息"
  ],
  "constraints": [
    "不代替专家完成内容",
    "不在讨论未充分时强行结束"
  ],
  "system_prompt_template": "你是专家群聊主持人。你的任务是控制讨论流程，而不是替专家完成全部内容。\n\n本次任务目标：{goal}\n当前工作模式：代码文档模式\n共享资料摘要：{data_summary}\n已有讨论摘要：{discussion_summary}\n\n你需要：\n1. 根据任务目标安排专家发言顺序。\n2. 识别讨论中的冲突、遗漏和风险。\n3. 在信息足够时推动结论收敛。\n4. 最终要求文档专家生成产物。"
}
```

### 9.2 产品经理

```json
{
  "name": "产品经理",
  "description": "明确需求、用户场景、优先级和 MVP 范围",
  "expertise": ["需求分析", "用户场景", "优先级排序", "MVP 定义"],
  "responsibilities": [
    "明确用户目标和边界",
    "拆分功能优先级",
    "定义 MVP 和后续版本边界",
    "检查是否满足真实使用场景"
  ],
  "constraints": [
    "不做超出技术可行性的承诺",
    "结论需要说明优先级理由"
  ]
}
```

### 9.3 系统架构师

```json
{
  "name": "系统架构师",
  "description": "设计模块、技术边界和整体流程",
  "expertise": ["架构设计", "模块拆分", "技术选型", "风险评估"],
  "responsibilities": [
    "设计整体架构",
    "拆分模块边界",
    "识别技术风险",
    "做技术取舍决策"
  ],
  "constraints": [
    "避免过度设计",
    "优先考虑初版可实现性",
    "结论需要说明取舍理由"
  ]
}
```

### 9.4 文档专家

```json
{
  "name": "文档专家",
  "description": "整理讨论结果，生成结构化最终文档",
  "expertise": ["技术写作", "文档结构", "信息整合", "可读性优化"],
  "responsibilities": [
    "整理讨论结果为结构化文档",
    "统一文档格式和风格",
    "确保结论清晰、可执行",
    "保留引用来源"
  ],
  "constraints": [
    "不添加讨论中未出现的内容",
    "保持客观，不偏向某个专家的观点"
  ]
}
```

---

## 十、关键 Prompt 模板

### 10.1 专家发言 Prompt（ContextBuilder 组装）

```
你是{name}，一位{description}。

## 专业能力
{expertise}

## 职责
{responsibilities}

## 约束
{constraints}

## 本次任务
目标：{goal}
工作模式：代码文档模式

## 共享资料
{file_contents_truncated}

## 已有讨论
{rolling_summary}

## 本轮要求
请从你的专业角度，对当前议题发表意见。
要求：
- 引用共享资料中的具体内容时，请标注来源文件名
- 区分"资料中明确的信息"和"你的推断/建议"
- 回复控制在 500 字以内
```

### 10.2 汇总产出 Prompt（ArtifactWriter 使用）

```
你是文档专家。请根据以下讨论记录，生成一份结构化的 Markdown 技术方案文档。

## 讨论记录
{full_discussion}

## 产出要求
请按以下结构生成文档：

# {goal}

## 1. 背景与目标
## 2. 需求拆解
## 3. 总体方案
## 4. 模块设计
## 5. 数据结构 / 接口设计
## 6. 实施步骤
## 7. 测试与验收标准
## 8. 风险与取舍
## 9. 后续迭代建议

要求：
- 内容必须来自讨论记录，不要编造
- 引用关键决策时标注是哪位专家提出的
- 结论要清晰、可执行
- 使用 Markdown 格式
```

---

## 十一、风险与应对

| 风险 | 可能性 | 影响 | 应对方案 |
|------|--------|------|---------|
| LLM API 调用失败/超时 | 高 | 讨论中断 | 重试一次 + 错误事件推送给前端 + 保存已讨论内容 |
| 讨论发散无法收敛 | 中 | 产出质量差 | 主持人第 3 轮后强制收敛 + 最大 5 轮硬限 |
| Token 超限导致上下文截断 | 高 | 后轮专家看不到前面内容 | 滚动摘要替代完整历史 + 资料截断注入 |
| 文件编码问题 | 中 | 文件读取失败 | 使用 `chardet` 检测编码，失败时跳过并警告 |
| API Key 泄露 | 低 | 安全事故 | AES 加密存储 + structlog 脱敏 + 前端不获取明文 Key |
| Tauri + Python 进程管理 | 中 | 桌面应用启动失败 | Tauri sidecar 模式 + 健康检查 + 自动重启 |
| 讨论费用过高 | 中 | 用户不满 | 硬性 token 上限 + 轮数限制 + 开始前提示预估 |

---

## 十二、开发角色分工建议

| 角色 | 负责阶段 | 核心交付 |
|------|---------|---------|
| **后端工程师** | 全阶段 | FastAPI 应用、数据库、API、讨论引擎、文件处理、安全 |
| **前端工程师** | 全阶段 | React 应用、页面组件、SSE Hook、状态管理、Tauri 集成 |
| **数据工程师** | 阶段 3-4 | Prompt 模板、ContextBuilder、ArtifactWriter、内置角色数据 |
| **测试工程师** | 阶段 1-5 | 单元测试、集成测试、端到端验证 |
| **文档专家** | 阶段 5 | README、使用说明、API 文档 |

---

## 十三、里程碑时间线（参考）

| 里程碑 | 阶段 | 标志 |
|--------|------|------|
| M0: 项目启动 | 阶段 0 | Git 仓库建立，前后端可运行 |
| M1: 基础管理 | 阶段 1 | Provider + 角色卡管理可用 |
| M2: 群聊创建 | 阶段 2 | 群聊创建 + 文件处理可用 |
| M3: 讨论引擎 | 阶段 3 | 多专家讨论可跑通 |
| M4: 产出生成 | 阶段 4 | 端到端流程可用 |
| M5: MVP 完成 | 阶段 5 | 可分发的桌面应用 |
| v0.1.0-mvp | — | Git tag 标记 |

---

## 附录 A：审查原始文件索引

| 文件 | 角色 | 主要内容 |
|------|------|---------|
| 专家团初版设计方案.md | 产品设计 | 核心概念、功能模块、数据模型、MVP 定义 |
| 报告1.txt | 数据创意工程师 | Prompt 设计、上下文构建、Token 预估 |
| 报告2.txt | UI/UX 设计师 | 色彩系统、组件规格、布局规则 |
| 报告3.txt | 产品经理 | MVP 范围、用户画像、价值主张 |
| 报告4.txt | 后端架构工程师 | 架构分层、数据模型、API 契约、安全策略 |
| 报告5.txt | 前端创意工程师 | 动画设计、微交互、情绪设计 |
| 报告6.txt | 后端自动化工程师 | 服务实现细节、讨论引擎状态机 |
| 报告7.txt | 前端实用工程师 | React 技术栈、页面实现、SSE Hook |
