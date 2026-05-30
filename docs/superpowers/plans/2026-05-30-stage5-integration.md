# Stage 5: Integration Testing + Security Hardening + Tauri Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete MVP with end-to-end testing, security hardening, error handling, Tauri desktop integration, and documentation.

**Architecture:** Backend security hardening (path validation, error middleware, token limits), frontend error boundaries, Tauri sidecar process management for Python backend, and comprehensive documentation.

**Tech Stack:** Python, FastAPI, React, TypeScript, Tauri 2.0, Rust

---

## File Structure

### Backend Files to Create/Modify:
- `backend/app/middleware/error_handler.py` - Global exception handler
- `backend/app/utils/path_validator.py` - Path traversal protection
- `backend/app/services/orchestrator.py` - Add token limit enforcement
- `backend/tests/test_security.py` - Security-focused tests
- `backend/tests/test_e2e.py` - End-to-end flow tests

### Frontend Files to Create/Modify:
- `frontend/src/components/shared/ErrorBoundary.tsx` - Global error boundary
- `frontend/src/components/shared/ErrorMessage.tsx` - User-friendly error display

### Tauri Files to Create:
- `src-tauri/Cargo.toml` - Rust dependencies
- `src-tauri/tauri.conf.json` - Tauri configuration
- `src-tauri/src/main.rs` - Rust entry point
- `src-tauri/src/sidecar.rs` - Python process management
- `src-tauri/icons/` - App icons

### Documentation Files to Create/Modify:
- `docs/stage5-test.md` - Stage 5 verification guide
- `docs/api-contracts.md` - API documentation
- `docs/architecture.md` - Architecture overview
- `README.md` - Enhanced with full documentation

---

## Task 1: Backend - Global Error Handler Middleware

**Files:**
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/middleware/error_handler.py`
- Modify: `backend/app/main.py` (register middleware)
- Test: `backend/tests/test_error_handler.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_error_handler.py
"""Tests for global error handler middleware."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_unhandled_exception_returns_500():
    """Test that unhandled exceptions return standardized error response."""
    from app.middleware.error_handler import ErrorHandlerMiddleware
    
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    
    @app.get("/test-error")
    async def test_error():
        raise ValueError("Test error")
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-error")
    
    assert response.status_code == 500
    data = response.json()
    assert "error" in data
    assert "message" in data
    assert "request_id" in data


def test_http_exception_returns_proper_format():
    """Test that HTTP exceptions use standardized format."""
    from app.middleware.error_handler import ErrorHandlerMiddleware
    from fastapi import HTTPException
    
    app = FastAPI()
    app.add_middleware(ErrorHandlerMiddleware)
    
    @app.get("/test-http-error")
    async def test_http_error():
        raise HTTPException(status_code=404, detail="Not found")
    
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/test-http-error")
    
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"] == "not_found"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_error_handler.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.middleware'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/middleware/__init__.py
"""Middleware package."""

# backend/app/middleware/error_handler.py
"""Global error handler middleware."""

import uuid
from typing import Any

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for standardized error responses."""

    async def dispatch(self, request: Request, call_next: Any) -> Any:
        request_id = str(uuid.uuid4())
        
        try:
            response = await call_next(request)
            return response
        except HTTPException as e:
            logger.warning(
                "HTTP exception",
                status_code=e.status_code,
                detail=e.detail,
                request_id=request_id,
                path=request.url.path,
            )
            return self._create_error_response(
                status_code=e.status_code,
                error=self._get_error_type(e.status_code),
                message=str(e.detail),
                request_id=request_id,
            )
        except Exception as e:
            logger.error(
                "Unhandled exception",
                error_type=type(e).__name__,
                error=str(e),
                request_id=request_id,
                path=request.url.path,
            )
            return self._create_error_response(
                status_code=500,
                error="internal_server_error",
                message="An unexpected error occurred",
                request_id=request_id,
            )

    def _create_error_response(
        self, status_code: int, error: str, message: str, request_id: str
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": error,
                "message": message,
                "request_id": request_id,
            },
        )

    def _get_error_type(self, status_code: int) -> str:
        error_types = {
            400: "bad_request",
            401: "unauthorized",
            403: "forbidden",
            404: "not_found",
            405: "method_not_allowed",
            409: "conflict",
            422: "validation_error",
            429: "rate_limit_exceeded",
            500: "internal_server_error",
            502: "bad_gateway",
            503: "service_unavailable",
        }
        return error_types.get(status_code, "unknown_error")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_error_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/middleware/ backend/tests/test_error_handler.py
