# Expert Room Architecture

Technical architecture overview for the Expert Room (专家团) application, an AI-powered multi-expert collaboration workbench.

---

## System Architecture

Expert Room uses a three-layer desktop architecture: Tauri shell wrapping a React frontend and a FastAPI backend running as a sidecar process. The backend manages all business logic, database access, and LLM communication. The frontend handles UI rendering and real-time event consumption via SSE.

```
+-------------------------------------------------------------+
|                     Tauri Shell (Rust)                       |
|                                                             |
|  +---------------------+    +----------------------------+  |
|  |   Frontend (React)  |    |   Backend (FastAPI)        |  |
|  |                     |    |                            |  |
|  |  React 18 + TS      |    |  Python 3.11+             |  |
|  |  Zustand stores     |    |  SQLAlchemy async         |  |
|  |  Tailwind CSS       |    |  Pydantic schemas        |  |
|  |  React Hook Form    |    |  httpx (LLM calls)       |  |
|  |                     |    |                            |  |
|  |  Port: 5173 (dev)   |    |  Port: 8000               |  |
|  +----------+----------+    +-------------+--------------+  |
|             |                             |                 |
|             |      HTTP / SSE             |                 |
|             +-----------------------------+                 |
|                                                             |
|  +-------------------------------------------------------+  |
|  |              SQLite Database (expert_room.db)         |  |
|  |  providers | role_cards | rooms | room_participants   |  |
|  |  messages  | shared_sources | artifacts               |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  +-------------------------------------------------------+  |
|  |           External LLM APIs (OpenAI-compatible)       |  |
|  |     OpenAI / DeepSeek / Moonshot / Custom endpoints   |  |
|  +-------------------------------------------------------+  |
+-------------------------------------------------------------+
```

The Tauri process manages the application lifecycle: it starts the backend sidecar on launch, monitors its health, and kills it on window close. The frontend runs inside a WebView and communicates with the backend over localhost HTTP.

---

## Component Details

### Tauri Shell

The desktop shell is built with Tauri 1.6 (Rust). It handles:

- Starting the Python backend as a sidecar process via `tauri::api::process::Command`
- Exposing `check_backend_health` and `get_app_version` commands to the frontend
- Managing window lifecycle (close kills the backend process)
- File system access scoped to user directories (`$APPDATA`, `$DOCUMENT`, `$DOWNLOAD`, `$DESKTOP`)
- Dialog APIs for folder selection

Configuration lives in `src-tauri/tauri.conf.json`. The backend binary is bundled as an external resource.

### Frontend

Single-page React application built with Vite 5.4.

**Stack:**
- React 18.3 with TypeScript 5.6
- React Router 6.26 for client-side routing
- Zustand 5.0 for local state (artifact store)
- React Hook Form 7.53 + Zod 3.23 for form validation
- Tailwind CSS 3.4 for styling
- react-markdown + remark-gfm for Markdown rendering

**Pages:**

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | `HomePage` | Landing / overview |
| `/settings` | `SettingsPage` | Provider configuration |
| `/role-cards` | `RoleCardsPage` | Expert role card management |
| `/rooms` | `RoomsPage` | Room listing |
| `/rooms/create` | `RoomCreatePage` | New room wizard |
| `/rooms/:roomId/discussion` | `DiscussionPage` | Live discussion view |
| `/rooms/:roomId/artifacts` | `ArtifactPage` | Generated output viewer |

**API Client:** A singleton `ApiClient` class wraps `fetch()` calls to `/api/*` endpoints. Vite proxies these to `http://localhost:8000` during development.

**SSE Hook:** `useDiscussionSSE` manages the EventSource connection for live discussion streaming. It handles four event types (`thinking`, `message`, `error_event`, `done`) and implements exponential backoff reconnection (max 3 attempts).

### Backend

FastAPI application running on Uvicorn with async SQLAlchemy.

**Router Modules:**

| Router | Prefix | Purpose |
|--------|--------|---------|
| `providers` | `/api/providers` | LLM provider CRUD and connectivity test |
| `role_cards` | `/api/role-cards` | Expert persona CRUD, copy, builtin seed |
| `rooms` | `/api/rooms` | Room lifecycle management |
| `sources` | `/api/sources` | Shared source file/folder management |
| `discussion` | `/api/rooms/{id}/start` | SSE discussion orchestration |
| `artifacts` | `/api/rooms/{id}/artifacts` | Generated output management |

**Service Layer:**

