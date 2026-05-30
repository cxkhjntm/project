# Stage 0 Verification Guide

## Overview

Stage 0 establishes the project scaffold with Python FastAPI backend, React frontend, database migrations, and basic configuration.

**Status:** ✅ Complete

---

## Backend Verification

### 1. Start Backend Server
```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Test Health Endpoint
```bash
curl http://localhost:8000/api/health
```
**Expected:** `{"status":"ok","version":"0.1.0"}`

### 3. Verify Database
```bash
cd backend
sqlite3 expert_room.db ".tables"
```
**Expected:** 7 tables (providers, role_cards, rooms, room_participants, messages, shared_sources, artifacts)

### 4. Verify Alembic Migrations
```bash
cd backend
alembic current
```
**Expected:** Shows current migration version

### 5. Check Logs
Start server and verify structured log output with no sensitive data exposure.

---

## Frontend Verification

### 1. Start Frontend Server
```bash
cd frontend
npm install
npm run dev
```

### 2. Open Browser
Visit http://localhost:5173

### 3. Verify Features
- [ ] Page loads with "专家团" heading
- [ ] Navigation links work (首页, 设置, 角色卡, 群聊)
- [ ] Backend connection status shows "✅ 后端连接成功"
- [ ] No CORS errors in browser console

---

## Integration Verification

### 1. Start Both Services
Terminal 1: `cd backend && uvicorn app.main:app --reload`
Terminal 2: `cd frontend && npm run dev`

### 2. Test API Proxy
```bash
curl http://localhost:5173/api/health
```
**Expected:** `{"status":"ok","version":"0.1.0"}`

### 3. Verify CORS
- No CORS errors in browser console
- API calls succeed through frontend proxy

---

## Git Verification

### 1. Check Commit History
```bash
git log --oneline
```
**Expected:** Multiple commits for each task

### 2. Verify Clean State
```bash
git status
```
**Expected:** Clean working directory

---

## Troubleshooting

### Backend won't start
- Check Python version (3.12+ required)
- Verify virtual environment is activated
- Check port 8000 is not in use

### Frontend won't start
- Check Node.js version (18+ required)
- Run `npm install` to ensure dependencies are installed
- Check port 5173 is not in use

### CORS errors
- Ensure backend is running on port 8000
- Check Vite proxy configuration in vite.config.ts
- Verify CORS_ORIGINS in backend .env file

### Database errors
- Run `alembic upgrade head` to apply migrations
- Check expert_room.db file exists in backend directory

---

## Stage 0 Deliverables

### Backend
- ✅ FastAPI application with health check endpoint
- ✅ SQLAlchemy + Alembic + SQLite database setup
- ✅ 7 database tables with proper relationships
- ✅ Structured logging with sensitive data masking
- ✅ Environment configuration with pydantic-settings

### Frontend
- ✅ React + TypeScript + Vite project
- ✅ Tailwind CSS configuration
- ✅ React Router with navigation
- ✅ Zustand state management
- ✅ API client for backend communication
- ✅ Health check display on home page

### Integration
- ✅ Frontend can communicate with backend through Vite proxy
- ✅ No CORS issues
- ✅ Health endpoint accessible from frontend

---

## Next Steps

Stage 0 is complete. Proceed to **Stage 1: Provider Management + Role Card Management**.

Refer to `project/plan/execution-plan.md` for Stage 1 requirements.