git commit -m "feat: add global error handler middleware with standardized responses"
```

---

## Task 2: Backend - Path Traversal Protection

**Files:**
- Create: `backend/app/utils/path_validator.py`
- Modify: `backend/app/routers/sources.py` (add validation)
- Modify: `backend/app/services/file_ingestion.py` (add validation)
- Test: `backend/tests/test_path_validator.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_path_validator.py
"""Tests for path traversal protection."""

import pytest
from app.utils.path_validator import validate_path, PathValidationError


def test_validate_path_rejects_dot_dot():
    """Test that path traversal attempts are rejected."""
    with pytest.raises(PathValidationError, match="traversal"):
        validate_path("/safe/path/../../../etc/passwd", "/safe/path")


def test_validate_path_rejects_absolute_outside_base():
    """Test that paths outside base directory are rejected."""
    with pytest.raises(PathValidationError, match="outside"):
        validate_path("/etc/passwd", "/safe/path")


def test_validate_path_accepts_valid_path():
    """Test that valid paths are accepted."""
    result = validate_path("/safe/path/subdir/file.txt", "/safe/path")
    assert result == "/safe/path/subdir/file.txt"


def test_validate_path_normalizes():
    """Test that paths are normalized."""
    result = validate_path("/safe/path/./subdir/../file.txt", "/safe/path")
    assert result == "/safe/path/file.txt"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_path_validator.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.utils.path_validator'"

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/utils/path_validator.py
"""Path traversal protection utilities."""

import os
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class PathValidationError(Exception):
    """Raised when path validation fails."""
    pass


def validate_path(path: str, base_directory: str) -> str:
    """Validate that a path is within the base directory.
    
    Args:
        path: The path to validate
        base_directory: The allowed base directory
        
    Returns:
        Normalized absolute path
        
    Raises:
        PathValidationError: If path traversal is detected
    """
    # Normalize paths
    base = Path(base_directory).resolve()
    target = Path(path).resolve()
    
    # Check for path traversal
    if ".." in Path(path).parts:
        logger.warning(
            "Path traversal attempt detected",
            path=path,
            base=base_directory,
        )
        raise PathValidationError(
            f"Path traversal detected in: {path}"
        )
    
    # Check if target is within base
    try:
        target.relative_to(base)
    except ValueError:
        logger.warning(
            "Path outside base directory",
            path=path,
            base=base_directory,
        )
        raise PathValidationError(
            f"Path {path} is outside allowed directory {base_directory}"
        )
    
    return str(target)


def validate_file_path(file_path: str, allowed_extensions: set[str]) -> bool:
    """Validate file extension.
    
    Args:
        file_path: The file path to validate
        allowed_extensions: Set of allowed extensions (e.g., {'.txt', '.md'})
        
    Returns:
        True if extension is allowed
        
    Raises:
        PathValidationError: If extension is not allowed
    """
    ext = Path(file_path).suffix.lower()
    if ext not in allowed_extensions:
        raise PathValidationError(
            f"File extension {ext} not allowed. Allowed: {allowed_extensions}"
        )
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_path_validator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/utils/path_validator.py backend/tests/test_path_validator.py
git commit -m "feat: add path traversal protection utilities"
```

---

## Task 3: Backend - Integrate Path Validation into Sources API

**Files:**
- Modify: `backend/app/routers/sources.py` (add path validation)
- Modify: `backend/app/services/file_ingestion.py` (add path validation)
- Test: `backend/tests/test_sources_security.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_sources_security.py
"""Tests for path validation in sources API."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_add_folder_rejects_traversal():
    """Test that folder source rejects path traversal."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/api/rooms/test-room/sources",
            json={
                "source_type": "folder",
                "path": "/safe/path/../../../etc",
            },
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "traversal" in data.get("message", "").lower() or "invalid" in data.get("message", "").lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_sources_security.py -v`
Expected: FAIL or PASS (depends on current implementation)

- [ ] **Step 3: Implement path validation in sources router**

```python
# backend/app/routers/sources.py (add to existing file)
from app.utils.path_validator import validate_path, PathValidationError