| Service | Responsibility |
|---------|----------------|
| `ProviderService` | Provider CRUD, encrypted key storage |
| `RoleCardService` | Role card CRUD, copy, builtin protection |
| `RoomService` | Room and participant management |
| `MessageService` | Message persistence and retrieval |
| `Orchestrator` | Multi-round discussion state machine |
| `ContextBuilder` | Prompt assembly with token budgeting |
| `ModelClient` | Unified OpenAI-compatible API client with retry |
| `CryptoService` | AES-256-GCM encryption via Fernet |
| `FileIngestion` | File reading with extension/size filtering |
| `ArtifactWriter` | Output file generation to user directory |
| `DiscussionLog` | Discussion log persistence |

---

## Data Flow

### Discussion Lifecycle

```
User clicks "Start Discussion"
         |
         v
POST /api/rooms/{id}/start
         |
         v
+-------------------+
| Load Room with    |
| participants,     |
| providers,        |
| role cards        |
+--------+----------+
         |
         v
+-------------------+
| Create Orchestrator|
| with SSE callback |
+--------+----------+
         |
         v
+-------------------+      SSE: thinking event
| Orchestrator Turn | <--- "主持人 is thinking"
| (build prompt,    |
|  call LLM)        |
+--------+----------+
         |
         v
+-------------------+      SSE: message event
| Save orchestrator | <--- round guidance message
| message to DB     |
+--------+----------+
         |
         v
+-------------------+
| For each expert:  |
|                   |
| 1. Load role card |      SSE: thinking event
| 2. Build prompt   | <--- "{expert} is thinking"
| 3. Call LLM       |
| 4. Save message   |      SSE: message event
|                   | <--- expert opinion
+--------+----------+
         |
         v
+-------------------+
| Update rolling    |
| summary           |
+--------+----------+
         |
         v
+-------------------+
| Check convergence |
| (round limit met?)|
+--------+----------+
         |
    +----+----+
    |         |
    v         v
  Yes        No --> next round
    |
    v
+-------------------+
| Mark room         |      SSE: done event
| completed         | <--- total rounds, messages
+-------------------+
```

### SSE Event Types

| Event | Payload | When |
|-------|---------|------|
| `thinking` | `{room_id, role, status}` | Before each LLM call |
| `message` | `{id, room_id, sender_type, sender_id, content, citations, round}` | After each LLM response |
| `error_event` | `{room_id, error, recoverable}` | On LLM call failure |
| `done` | `{room_id, total_rounds, total_messages, artifact_count}` | Discussion complete |

The frontend consumes these events through `EventSource` with automatic reconnection on connection drops.

---

## Security Architecture

### API Key Protection

API keys are encrypted at rest using Fernet (AES-256-GCM). The encryption key is loaded from the `ENCRYPTION_KEY` environment variable. If no key is configured, a temporary key is generated at startup (keys are not persisted across restarts in this case).

```
User input: API key (plaintext)
     |
     v
CryptoService.encrypt()
     |
     v
Fernet.encrypt(key) --> Base64 ciphertext
     |
     v
Stored in SQLite: providers.api_key_encrypted
     |
     v  (on LLM call)
CryptoService.decrypt(ciphertext) --> plaintext --> ModelClient
```

API keys are never logged, never returned to the frontend in plaintext, and masked (first 8 chars + `***`) in any display context.

### File System Safety

- Outputs are written only to user-specified output directories
- Shared source files are read-only during discussions
- File uploads are filtered by extension whitelist and size limit (default 10MB)
- Excluded directories: `node_modules`, `.git`, `dist`, `build`, `.next`, `.venv`, `__pycache__`, `target`, `coverage`

### CORS Policy

CORS is configured to allow only the Vite dev server origins (`http://localhost:5173`, `http://localhost:3000`) during development. Production builds serve the frontend through Tauri's WebView, eliminating CORS concerns.

### Content Security Policy

Tauri enforces a CSP that restricts resource loading to `self` and localhost connections only:

```
default-src 'self';
style-src 'self' 'unsafe-inline';
script-src 'self';
connect-src 'self' http://localhost:* ws://localhost:*
```

---

## Deployment Architecture

### Development

```
Terminal 1: cd frontend && npm run dev     --> Vite on :5173
Terminal 2: cd backend && uvicorn ...      --> FastAPI on :8000
```

Vite proxies `/api` requests to the backend. Frontend hot-reloads on code changes.

### Production (Tauri Desktop App)

```
cargo tauri build
     |
     v
+-----------------------------+
| Expert Room.app / .exe      |
|                             |
| WebView: frontend/dist/     |
| Sidecar: backend binary     |
| Database: $APPDATA/expert_room.db |
+-----------------------------+
```

The backend binary is bundled as a Tauri sidecar. On app launch, Tauri spawns the backend process and monitors it. The database file is stored in the user's application data directory.

### Database

SQLite with async access via `aiosqlite` driver and SQLAlchemy 2.0 async ORM. Database migrations are managed by Alembic.

**Connection string:** `sqlite+aiosqlite:///./expert_room.db`

