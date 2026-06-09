#   专家团 - AI Expert Team Collaboration Workbench

本地优先的 AI 多专家协作讨论工作台。用户配置 LLM API 密钥，创建可复用的专家角色卡，将多个 AI 专家组装进群聊房间讨论任务，最终生成结构化文档、报告或代码草稿。

## 功能特性

### 核心功能

- **Provider 管理** - 配置多个 LLM 服务提供商（OpenAI、Claude 等），支持连接测试
- **角色卡系统** - 创建和管理可复用的专家角色卡，内置 4 个默认角色（主持人、产品经理、系统架构师、文档专家）
- **房间讨论** - 创建讨论房间，选择参与专家，配置讨论策略和轮次限制
- **多轮协作** - 主持人控制讨论节奏，专家轮流发言，自动收敛生成结论
- **数据源管理** - 上传文件、添加文件夹或文本内容作为讨论上下文
- **产物生成** - 讨论完成后生成结构化 Markdown 文档，保存到指定目录
- **实时流式输出** - 通过 SSE 实时展示讨论进度和专家发言

### 工作模式

| 模式 | 说明 | 输出格式 |
|------|------|----------|
| `code_document` | 生成技术方案文档 | 结构化 Markdown |
| `document` | 生成可读报告/材料 | txt, md, csv |
| `code` | 生成核心代码草稿 | 代码 + 集成说明 |

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| **后端** | Python 3.12+ / FastAPI / SQLAlchemy / SQLite |
| **前端** | React 18 / TypeScript 5.6 / Vite 5.4 |
| **状态管理** | Zustand 5.0 / React Hook Form 7.53 / Zod 3.23 |
| **样式** | Tailwind CSS 3.4 |
| **实时通信** | SSE (Server-Sent Events) |
| **安全** | Fernet 加密存储 API Key |
| **数据库** | SQLite + aiosqlite (异步驱动) |
| **ORM** | SQLAlchemy 2.0 + Alembic (迁移) |
| **日志** | structlog |

## 快速开始

### 环境要求

- Python 3.12+
- Node.js 18+
- npm 或 pnpm

### 一键启动（推荐）

#### Windows 用户

需要已安装 Anaconda/Miniconda 并创建 `Test` 环境：

```bash
# 创建 Conda 环境（如果尚未创建）
conda create -n Test python=3.11 -y

# 双击运行启动脚本
start_windows.bat
```

#### Linux 用户

```bash
chmod +x start_linux.sh
./start_linux.sh

# 停止服务
./stop_linux.sh
```

### 手动启动

#### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 设置 ENCRYPT_API_KEYS 和 ENCRYPTION_KEY（用于加密 API 密钥）

# 生成加密密钥
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 初始化数据库
python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"

# 启动服务
uvicorn app.main:app --reload --port 8000
```

#### 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 http://localhost:5173 即可使用。

> **详细文档**：请查看 `ToUse/` 目录下的使用指南。

### 环境变量配置

在 `backend/.env` 中配置以下变量：

```env
# 应用配置
APP_NAME=Expert Room
DEBUG=false

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./expert_room.db

# CORS（JSON 数组格式）
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]

# 安全 - 用于加密 API 密钥（Fernet 格式，32 字节 Base64 编码）
ENCRYPT_API_KEYS=true
ENCRYPTION_KEY=your-generated-key-here

# LLM 默认参数
DEFAULT_MAX_TOKENS=4096
DEFAULT_TEMPERATURE=0.7
MAX_DISCUSSION_ROUNDS=5

