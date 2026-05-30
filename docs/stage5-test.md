# Stage 5 Verification Guide

## Overview

Stage 5 completes the MVP with integration testing, security hardening, and Tauri desktop packaging. This is the final verification before tagging v0.1.0-mvp.

**Status:** Pending

---

## 1. Security Verification

### 1.1 API Key Encryption

Verify that API keys are encrypted at rest and never exposed in plaintext.

```bash
# Check database directly - api_key_encrypted should be ciphertext, not plaintext
sqlite3 backend/expert_room.db "SELECT api_key_encrypted FROM providers LIMIT 1;"
```

**Expected:** Output looks like `gAAAAAB...` (Fernet ciphertext), NOT `sk-...` or any plaintext key.

```bash
# Verify API response does NOT include raw key
curl http://localhost:8000/api/providers
```

**Expected:** Response shows `api_key_encrypted` field is absent or masked. No `api_key` field with plaintext.

```bash
# Verify logs do not contain API keys
grep -r "sk-" backend/server.log backend/server_error.log 2>/dev/null
```

**Expected:** No matches. Zero tolerance for key leaks in logs.

- [ ] API keys stored as Fernet ciphertext in database
- [ ] Provider list API returns masked or omitted key field
- [ ] Provider detail API returns masked or omitted key field
- [ ] structlog output never includes raw API keys
- [ ] Error messages never include raw API keys

### 1.2 Path Traversal Prevention

Verify that file operations reject directory traversal attempts.

```bash
# Attempt path traversal in folder source
curl -X POST http://localhost:8000/api/rooms/{id}/sources \
  -H "Content-Type: application/json" \
  -d '{"source_type":"folder","path":"../../etc"}'
```

**Expected:** HTTP 400 or 422 with error message about invalid path.

```bash
# Attempt path traversal in output directory
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{"name":"test","goal":"test","output_directory":"../../../tmp/evil"}'
```

**Expected:** HTTP 400 or 422 rejecting the path.

```bash
# Attempt to read file outside allowed scope
curl "http://localhost:8000/api/artifacts/{id}/content?path=../../etc/passwd"
```

**Expected:** HTTP 403 or 400, file not served.

- [ ] Folder source rejects `..` in path
- [ ] Output directory rejects `..` in path
- [ ] Artifact content endpoint rejects traversal paths
- [ ] Error messages explain the rejection without leaking system info

### 1.3 Error Handling

Verify unified error response format across all endpoints.

```bash
# Test 404
curl http://localhost:8000/api/providers/nonexistent-id
# Test 400 (bad JSON)
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{invalid json}'
# Test 422 (validation failure)
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{"name":""}'
```

**Expected:** All errors return consistent JSON format:
```json
{
  "detail": "Human-readable error message"
}
```

- [ ] 404 returns JSON error, not HTML stack trace
- [ ] 400 returns JSON error for malformed requests
- [ ] 422 returns JSON error with field-level details
- [ ] 500 errors are caught and return generic message (no stack traces)
- [ ] Frontend displays error messages to user (not silent failures)

---

## 2. Integration Testing

### 2.1 End-to-End Flow

Run the complete user journey from provider setup to artifact output.

**Step 1: Configure Provider**
```bash
curl -X POST http://localhost:8000/api/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Provider",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your-test-key",
    "default_model": "gpt-4o-mini"
  }'
# Save the returned ID as PROVIDER_ID

# Test connectivity
curl -X POST http://localhost:8000/api/providers/{PROVIDER_ID}/test
```

- [ ] Provider created successfully
- [ ] Connection test returns success or clear error

**Step 2: Verify Role Cards**
```bash
curl http://localhost:8000/api/role-cards?builtin=true
```

- [ ] Returns 4 built-in roles: 主持人, 产品经理, 系统架构师, 文档专家
- [ ] Each role has system_prompt, expertise, responsibilities