The database is a single file, making backup and portability straightforward. No external database server is required.

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Desktop framework | Tauri | Small binary size, native performance, Rust security model, sidecar support |
| Frontend framework | React 18 | Mature ecosystem, concurrent features, large talent pool |
| State management | Zustand | Minimal boilerplate, no providers needed, good TypeScript support |
| Styling | Tailwind CSS | Utility-first, rapid prototyping, small production bundle |
| Forms | React Hook Form + Zod | Performance (uncontrolled inputs), type-safe validation |
| Backend framework | FastAPI | Async native, automatic OpenAPI docs, Pydantic integration |
| ORM | SQLAlchemy 2.0 async | Mature async support, type hints, migration tooling (Alembic) |
| Database | SQLite | Zero-config, single-file, sufficient for local-first desktop app |
| LLM client | httpx + custom wrapper | Async, retry logic, OpenAI-compatible endpoint support |
| Real-time | SSE | Simple, one-directional (server to client), no WebSocket complexity needed |
| Encryption | Fernet (AES-256-GCM) | Authenticated encryption, built-in Python library, key derivation included |
| ID generation | UUID v4 strings | No collision risk, no auto-increment dependency, works across distributed scenarios |

### Why Not WebSocket

SSE was chosen over WebSocket for discussion streaming because:
- Data flows one direction (server to client)
- SSE auto-reconnects natively in the browser
- No additional protocol complexity
- Sufficient for the discussion use case (no client-to-server streaming needed during a round)

### Why SQLite Over PostgreSQL

The application is local-first with a single user. SQLite eliminates the need for a separate database process, simplifies installation, and the file-based storage makes the database portable. The async driver (`aiosqlite`) prevents the database from blocking the event loop during I/O.

---

## Database Schema

Six core tables with UUID primary keys:

```
providers
  id, name, type, base_url, api_key_encrypted
  default_model, default_temperature, default_max_tokens
  enabled, created_at, updated_at

role_cards
  id, name, description, expertise (JSON), responsibilities (JSON)
  constraints (JSON), system_prompt, output_style
  default_provider_id -> providers.id
  default_model, temperature
  is_builtin, created_at, updated_at

rooms
  id, name, goal, mode, strategy
  output_directory, round_limit, status
  created_at, updated_at

room_participants (composite PK: room_id + role_card_id)
  room_id -> rooms.id (CASCADE)
  role_card_id -> role_cards.id
  provider_id -> providers.id
  model_override

messages
  id, room_id -> rooms.id (CASCADE)
  sender_type ('user'|'expert'|'orchestrator'|'system')
  sender_id (nullable, role_card_id for experts)
  content, citations (JSON), round
  created_at

shared_sources
  id, room_id -> rooms.id (CASCADE)
  source_type ('file'|'folder'|'text')
  path, content, file_count
  created_at

artifacts
  id, room_id -> rooms.id (CASCADE)
  artifact_type ('markdown'|'text'|'code'|'csv')
  title, file_path, summary
  created_at
```

### Relationships

- `Provider` 1:N `RoleCard` (default provider for a role card)
- `Room` N:M `RoleCard` through `RoomParticipant` (each participant binds a room, role card, and provider)
- `Room` 1:N `Message` (all discussion messages)
- `Room` 1:N `SharedSource` (uploaded files/folders)
- `Room` 1:N `Artifact` (generated outputs)

---

## Project Structure

```
project/
  src-tauri/                 # Tauri shell (Rust)
    src/main.rs              # Sidecar management, health check command
    tauri.conf.json          # Window config, sidecar bundling, CSP
    Cargo.toml               # Rust dependencies

  frontend/                  # React SPA
    src/
      api/client.ts          # HTTP API client singleton
      components/            # UI components by domain
        artifacts/           # Artifact display
        discussion/          # Live discussion UI
        provider/            # Provider config forms
        role-card/           # Role card management
        room/                # Room creation and listing
        shared/              # Layout, common components
      hooks/
        useDiscussionSSE.ts  # SSE connection management
      pages/                 # Route-level page components
      stores/                # Zustand stores
      types/                 # TypeScript type definitions
    vite.config.ts           # Vite config with /api proxy

  backend/                   # FastAPI application
    app/
      config.py              # Pydantic Settings (env-based config)
      database.py            # SQLAlchemy async engine and session
      main.py                # FastAPI app factory, router registration
      models/                # SQLAlchemy ORM models (6 tables)
      routers/               # API route handlers (6 modules)
      schemas/               # Pydantic request/response models
      services/              # Business logic (11 services)
      seed/                  # Built-in role card seeding
      utils/                 # Logging, helpers
    alembic/                 # Database migrations
    tests/                   # Test suite

  docs/                      # Project documentation
    api-contracts.md         # REST API reference
    architecture.md          # This file
```