# In add_source endpoint, before calling file_ingestion:
if source.source_type == "folder" and source.path:
    try:
        validate_path(source.path, "/")  # Allow any absolute path
    except PathValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_sources_security.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/sources.py backend/tests/test_sources_security.py
git commit -m "feat: add path validation to sources API"
```

---

## Task 4: Backend - Token Limit Enforcement

**Files:**
- Modify: `backend/app/services/orchestrator.py` (add token limits)
- Modify: `backend/app/config.py` (add token limit config)
- Test: `backend/tests/test_token_limits.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_token_limits.py
"""Tests for token limit enforcement."""

import pytest
from app.config import Settings


def test_settings_has_token_limits():
    """Test that settings include token limits."""
    settings = Settings()
    assert hasattr(settings, "max_tokens_per_turn")
    assert hasattr(settings, "max_total_tokens")


def test_settings_token_limits_have_defaults():
    """Test that token limits have sensible defaults."""
    settings = Settings()
    assert settings.max_tokens_per_turn > 0
    assert settings.max_total_tokens > 0
    assert settings.max_tokens_per_turn <= settings.max_total_tokens
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_token_limits.py -v`
Expected: FAIL with "AttributeError"

- [ ] **Step 3: Add token limit configuration**

```python
# backend/app/config.py (add to existing Settings class)
class Settings(BaseSettings):
    # ... existing fields ...
    
    # Token limits
    max_tokens_per_turn: int = Field(
        default=4096,
        description="Maximum tokens per LLM call"
    )
    max_total_tokens: int = Field(
        default=50000,
        description="Maximum total tokens per discussion"
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_token_limits.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/config.py backend/tests/test_token_limits.py
git commit -m "feat: add token limit configuration"
```

---

## Task 5: Backend - End-to-End Flow Test

**Files:**
- Create: `backend/tests/test_e2e.py`

- [ ] **Step 1: Write the E2E test**

```python
# backend/tests/test_e2e.py
"""End-to-end flow tests."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_full_flow_provider_to_artifact():
    """Test complete flow: create provider, role card, room, add source."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Step 1: Create provider
        provider_response = await client.post(
            "/api/providers",
            json={
                "name": "Test Provider",
                "base_url": "https://api.openai.com/v1",
                "api_key": "sk-test-key-123456789",
                "default_model": "gpt-4",
            },
        )
        assert provider_response.status_code == 200
        provider_id = provider_response.json()["id"]
        
        # Step 2: Get role cards
        roles_response = await client.get("/api/role-cards?builtin=true")
        assert roles_response.status_code == 200
        roles = roles_response.json()
        assert len(roles) > 0
        
        # Step 3: Create room
        room_response = await client.post(
            "/api/rooms",
            json={
                "name": "Test Room",
                "goal": "Test goal",
                "mode": "code_document",
                "participant_role_ids": [roles[0]["id"]],
                "output_directory": "/tmp/test-output",
            },
        )
        assert room_response.status_code == 200
        room_id = room_response.json()["id"]
        
        # Step 4: Verify room was created
        get_room_response = await client.get(f"/api/rooms/{room_id}")
        assert get_room_response.status_code == 200
        assert get_room_response.json()["name"] == "Test Room"
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_e2e.py -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_e2e.py
git commit -m "test: add end-to-end flow test"
```

---

## Task 6: Frontend - Error Boundary Component

**Files:**
- Create: `frontend/src/components/shared/ErrorBoundary.tsx`
- Create: `frontend/src/components/shared/ErrorMessage.tsx`
- Modify: `frontend/src/App.tsx` (wrap with ErrorBoundary)

- [ ] **Step 1: Create ErrorBoundary component**

```typescript
// frontend/src/components/shared/ErrorBoundary.tsx
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
          <div className="max-w-md p-8 bg-white rounded-lg shadow-lg">
            <h2 className="text-2xl font-bold text-red-600 mb-4">
              出错了
            </h2>
            <p className="text-gray-600 mb-4">
              应用遇到了一个意外错误。请尝试刷新页面。
            </p>
            {this.state.error && (
              <pre className="p-4 bg-gray-100 rounded text-sm overflow-auto mb-4">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={this.handleReset}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              重试
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

- [ ] **Step 2: Create ErrorMessage component**

```typescript
// frontend/src/components/shared/ErrorMessage.tsx
import React from 'react';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({
  message,
  onRetry,
  onDismiss,
}) => {
  return (
    <div className="bg-red-50 border border-red-200 rounded-lg p-4">
      <div className="flex items-start">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm text-red-800">{message}</p>
          {(onRetry || onDismiss) && (
            <div className="mt-3 flex space-x-3">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="text-sm font-medium text-red-800 hover:text-red-900"
                >
                  重试
                </button>
              )}
              {onDismiss && (
                <button
                  onClick={onDismiss}
                  className="text-sm font-medium text-red-600 hover:text-red-700"
                >
                  关闭
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
```

- [ ] **Step 3: Wrap App with ErrorBoundary**

```typescript
// frontend/src/App.tsx (add import and wrap)
import { ErrorBoundary } from './components/shared/ErrorBoundary';

function App() {
  return (
    <ErrorBoundary>
      {/* existing app content */}
    </ErrorBoundary>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/shared/ frontend/src/App.tsx
git commit -m "feat: add error boundary and error message components"
```

---

## Task 7: Tauri - Project Initialization

**Files:**
- Create: `src-tauri/Cargo.toml`
- Create: `src-tauri/tauri.conf.json`
- Create: `src-tauri/src/main.rs`
- Create: `src-tauri/build.rs`

- [ ] **Step 1: Create Tauri configuration**

```json
// src-tauri/tauri.conf.json
{
  "build": {
    "beforeDevCommand": "npm run dev",
    "beforeBuildCommand": "npm run build",
    "devUrl": "http://localhost:5173",
    "frontendDist": "../frontend/dist"
  },
  "package": {
    "productName": "Expert Room",
    "version": "0.1.0"
  },
  "tauri": {
    "allowlist": {
      "all": false,
      "shell": {
        "sidecar": true,
        "scope": [
          {
            "name": "python-backend",
            "cmd": "python",
            "args": ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            "cwd": "backend"
          }
        ]
      },
      "dialog": {
        "all": true
      },
      "fs": {
        "scope": ["**"]
      }
    },
    "bundle": {
      "active": true,
      "targets": "all",
      "identifier": "com.expert-room.app",
      "icon": [
        "icons/32x32.png",
        "icons/128x128.png",
        "icons/128x128@2x.png",
        "icons/icon.icns",
        "icons/icon.ico"
      ]
    },
    "security": {
      "csp": null
    },
    "windows": [
      {
        "fullscreen": false,
        "resizable": true,
        "title": "专家团 - AI Expert Team",
        "width": 1200,
        "height": 800
      }
    ]
  }
}
```

- [ ] **Step 2: Create Cargo.toml**

```toml
# src-tauri/Cargo.toml
[package]
name = "expert-room"
version = "0.1.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "1.5", features = [] }

[dependencies]
tauri = { version = "1.6", features = ["shell-sidecar", "dialog-all", "fs-all"] }
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
```

- [ ] **Step 3: Create main.rs**

```rust
// src-tauri/src/main.rs
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            // Start Python backend sidecar
            let sidecar = app.shell().sidecar("python-backend").unwrap();
            let (mut _rx, _child) = sidecar.spawn().expect("Failed to spawn Python backend");
            
            // Store child process for cleanup
            app.manage(_child);
            
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

- [ ] **Step 4: Create build.rs**

```rust
// src-tauri/build.rs
fn main() {
    tauri_build::build()
}
```

- [ ] **Step 5: Commit**

```bash
git add src-tauri/
git commit -m "feat: initialize Tauri project with sidecar configuration"
```

---

## Task 8: Documentation - Stage 5 Test Guide

**Files:**
- Create: `docs/stage5-test.md`

- [ ] **Step 1: Create verification guide**

```markdown
# Stage 5 Verification Guide

## 1. Security Verification

### API Key Encryption
- [ ] API keys are encrypted in database (check `api_key_encrypted` column)
- [ ] API keys are masked in logs (no raw keys in log output)
- [ ] API keys are not exposed in API responses (only `api_key_masked`)

### Path Traversal Protection
- [ ] Folder paths with `..` are rejected
- [ ] Paths outside allowed directories are rejected
- [ ] Valid paths are accepted

### Error Handling
- [ ] Unhandled exceptions return standardized error format
- [ ] Error responses include `request_id` for tracing
- [ ] User-friendly error messages are displayed

## 2. Integration Testing

### End-to-End Flow
- [ ] Create provider with API key
- [ ] Create room with participants
- [ ] Add shared sources (files/folders)
- [ ] Start discussion (requires valid API key)
- [ ] Generate artifacts
- [ ] View artifact content

### Error Scenarios
- [ ] Invalid API key shows error
- [ ] Network timeout shows error
- [ ] Invalid file paths are rejected

## 3. Tauri Desktop Integration

### Build
- [ ] `npm run tauri dev` starts successfully
- [ ] `npm run tauri build` produces executable
- [ ] Python backend starts as sidecar

### Functionality
- [ ] App window opens
- [ ] All pages load correctly
- [ ] API calls work through sidecar

## 4. Token Limits

### Configuration
- [ ] `max_tokens_per_turn` is enforced
- [ ] `max_total_tokens` is enforced
- [ ] Token usage is logged

## 5. Documentation

### Completeness
- [ ] README has complete setup instructions
- [ ] API documentation is available
- [ ] Architecture diagram exists
```

- [ ] **Step 2: Commit**

```bash
git add docs/stage5-test.md
git commit -m "docs: add stage 5 verification guide"
```

---

## Task 9: Documentation - Enhanced README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README with comprehensive documentation**

```markdown
#   专家团 - AI Expert Team Collaboration Workbench

本地优先的 AI 多专家协作讨论工作台。用户配置 LLM API Key，创建专家角色卡，组建群聊房间，多专家协作讨论并生成结构化文档。

## ✨ 功能特性

-   **Provider 管理** - 配置多个 LLM 服务商（OpenAI、Claude、本地模型等）
-   **角色卡系统** - 创建和管理专家角色卡，内置 4 个专业角色
-   **群聊协作** - 创建讨论房间，选择专家组合，设定讨论目标
-   **文件共享** - 上传文件或指定文件夹作为讨论资料
-   **智能讨论** - 多专家按标准模式进行结构化讨论
-   **产出生成** - 自动生成结构化 Markdown 技术方案文档

##   技术栈

| 层级 | 技术 |
|------|------|
| 桌面壳 | Tauri 2.0 |
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / SQLite |
| 前端 | React 18 / TypeScript / Vite / Tailwind CSS / Zustand |
| 实时通信 | SSE (Server-Sent Events) |
| LLM 集成 | OpenAI-compatible API |

##   快速开始

### 前置要求

- Python 3.11+
- Node.js 18+
- Rust (for Tauri)

### 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置 ENCRYPTION_KEY

# 初始化数据库
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 桌面应用 (Tauri)

```bash
# 安装 Tauri CLI
npm install -g @tauri-apps/cli

# 开发模式
npm run tauri dev

# 构建生产版本
npm run tauri build
```

##   项目结构

```
project/
├── backend/                # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py        # 应用入口
│   │   ├── config.py      # 配置管理
│   │   ├── models/        # 数据库模型
│   │   ├── routers/       # API 路由
│   │   ├── services/      # 业务逻辑
│   │   └── utils/         # 工具函数
│   ├── tests/             # 测试文件
│   └── alembic/           # 数据库迁移
├── frontend/               # React 前端
│   ├── src/
│   │   ├── api/           # API 客户端
│   │   ├── components/    # React 组件
│   │   ├── pages/         # 页面组件
│   │   ├── stores/        # Zustand 状态管理
│   │   └── types/         # TypeScript 类型
│   └── package.json
├── src-tauri/              # Tauri 桌面应用
│   ├── src/               # Rust 源码
│   └── tauri.conf.json    # Tauri 配置
├── docs/                   # 项目文档
└── project/plan/           # 执行计划
```

##   API 文档

启动后端后访问 http://localhost:8000/docs 查看 Swagger UI 文档。

### 主要 API 端点

| 模块 | 端点 | 说明 |
|------|------|------|
| Provider | `POST /api/providers` | 创建服务商配置 |
| Provider | `POST /api/providers/{id}/test` | 测试连接 |
| Role Card | `GET /api/role-cards` | 获取角色卡列表 |
| Room | `POST /api/rooms` | 创建讨论房间 |
| Discussion | `POST /api/rooms/{id}/start` | 启动讨论 (SSE) |
| Artifact | `POST /api/rooms/{id}/synthesize` | 生成产出文档 |

##   安全特性

- **API Key 加密** - 使用 AES-256 加密存储 API Key
- **日志脱敏** - 自动屏蔽敏感信息（API Key、Token 等）
- **路径校验** - 防止路径遍历攻击
- **错误处理** - 统一错误响应格式，包含请求 ID

##  ️ 开发

### 运行测试

```bash
# 后端测试
cd backend
python -m pytest tests/ -v

# 前端类型检查
cd frontend
npm run type-check
```

### 代码规范

- **后端**: Ruff (lint) + mypy (type check)
- **前端**: ESLint + TypeScript strict mode

##   文档

- [执行计划](project/plan/execution-plan.md) - 详细的开发计划
- [API 契约](docs/api-contracts.md) - API 接口文档
- [架构设计](docs/architecture.md) - 系统架构说明

##   许可证

MIT License
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: enhance README with comprehensive documentation"
```

---

## Task 10: Documentation - API Contracts

**Files:**
- Create: `docs/api-contracts.md`

- [ ] **Step 1: Create API documentation**

```markdown
# API Contracts

## Base URL

```
http://localhost:8000/api
```

## Authentication

目前 API 无需认证（本地优先设计）。

## Error Response Format

所有错误响应遵循统一格式：

```json
{
  "error": "error_type",
  "message": "Human-readable error message",
  "request_id": "uuid-for-tracing"
}
```

### Error Types

| Type | HTTP Status | Description |
|------|-------------|-------------|
| `bad_request` | 400 | 请求参数错误 |
| `not_found` | 404 | 资源不存在 |
| `validation_error` | 422 | 数据验证失败 |
| `internal_server_error` | 500 | 服务器内部错误 |

---

## Provider API

### Create Provider

```http
POST /api/providers
Content-Type: application/json

{
  "name": "OpenAI",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "default_model": "gpt-4",
  "default_temperature": 0.7,
  "default_max_tokens": 4096
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "name": "OpenAI",
  "base_url": "https://api.openai.com/v1",
  "api_key_masked": "sk-abc123***",
  "default_model": "gpt-4",
  "default_temperature": 0.7,
  "default_max_tokens": 4096,
  "enabled": true,
  "created_at": "2026-05-30T10:00:00Z",
  "updated_at": "2026-05-30T10:00:00Z"
}
```

### Test Provider Connection

```http
POST /api/providers/{id}/test
```

**Response (200):**
```json
{
  "success": true,
  "message": "Connection successful",
  "model": "gpt-4",
  "latency_ms": 150
}
```

---

## Role Card API

### List Role Cards

```http
GET /api/role-cards?builtin=true
```

**Response (200):**
```json
[
  {
    "id": "role_orchestrator",
    "name": "主持人",
    "description": "控制讨论流程，推动专家发言和结论收敛",
    "expertise": ["流程管理", "冲突识别", "结论收敛"],
    "responsibilities": ["安排专家发言顺序", "识别讨论中的冲突和遗漏"],
    "is_builtin": true,
    "created_at": "2026-05-30T10:00:00Z",
    "updated_at": "2026-05-30T10:00:00Z"
  }
]
```

---

## Room API

### Create Room

```http
POST /api/rooms
Content-Type: application/json

{
  "name": "登录模块设计",
  "goal": "设计一个安全的用户登录模块",
  "mode": "code_document",
  "strategy": "standard",
  "output_directory": "/path/to/output",
  "round_limit": 5,
  "participant_role_ids": ["role_orchestrator", "role_pm", "role_architect"]
}
```

**Response (200):**
```json
{
  "id": "uuid",
  "name": "登录模块设计",
  "goal": "设计一个安全的用户登录模块",
  "mode": "code_document",
  "strategy": "standard",
  "output_directory": "/path/to/output",
  "round_limit": 5,
  "status": "draft",
  "created_at": "2026-05-30T10:00:00Z",
  "updated_at": "2026-05-30T10:00:00Z"
}
```

---

## Discussion API

### Start Discussion

```http
POST /api/rooms/{id}/start
```

**Response:** SSE Stream

```
event: thinking
data: {"room_id":"uuid","role":"主持人","status":"思考中"}

event: message
data: {"id":"uuid","room_id":"uuid","sender_type":"orchestrator","content":"...","round":1}

event: done
data: {"room_id":"uuid","total_rounds":3,"total_messages":12}
```

---

## Artifact API

### Synthesize Artifacts

```http
POST /api/rooms/{id}/synthesize
Content-Type: application/json

{
  "output_directory": "/path/to/output"  // optional
}
```

**Response (200):**
```json
{
  "success": true,
  "artifacts": [
    {
      "id": "uuid",
      "room_id": "uuid",
      "artifact_type": "markdown",
      "title": "技术方案 - 登录模块设计",
      "file_path": "/path/to/output/final-plan.md",
      "summary": "基于讨论生成的技术方案文档",
      "created_at": "2026-05-30T10:00:00Z"
    }
  ],
  "message": "成功生成 2 个产出文件"
}
```

### Get Artifact Content

```http
GET /api/artifacts/{id}/content
```

**Response (200):**
```json
{
  "id": "uuid",
  "content": "# 技术方案\n\n## 1. 背景与目标\n...",
  "file_path": "/path/to/output/final-plan.md"
}
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/api-contracts.md
git commit -m "docs: add comprehensive API documentation"
```

---

## Task 11: Documentation - Architecture Overview

**Files:**
- Create: `docs/architecture.md`

- [ ] **Step 1: Create architecture documentation**

```markdown
# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Tauri Desktop Shell                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                 React Frontend                       │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │  Pages  │  │Components│  │  Stores │            │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘            │   │
│  │       └────────────┼────────────┘                   │   │
│  │                    │                                │   │
│  │              ┌─────┴─────┐                          │   │
│  │              │ API Client│                          │   │
│  │              └─────┬─────┘                          │   │
│  └────────────────────┼────────────────────────────────┘   │
│                       │ HTTP/SSE                            │
│  ┌────────────────────┼────────────────────────────────┐   │
│  │              Python Backend (Sidecar)                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │ Routers │  │Services │  │ Models  │            │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘            │   │
│  │       └────────────┼────────────┘                   │   │
│  │                    │                                │   │
│  │              ┌─────┴─────┐                          │   │
│  │              │  SQLite   │                          │   │
│  │              └───────────┘                          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
                    ┌─────────────────┐
                    │   LLM Provider  │
                    │  (OpenAI, etc)  │
                    └─────────────────┘
```

## Component Details

### Frontend (React)

| Component | Responsibility |
|-----------|----------------|
| **Pages** | Route-level components (Settings, RoleCards, Rooms, Discussion, Artifacts) |
| **Components** | Reusable UI components (forms, lists, previews) |
| **Stores** | Zustand state management (global app state, artifact state) |
| **Hooks** | Custom hooks (useDiscussionSSE for real-time updates) |
| **API Client** | HTTP client with error handling |

### Backend (FastAPI)

| Layer | Responsibility |
|-------|----------------|
| **Routers** | HTTP endpoint definitions, request validation |
| **Services** | Business logic, orchestration |
| **Models** | SQLAlchemy ORM models |
| **Schemas** | Pydantic request/response schemas |
| **Utils** | Shared utilities (logging, crypto, file handling) |

### Data Flow

```
User Action
    │
    ▼
React Component
    │
    ▼
API Client (fetch)
    │
    ▼
FastAPI Router
    │
    ▼
Service Layer
    │
    ├──▶ Database (SQLAlchemy)
    │
    └──▶ LLM API (httpx)
         │
         ▼
    SSE Stream ──▶ React Hook ──▶ UI Update
```

## Security Architecture

### API Key Management

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │     │   Backend   │     │  Database   │
│             │     │             │     │             │
│  api_key ───┼────▶│  encrypt() ─┼────▶│ encrypted   │
│  (input)    │     │  (Fernet)   │     │ _key        │
└─────────────┘     └─────────────┘     └─────────────┘
                          │
                          ▼
                    ┌─────────────┐
                    │  Log Output │
                    │  (masked)   │
                    └─────────────┘
```

### Error Handling

```
Exception
    │
    ▼
Error Handler Middleware
    │
    ├──▶ Log Error (structlog)
    │
    └──▶ Standardized Response
         │
         ▼
    ┌─────────────────┐
    │ {               │
    │   "error": "...",│
    │   "message": "...",│
    │   "request_id": "..."│
    │ }               │
    └─────────────────┘
```

## Deployment Architecture

### Desktop (Tauri)

```
┌─────────────────────────────────────┐
│         Tauri Application           │
│  ┌─────────────────────────────┐   │
│  │      WebView (Frontend)     │   │
│  └─────────────────────────────┘   │
│  ┌─────────────────────────────┐   │
│  │   Python Sidecar Process    │   │
│  │   (FastAPI + SQLite)        │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Development

```
Terminal 1: cd backend && uvicorn app.main:app --reload
Terminal 2: cd frontend && npm run dev
Browser: http://localhost:5173
```

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database | SQLite | Local-first, zero config, single file |
| State Management | Zustand | Lightweight, TypeScript-first, no boilerplate |
| Real-time | SSE | Simple, works with HTTP/2, no WebSocket complexity |
| Desktop | Tauri | Lightweight (vs Electron), Rust backend, native feel |
| Encryption | Fernet | Simple API, good security, Python standard library |
```

- [ ] **Step 2: Commit**

```bash
git add docs/architecture.md
git commit -m "docs: add architecture overview with diagrams"
```

---

## Task 12: Final Verification and Tag

**Files:**
- None (verification only)

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds

- [ ] **Step 3: Verify git status**

Run: `git status`
Expected: Clean working tree

- [ ] **Step 4: Create MVP tag**

```bash
git tag -a v0.1.0-mvp -m "MVP 初版完成

功能：
- Provider 管理与连接测试
- 角色卡 CRUD + 4 个内置角色
- 群聊创建与文件处理
- 多专家讨论引擎
- 产出生成与预览
- Tauri 桌面应用集成

安全：
- API Key AES 加密存储
- 日志脱敏
- 路径遍历防护
- 统一错误处理

文档：
- 完整 README
- API 文档
- 架构设计文档"

git push origin v0.1.0-mvp
```

---

## Verification Checklist

### Security
- [ ] API keys encrypted in database
- [ ] API keys masked in logs
- [ ] API keys not exposed in responses
- [ ] Path traversal protection active
- [ ] Error responses standardized

### Functionality
- [ ] Provider CRUD + test connection
- [ ] Role card CRUD + builtin roles
- [ ] Room creation + participant management
- [ ] File upload + folder scanning
- [ ] Discussion engine (SSE)
- [ ] Artifact generation

### Documentation
- [ ] README complete
- [ ] API documentation
- [ ] Architecture documentation
- [ ] Stage 5 test guide

### Desktop (Tauri)
- [ ] Tauri project initialized
- [ ] Sidecar configuration
- [ ] Build configuration