**Step 3: Create Room**
```bash
curl -X POST http://localhost:8000/api/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "name": "E2E Test Room",
    "goal": "设计一个用户认证模块",
    "mode": "code_document",
    "output_directory": "/tmp/e2e-test-output",
    "round_limit": 3,
    "participants": [
      {"role_card_id": "role_orchestrator", "provider_id": "PROVIDER_ID"},
      {"role_card_id": "role_pm", "provider_id": "PROVIDER_ID"},
      {"role_card_id": "role_architect", "provider_id": "PROVIDER_ID"},
      {"role_card_id": "role_doc", "provider_id": "PROVIDER_ID"}
    ]
  }'
# Save ROOM_ID
```

- [ ] Room created with status "draft"
- [ ] Participants linked correctly

**Step 4: Add Shared Source**
```bash
curl -X POST http://localhost:8000/api/rooms/{ROOM_ID}/sources \
  -H "Content-Type: application/json" \
  -d '{"source_type":"text","content":"# 项目说明\n这是一个Web应用项目。"}'
```

- [ ] Source added to room
- [ ] Source listed in room sources

**Step 5: Start Discussion**
```bash
curl -N http://localhost:8000/api/rooms/{ROOM_ID}/start
```

Observe SSE stream output:
- [ ] `thinking` events appear before each expert speaks
- [ ] `message` events contain expert responses
- [ ] Round counter increments (1, 2, 3)
- [ ] Orchestrator manages flow between experts
- [ ] Discussion completes with `done` event after round limit or convergence
- [ ] No `error` events during normal flow

**Step 6: Verify Messages Persisted**
```bash
curl http://localhost:8000/api/rooms/{ROOM_ID}/messages
```

- [ ] All messages from discussion are stored
- [ ] Each message has correct round number
- [ ] sender_type and sender_id are correct

**Step 7: Generate Artifact**
```bash
curl -X POST http://localhost:8000/api/rooms/{ROOM_ID}/synthesize
```

- [ ] Synthesize endpoint returns success
- [ ] Artifact record created in database

**Step 8: Check Output Files**
```bash
ls /tmp/e2e-test-output/
curl http://localhost:8000/api/rooms/{ROOM_ID}/artifacts
curl http://localhost:8000/api/artifacts/{ARTIFACT_ID}/content
```

- [ ] Output directory contains `final-plan.md`
- [ ] Output directory contains `discussion-log.md`
- [ ] `final-plan.md` has structured sections (背景, 需求, 方案, etc.)
- [ ] `discussion-log.md` contains formatted discussion history
- [ ] Content endpoint returns file content correctly

### 2.2 Error Recovery

```bash
# Test with invalid provider (bad API key)
# Create room with invalid provider, start discussion
# Expected: error SSE event, not a crash
```

- [ ] Invalid API key produces `error` SSE event
- [ ] Server does not crash on LLM API failure
- [ ] Partial discussion messages are preserved
- [ ] Frontend shows error state to user

---

## 3. Tauri Desktop Integration

### 3.1 Build Verification

```bash
# Build frontend
cd frontend
npm run build
```

- [ ] Build completes without errors
- [ ] Build output in `frontend/dist/`

```bash
# Build Tauri app
cd src-tauri
cargo build --release
```

- [ ] Tauri build completes without errors
- [ ] Executable created in `src-tauri/target/release/`

### 3.2 Python Sidecar

- [ ] Tauri app launches Python backend process on startup
- [ ] Backend health check passes after launch
- [ ] Tauri app stops Python process on exit
- [ ] No orphan Python processes after app close

### 3.3 Desktop Functionality

Launch the built Tauri application and verify:

- [ ] App window opens with correct title and icon
- [ ] All 4 pages accessible: 设置, 角色卡, 群聊创建, 讨论工作台
- [ ] Provider form works (create, edit, test connection)
- [ ] Role cards display with 4 built-in roles
- [ ] Room creation form works
- [ ] File upload dialog opens (Tauri native dialog)
- [ ] Discussion page loads and connects to SSE
- [ ] Artifacts display after discussion completes

### 3.4 Cross-Platform Notes

If building on Windows:
```bash
# Verify Windows build
cd src-tauri
cargo build --release --target x86_64-pc-windows-msvc
```

- [ ] Windows build succeeds
- [ ] App launches and functions on Windows

---

## 4. Token Limits

### 4.1 Configuration

Verify token limits are enforced at the configuration level.