# 文件处理
MAX_FILE_SIZE_MB=10
```

## 项目结构

```
project/
├── backend/                    # Python FastAPI 后端
│   ├── alembic/               # 数据库迁移
│   ├── app/
│   │   ├── config.py          # 应用配置
│   │   ├── database.py        # 数据库连接
│   │   ├── main.py            # FastAPI 入口
│   │   ├── middleware/        # 中间件
│   │   ├── models/            # SQLAlchemy 数据模型
│   │   │   ├── provider.py    # LLM 服务提供商
│   │   │   ├── role_card.py   # 专家角色卡
│   │   │   ├── room.py        # 讨论房间
│   │   │   ├── message.py     # 讨论消息
│   │   │   ├── artifact.py    # 生成产物
│   │   │   └── shared_source.py # 共享数据源
│   │   ├── routers/           # API 路由
│   │   │   ├── providers.py   # Provider CRUD + 连接测试
│   │   │   ├── role_cards.py  # 角色卡 CRUD + 复制
│   │   │   ├── rooms.py       # 房间 CRUD
│   │   │   ├── sources.py     # 数据源上传/管理
│   │   │   ├── discussion.py  # 讨论启动/SSE 流
│   │   │   └── artifacts.py   # 产物生成/查看
│   │   ├── schemas/           # Pydantic 数据模式
│   │   ├── seed/              # 内置角色卡种子数据
│   │   │   └── builtin_roles.json
│   │   ├── services/          # 业务逻辑层
│   │   │   ├── orchestrator.py    # 讨论编排器（状态机）
│   │   │   ├── model_client.py    # LLM 调用客户端
│   │   │   ├── context_builder.py # 上下文构建
│   │   │   ├── crypto.py          # API Key 加密服务
│   │   │   ├── artifact_writer.py # 产物生成
│   │   │   └── file_ingestion.py  # 文件处理
│   │   └── utils/             # 工具函数
│   ├── tests/                 # 测试文件
│   └── requirements.txt       # Python 依赖
│
├── frontend/                   # React 前端
│   ├── src/
│   │   ├── api/               # API 客户端
│   │   ├── components/        # 可复用组件
│   │   ├── hooks/             # 自定义 Hooks
│   │   ├── pages/             # 页面组件
│   │   │   ├── HomePage.tsx       # 首页
│   │   │   ├── SettingsPage.tsx   # Provider 配置
│   │   │   ├── RoleCardsPage.tsx  # 角色卡管理
│   │   │   ├── RoomCreatePage.tsx # 创建房间
│   │   │   ├── RoomsPage.tsx      # 房间列表
│   │   │   ├── DiscussionPage.tsx # 讨论进行中
│   │   │   └── ArtifactPage.tsx   # 产物查看
│   │   ├── stores/            # Zustand 状态管理
│   │   ├── styles/            # 全局样式
│   │   └── types/             # TypeScript 类型定义
│   ├── package.json
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   └── vite.config.ts
│
└── docs/                       # 项目文档
```

## API 文档

后端启动后访问以下地址查看完整 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 核心 API 端点

#### Provider 管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/providers` | 创建 Provider |
| `GET` | `/api/providers` | 列出所有 Provider |
| `GET` | `/api/providers/{id}` | 获取单个 Provider |
| `PUT` | `/api/providers/{id}` | 更新 Provider |
| `DELETE` | `/api/providers/{id}` | 删除 Provider |
| `POST` | `/api/providers/{id}/test` | 测试连接 |

#### 角色卡管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/role-cards` | 创建角色卡 |
| `GET` | `/api/role-cards` | 列出角色卡（支持 `?builtin=true` 过滤） |
| `GET` | `/api/role-cards/{id}` | 获取单个角色卡 |
| `PUT` | `/api/role-cards/{id}` | 更新角色卡（内置角色不可修改） |
| `DELETE` | `/api/role-cards/{id}` | 删除角色卡（内置角色不可删除） |
| `POST` | `/api/role-cards/{id}/copy` | 复制角色卡 |

#### 房间管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rooms` | 创建房间 |
| `GET` | `/api/rooms` | 列出所有房间 |
| `GET` | `/api/rooms/{id}` | 获取房间详情 |
| `PUT` | `/api/rooms/{id}` | 更新房间 |
| `DELETE` | `/api/rooms/{id}` | 删除房间（级联删除关联数据） |

#### 数据源管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rooms/{id}/sources` | 添加数据源（file/folder/text） |
| `GET` | `/api/rooms/{id}/sources` | 列出房间数据源 |
| `DELETE` | `/api/sources/{id}` | 删除数据源 |

#### 讨论系统

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/rooms/{id}/start` | 启动讨论（返回 SSE 流） |
| `GET` | `/api/rooms/{id}/messages` | 获取消息列表 |
| `POST` | `/api/rooms/{id}/messages` | 发送用户插话消息 |
| `GET` | `/api/rooms/{id}/messages/stream` | SSE 消息流 |

#### 产物管理

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/rooms/{id}/synthesize` | 生成产物 |
| `GET` | `/api/rooms/{id}/artifacts` | 列出房间产物 |
| `GET` | `/api/artifacts/{id}/content` | 获取产物内容 |

