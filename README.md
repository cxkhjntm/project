#   专家团 - AI Expert Team Collaboration Workbench

本地优先的 AI 多专家协作讨论工作台。

## 技术栈

- **后端**: Python 3.11+ / FastAPI / SQLAlchemy / SQLite
- **前端**: React 18 / TypeScript / Vite / Tailwind CSS / Zustand
- **桌面**: Tauri 2.0

## 快速开始

### 后端

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 项目结构

```
project/
├── backend/          # Python FastAPI 后端
├── frontend/         # React 前端
├── docs/             # 项目文档
└── project/plan/     # 执行计划
```