```bash
# Check backend config for token limits
curl http://localhost:8000/api/config
```

- [ ] Response includes max_tokens_per_turn setting
- [ ] Response includes max_rounds setting
- [ ] Values are reasonable (e.g., 4096 tokens/turn, 5 rounds max)

### 4.2 Enforcement

- [ ] Each expert response is truncated if it exceeds max_tokens_per_turn
- [ ] Discussion stops after max_rounds even if orchestrator wants to continue
- [ ] Token usage is logged (structlog) per turn
- [ ] No single API call sends more than configured max_tokens

### 4.3 Frontend Display

- [ ] Round progress bar reflects round_limit
- [ ] UI shows "round X of Y" indicator
- [ ] Warning displayed if approaching round limit

---

## 5. Documentation

### 5.1 README

- [ ] `README.md` exists in project root
- [ ] Includes project description and purpose
- [ ] Lists prerequisites (Python 3.12+, Node.js 18+, Rust for Tauri)
- [ ] Has quick start instructions for development
- [ ] Has build instructions for Tauri desktop app

### 5.2 API Documentation

- [ ] Swagger UI accessible at http://localhost:8000/docs
- [ ] ReDoc accessible at http://localhost:8000/redoc
- [ ] All endpoints documented with request/response schemas
- [ ] Example requests provided for key endpoints

### 5.3 User Guide

- [ ] Usage guide covers: provider setup, role card creation, room creation, starting discussion, viewing artifacts
- [ ] Screenshots or descriptions of each page
- [ ] Troubleshooting section for common issues

---

## 6. Checklist Summary

### Security
- [ ] API keys encrypted at rest (Fernet)
- [ ] API keys never in logs
- [ ] API keys never in API responses
- [ ] Path traversal rejected
- [ ] Unified error format (no stack traces)

### Integration
- [ ] Full E2E flow: provider → role card → room → source → discussion → artifact
- [ ] SSE stream delivers all 5 event types correctly
- [ ] Messages persisted to database
- [ ] Artifacts written to output directory
- [ ] Error recovery works (bad API key → error event, not crash)

### Desktop
- [ ] Tauri build succeeds
- [ ] Python sidecar starts and stops correctly
- [ ] All pages functional in desktop app
- [ ] Native file dialogs work

### Token Limits
- [ ] Max tokens per turn enforced
- [ ] Max rounds enforced
- [ ] Usage logged

### Documentation
- [ ] README complete
- [ ] API docs accessible
- [ ] User guide exists

---

## Troubleshooting

### SSE connection drops
- Check backend is running and healthy
- Verify no proxy timeout settings
- Check browser console for reconnect attempts

### Artifact generation fails
- Verify output directory exists and is writable
- Check discussion completed (has `done` event)
- Review backend logs for synthesis errors

### Tauri build fails
- Ensure Rust toolchain installed (`rustup`)
- Check Node.js version (18+)
- Verify frontend builds independently first (`npm run build`)
- Check `src-tauri/Cargo.toml` dependencies

### Python sidecar won't start
- Verify Python 3.12+ installed and in PATH
- Check `backend/requirements.txt` installed
- Look for port 8000 conflicts
- Review Tauri sidecar configuration

---

## Stage 5 Deliverables

### Security
- API Key encryption verified (Fernet/AES)
- Path traversal prevention verified
- Structured error handling across all endpoints

### Integration
- End-to-end flow validated
- SSE event protocol working (thinking, message, artifact, error, done)
- Message persistence confirmed
- Artifact generation and output confirmed

### Desktop
- Tauri application builds and runs
- Python sidecar lifecycle managed correctly
- All UI pages functional in desktop context

### Token Management
- Per-turn token limits enforced
- Round limits enforced
- Usage logging in place

### Documentation
- README with setup and usage instructions
- API documentation (Swagger/ReDoc)
- Test verification guides for all stages

---

## Next Steps

Stage 5 is the final stage. After all checks pass:

```bash
git tag -a v0.1.0-mvp -m "MVP 初版完成"
git push origin v0.1.0-mvp
```

Refer to `project/plan/execution-plan.md` for the full development plan.