#### 其他

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/health` | 健康检查 |

### SSE 事件类型

讨论过程通过 SSE 流式传输以下事件：

| 事件类型 | 说明 | 数据字段 |
|----------|------|----------|
| `thinking` | 专家正在思考 | `room_id`, `role`, `status` |
| `message` | 新消息 | `id`, `room_id`, `sender_type`, `sender_id`, `content`, `round` |
| `artifact` | 产物生成 | `artifact_id`, `file_path` |
| `error` | 错误 | `room_id`, `error`, `recoverable` |
| `done` | 讨论完成 | `room_id`, `total_rounds`, `total_messages` |

## 安全特性

### API 密钥加密

所有 LLM Provider 的 API 密钥默认使用 Fernet 加密存储：

- 密钥在写入数据库前加密
- 读取时解密，传输到前端时掩码显示（如 `sk-abc12345***`）
- `ENCRYPT_API_KEYS=true` 时启用加密，默认启用
- 加密密钥优先从环境变量 `ENCRYPTION_KEY` 读取（需为有效 Fernet 格式）
- 若 `ENCRYPTION_KEY` 未配置或格式无效，自动从 `.encryption_key` 文件读取
- 若文件也不存在，自动生成新密钥并持久化到 `.encryption_key`

### 文件安全

- 上传文件大小限制：默认 10MB
- 支持的文件扩展名白名单：`.txt`, `.md`, `.json`, `.csv`, `.py`, `.ts`, `.js` 等
- 自动排除目录：`node_modules`, `.git`, `dist`, `build`, `.venv` 等
- 文件夹路径验证：防止目录遍历攻击

### 内置角色保护

- 内置角色卡（主持人、产品经理、系统架构师、文档专家）不可修改或删除
- 可通过复制功能创建自定义版本

## 开发指南

### 后端开发

```bash
cd backend

# 运行测试
pytest

# 数据库迁移
alembic revision --autogenerate -m "描述"
alembic upgrade head

# 代码格式化
ruff format .

# 代码检查
ruff check .
```

### 前端开发

```bash
cd frontend

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 代码检查
npm run lint

# 预览构建结果
npm run preview
```

### 讨论编排流程

讨论系统采用状态机模式管理：

```
INITIALIZED → RUNNING → CONVERGING → COMPLETED
                    ↓
                 FAILED
```

每轮讨论流程：
1. **主持人发言** - 分析当前状态，安排下一位专家
2. **专家轮流发言** - 根据角色卡定义的专业领域给出观点
3. **更新滚动摘要** - 压缩历史消息为摘要
4. **检查收敛条件** - 达到最大轮次或满足收敛条件时结束

### 数据模型

```
Provider (LLM 服务提供商)
  ├── name, type, base_url
  ├── api_key_encrypted (加密存储)
  └── default_model, default_temperature, default_max_tokens

RoleCard (专家角色卡)
  ├── name, description
  ├── expertise[] (专业领域)
  ├── responsibilities[] (职责)
  ├── constraints[] (约束)
  └── system_prompt, output_style

Room (讨论房间)
  ├── name, goal, mode
  ├── status (draft/running/completed/failed)
  ├── round_limit, output_directory
  └── participants[] (关联 RoleCard + Provider)

Message (讨论消息)
  ├── sender_type (orchestrator/expert)
  ├── sender_id (RoleCard ID)
  ├── content, citations
  └── round (轮次)

Artifact (生成产物)
  ├── title, file_path
  ├── file_format (md/txt/csv)
  └── file_size_bytes

SharedSource (共享数据源)
  ├── source_type (file/folder/text)
  ├── path, content
  └── file_size_bytes
```

## 内置角色卡

| 角色 | 说明 | 专业领域 |
|------|------|----------|
|   主持人 | 控制讨论流程，推动收敛 | 流程管理、冲突识别、结论收敛 |
|   产品经理 | 需求分析，优先级排序 | 需求分析、用户场景、MVP 定义 |
|  ️ 系统架构师 | 技术方案设计 | 架构设计、模块拆分、技术选型 |
|   文档专家 | 整理讨论结果 | 技术写作、文档结构、信息整合 |

## 许可证

MIT License

---

**Built with ❤️ by Expert Room Team**
