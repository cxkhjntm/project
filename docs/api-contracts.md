# Expert Room API Contracts

Complete REST API reference for the Expert Room backend. All endpoints return JSON unless noted otherwise.

---

## Base URL

```
http://localhost:8000
```

Interactive docs available at `/docs` (Swagger UI) and `/redoc` (ReDoc).

---

## Common Response Formats

### Error Response

All error responses follow this structure:

```json
{
  "detail": "Human-readable error message"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200  | Success |
| 201  | Created |
| 204  | No Content (successful delete) |
| 400  | Bad request / validation error |
| 403  | Forbidden (e.g., modifying built-in role card) |
| 404  | Resource not found |
| 500  | Internal server error |

---

## Health Check

### `GET /api/health`

Check server status.

**Response** `200 OK`

```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

## Provider API

Manage LLM model service configurations. API keys are stored encrypted (AES-256-GCM) and never exposed in responses; only a masked version is returned.

**Prefix:** `/api/providers`

### Provider Object

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| name | string | Display name (1-100 chars) |
| type | string | Provider type (derived from base_url) |
| base_url | string | API base URL |
| api_key_masked | string | Masked key for display (e.g., `sk-****abcd`) |
| default_model | string | Default model identifier |
| default_temperature | float | 0.0 - 2.0 |
| default_max_tokens | int | 1 - 128000 |
| enabled | boolean | Whether provider is active |
| created_at | datetime | ISO 8601 |
| updated_at | datetime | ISO 8601 |

### `POST /api/providers`

Create a new provider.

**Request Body**

```json
{
  "name": "OpenAI",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "default_model": "gpt-4o",
  "default_temperature": 0.7,
  "default_max_tokens": 4096
}
```

| Field | Required | Constraints |
|-------|----------|-------------|
| name | yes | 1-100 chars |
| base_url | yes | 1-500 chars |
| api_key | yes | min 1 char, encrypted before storage |
| default_model | yes | 1-100 chars |
| default_temperature | no | 0.0-2.0, default 0.7 |
| default_max_tokens | no | 1-128000, default 4096 |

**Response** `201 Created`

```json
{
  "id": "a1b2c3d4-...",
  "name": "OpenAI",
  "type": "openai",
  "base_url": "https://api.openai.com/v1",
  "api_key_masked": "sk-****abcd",
  "default_model": "gpt-4o",
  "default_temperature": 0.7,
  "default_max_tokens": 4096,
  "enabled": true,
  "created_at": "2026-05-30T10:00:00Z",
  "updated_at": "2026-05-30T10:00:00Z"
}
```

### `GET /api/providers`

List all providers.

**Response** `200 OK`

```json
[
  {
    "id": "a1b2c3d4-...",
    "name": "OpenAI",
    "type": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key_masked": "sk-****abcd",
    "default_model": "gpt-4o",
    "default_temperature": 0.7,
    "default_max_tokens": 4096,
    "enabled": true,
    "created_at": "2026-05-30T10:00:00Z",
    "updated_at": "2026-05-30T10:00:00Z"
  }
]
```

### `GET /api/providers/{provider_id}`

Get a single provider by ID.

**Response** `200 OK` - Provider object

**Errors:** `404` if not found

### `PUT /api/providers/{provider_id}`

Update a provider. All fields are optional; only supplied fields are changed.

**Request Body**

```json
{
  "name": "OpenAI Updated",
  "default_model": "gpt-4o-mini",
  "enabled": false
}
```

**Response** `200 OK` - Updated provider object

**Errors:** `404` if not found

### `DELETE /api/providers/{provider_id}`

Delete a provider.

**Response** `204 No Content`

**Errors:** `404` if not found

### `POST /api/providers/{provider_id}/test`

Test connectivity to a provider's API endpoint.

**Response** `200 OK`

```json
{
  "success": true,
  "message": "Connection successful",
  "latency_ms": 245.3
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Whether the test passed |
| message | string | Human-readable result |
| latency_ms | float, nullable | Round-trip time in milliseconds |

---

## Role Card API

Manage reusable expert persona cards. Built-in cards cannot be modified or deleted.

**Prefix:** `/api/role-cards`

### Role Card Object

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| name | string | Expert name (1-100 chars) |
| description | string | What this expert does |
| expertise | string[] | Areas of expertise |
| responsibilities | string[] | Key responsibilities |
| constraints | string[], nullable | Behavioral constraints |
| system_prompt | string | Full system prompt |
| output_style | string, nullable | Preferred output format |
| default_provider_id | string, nullable | Preferred provider |
| default_model | string, nullable | Preferred model |
| temperature | float | 0.0 - 2.0 |
| is_builtin | boolean | Whether this is a built-in card |
| created_at | datetime | ISO 8601 |
| updated_at | datetime | ISO 8601 |

### `POST /api/role-cards`

Create a new role card.

**Request Body**

```json
{
  "name": "Code Reviewer",
  "description": "Expert at reviewing code for quality and security",
  "expertise": ["code review", "security", "best practices"],
  "responsibilities": ["Review code", "Identify bugs", "Suggest improvements"],
  "constraints": ["Focus on actionable feedback", "No rewriting entire files"],
  "system_prompt": "You are an expert code reviewer...",
  "output_style": "structured",
  "default_provider_id": "a1b2c3d4-...",
  "default_model": "gpt-4o",
  "temperature": 0.5
}
```

| Field | Required | Constraints |
|-------|----------|-------------|
| name | yes | 1-100 chars |
| description | yes | min 1 char |
| expertise | yes | min 1 item |
| responsibilities | yes | min 1 item |
| constraints | no | list of strings |
| system_prompt | yes | min 1 char |
| output_style | no | free text |
| default_provider_id | no | UUID of a provider |
| default_model | no | model identifier |
| temperature | no | 0.0-2.0, default 0.7 |

**Response** `201 Created` - Role card object

### `GET /api/role-cards`

List all role cards.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| builtin | boolean | Filter: `true` = built-in only, `false` or omit = all |

**Response** `200 OK`

```json
[
  {
    "id": "b2c3d4e5-...",
    "name": "Code Reviewer",
    "description": "Expert at reviewing code for quality and security",
    "expertise": ["code review", "security", "best practices"],
    "responsibilities": ["Review code", "Identify bugs", "Suggest improvements"],
    "constraints": ["Focus on actionable feedback"],
    "system_prompt": "You are an expert code reviewer...",
    "output_style": "structured",
    "default_provider_id": "a1b2c3d4-...",
    "default_model": "gpt-4o",
    "temperature": 0.5,
    "is_builtin": false,
    "created_at": "2026-05-30T10:00:00Z",
    "updated_at": "2026-05-30T10:00:00Z"
  }
]
```

### `GET /api/role-cards/{role_card_id}`

Get a single role card.

**Response** `200 OK` - Role card object

**Errors:** `404` if not found

### `PUT /api/role-cards/{role_card_id}`

Update a role card. Built-in cards cannot be modified.

**Request Body** - Any subset of RoleCardCreate fields.

**Response** `200 OK` - Updated role card object

**Errors:** `403` if built-in, `404` if not found

### `DELETE /api/role-cards/{role_card_id}`

Delete a role card. Built-in cards cannot be deleted.

**Response** `204 No Content`

**Errors:** `403` if built-in, `404` if not found

### `POST /api/role-cards/{role_card_id}/copy`

Create a copy of an existing role card with a new name.

**Request Body**

```json
{
  "new_name": "My Custom Code Reviewer"
}
```

| Field | Required | Constraints |
|-------|----------|-------------|
| new_name | yes | 1-100 chars |

**Response** `200 OK` - New role card object

**Errors:** `404` if source not found

---

## Room API

Create and manage expert discussion rooms.

**Prefix:** `/api/rooms`

### Room Object

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| name | string | Room name (1-200 chars) |
| goal | string | Discussion goal/prompt |
| mode | string | `code_document`, `document`, or `code` |
| strategy | string | Discussion strategy (default: `standard`) |
| output_directory | string | File output path |
| round_limit | int | Max discussion rounds (1-20) |
| status | string | `draft`, `running`, `completed`, or `failed` |
| created_at | datetime | ISO 8601 |
| updated_at | datetime | ISO 8601 |
| participants | Participant[] | List of participants |

### Participant Object

| Field | Type | Description |
|-------|------|-------------|
| room_id | string | Parent room UUID |
| role_card_id | string | Role card UUID |
| provider_id | string | Provider UUID |
| model_override | string, nullable | Override model for this participant |

### `POST /api/rooms`

Create a new room with participants.

**Request Body**

```json
{
  "name": "API Design Review",
  "goal": "Design a REST API for user management",
  "mode": "code_document",
  "strategy": "standard",
  "output_directory": "C:/projects/output",
  "round_limit": 5,
  "participants": [
    {
      "role_card_id": "b2c3d4e5-...",
      "provider_id": "a1b2c3d4-...",
      "model_override": null
    },
    {
      "role_card_id": "c3d4e5f6-...",
      "provider_id": "a1b2c3d4-...",
      "model_override": "gpt-4o-mini"
    }
  ]
}
```

| Field | Required | Constraints |
|-------|----------|-------------|
| name | yes | 1-200 chars |
| goal | yes | min 1 char |
| mode | no | default `code_document` |
| strategy | no | default `standard` |
| output_directory | yes | 1-500 chars |
| round_limit | no | 1-20, default 5 |
| participants | yes | min 1 participant |

**Response** `201 Created` - Room object with participants

### `GET /api/rooms`

List all rooms (without participants).

**Response** `200 OK`

```json
[
  {
    "id": "d4e5f6a7-...",
    "name": "API Design Review",
    "goal": "Design a REST API for user management",
    "mode": "code_document",
    "status": "draft",
    "created_at": "2026-05-30T10:00:00Z",
    "updated_at": "2026-05-30T10:00:00Z"
  }
]
```

### `GET /api/rooms/{room_id}`

Get a single room with participants.

**Response** `200 OK` - Full room object

**Errors:** `404` if not found

### `PUT /api/rooms/{room_id}`

Update room settings. Only modifies the room itself, not participants.

**Request Body** - Any subset of room fields (excluding participants).

**Response** `200 OK` - Updated room object

**Errors:** `404` if not found

### `DELETE /api/rooms/{room_id}`

Delete a room and all related data (messages, artifacts, sources).

**Response** `204 No Content`

**Errors:** `404` if not found

---

## Shared Sources API

Attach files, folders, or text content to a room for expert context.

**Prefix:** `/api/rooms/{room_id}/sources` (list/create), `/api/sources/{source_id}` (delete)

### Source Object

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| room_id | string | Parent room UUID |
| source_type | string | `file`, `folder`, or `text` |
| path | string, nullable | File/folder path |
| content | string, nullable | Text content |
| file_count | int | Number of files represented |
| created_at | datetime | ISO 8601 |

### `POST /api/rooms/{room_id}/sources`

Add a source to a room. Uses `multipart/form-data`.

**Form Fields**

| Field | Required | Description |
|-------|----------|-------------|
| source_type | yes | `file`, `folder`, or `text` |
| file | conditional | Required when `source_type=file` |
| path | conditional | Required when `source_type=folder` |
| content | conditional | Required when `source_type=text` |

**Example** (file upload):

```bash
curl -X POST /api/rooms/{room_id}/sources \
  -F "source_type=file" \
  -F "file=@readme.md"
```

**Example** (folder reference):

```bash
curl -X POST /api/rooms/{room_id}/sources \
  -F "source_type=folder" \
  -F "path=C:/projects/myapp"
```

**Example** (text paste):

```bash
curl -X POST /api/rooms/{room_id}/sources \
  -F "source_type=text" \
  -F "content=Some inline text content..."
```

**Response** `201 Created` - Source object

**Errors:** `400` if validation fails, `404` if room not found

### `GET /api/rooms/{room_id}/sources`

List all sources attached to a room.

**Response** `200 OK`

```json
[
  {
    "id": "e5f6a7b8-...",
    "room_id": "d4e5f6a7-...",
    "source_type": "file",
    "path": "readme.md",
    "content": null,
    "file_count": 1,
    "created_at": "2026-05-30T10:00:00Z"
  }
]
```

**Errors:** `404` if room not found

### `DELETE /api/sources/{source_id}`

Delete a source.

**Response** `204 No Content`

**Errors:** `404` if source not found

---

## Discussion API

Start and monitor multi-expert discussions. Uses Server-Sent Events (SSE) for real-time streaming.

**Prefix:** `/api/rooms/{room_id}`

### `POST /api/rooms/{room_id}/start`

Start a discussion in a room. Returns an SSE stream.

The room must be in `draft` or `completed` status and have at least one participant. While running, the room status changes to `running`, then to `completed` or `failed` when done.

**Response** `200 OK` (SSE stream)

```
Content-Type: text/event-stream
```

#### SSE Event Types

| Event | Data | Description |
|-------|------|-------------|
| `thinking` | `{ "expert_name": "...", "content": "..." }` | Expert is generating a response |
| `message` | `{ "id": "...", "room_id": "...", "sender_type": "expert", "sender_id": "...", "content": "...", "round": 1, "citations": [...], "created_at": "..." }` | New message from an expert, orchestrator, or system |
| `error` | `{ "message": "...", "expert_name": "..." }` | Error during discussion |
| `done` | `{ "success": true, "total_messages": 12, "total_rounds": 3 }` | Discussion completed |

#### Example SSE Stream

```
event: thinking
data: {"expert_name": "Code Reviewer", "content": "Analyzing the API structure..."}

event: message
data: {"id": "msg-001", "room_id": "...", "sender_type": "expert", "sender_id": "role-card-uuid", "content": "The API design looks good overall, but I have concerns about...", "round": 1, "citations": [], "created_at": "2026-05-30T10:01:00Z"}

event: thinking
data: {"expert_name": "Architect", "content": "Considering scalability implications..."}

event: message
data: {"id": "msg-002", ...}

event: done
data: {"success": true, "total_messages": 12, "total_rounds": 3}
```

**Errors:** `400` if room is in invalid state or has no participants, `404` if room not found

### `GET /api/rooms/{room_id}/messages`

Get all messages for a room.

**Query Parameters**

| Param | Type | Description |
|-------|------|-------------|
| limit | int, nullable | Max messages to return |
| offset | int, nullable | Skip first N messages |

**Response** `200 OK`

```json
[
  {
    "id": "msg-001",
    "room_id": "d4e5f6a7-...",
    "sender_type": "orchestrator",
    "sender_id": null,
    "content": "Let's begin the discussion about API design.",
    "citations": null,
    "round": 0,
    "created_at": "2026-05-30T10:00:30Z"
  },
  {
    "id": "msg-002",
    "room_id": "d4e5f6a7-...",
    "sender_type": "expert",
    "sender_id": "b2c3d4e5-...",
    "content": "I'll start by reviewing the current API structure...",
    "citations": [
      {
        "source_id": "e5f6a7b8-...",
        "file": "api-spec.yaml",
        "snippet": "paths: /users: ..."
      }
    ],
    "round": 1,
    "created_at": "2026-05-30T10:01:00Z"
  }
]
```

| sender_type | Description |
|-------------|-------------|
| `orchestrator` | Discussion coordinator |
| `expert` | Expert participant (sender_id = role card UUID) |
| `system` | System messages |
| `user` | User messages |

**Errors:** `404` if room not found

### `GET /api/rooms/{room_id}/messages/stream`

Stream new messages via SSE. Polls for new messages every second.

**Response** `200 OK` (SSE stream)

```
event: message
data: {"id": "msg-003", "room_id": "...", "sender_type": "expert", "sender_id": "...", "content": "...", "round": 2, "created_at": "..."}
```

**Errors:** `404` if room not found

---

## Artifact API

Generate and retrieve final output artifacts from discussions.

### Artifact Object

| Field | Type | Description |
|-------|------|-------------|
| id | string | UUID |
| room_id | string | Parent room UUID |
| artifact_type | string | `markdown`, `text`, `code`, or `csv` |
| title | string | Artifact title (1-200 chars) |
| file_path | string | Absolute file path |
| summary | string, nullable | Brief content summary |
| created_at | datetime | ISO 8601 |

### `POST /api/rooms/{room_id}/synthesize`

Generate an artifact from a room's discussion messages.

**Request Body**

```json
{
  "artifact_type": "markdown",
  "title": "API Design Document",
  "include_citations": true,
  "max_length": 10000
}
```

| Field | Required | Constraints |
|-------|----------|-------------|
| artifact_type | no | `markdown`, `text`, `code`, or `csv`. Default: `markdown` |
| title | no | Override artifact title |
| include_citations | no | Include source citations. Default: `true` |
| max_length | no | Max output length in chars, min 100 |

**Response** `200 OK`

```json
{
  "artifact": {
    "id": "f6a7b8c9-...",
    "room_id": "d4e5f6a7-...",
    "artifact_type": "markdown",
    "title": "API Design Document",
    "file_path": "C:/projects/output/api-design-document.md",
    "summary": "Comprehensive API design with endpoints and data models",
    "created_at": "2026-05-30T10:05:00Z"
  },
  "content_preview": "# API Design Document\n\n## Overview\n\n...",
  "message": "Artifact generated successfully"
}
```

**Errors:** `400` if no messages exist, `404` if room not found, `500` if generation fails

### `GET /api/rooms/{room_id}/artifacts`

List all artifacts for a room, ordered by creation date (newest first).

**Response** `200 OK`

```json
[
  {
    "id": "f6a7b8c9-...",
    "room_id": "d4e5f6a7-...",
    "artifact_type": "markdown",
    "title": "API Design Document",
    "file_path": "C:/projects/output/api-design-document.md",
    "summary": "Comprehensive API design",
    "created_at": "2026-05-30T10:05:00Z"
  }
]
```

**Errors:** `404` if room not found

### `GET /api/artifacts/{artifact_id}/content`

Get the full text content of an artifact file.

**Response** `200 OK`

```json
{
  "content": "# API Design Document\n\n## Overview\n\nThis document describes...",
  "encoding": "utf-8"
}
```

| Field | Type | Description |
|-------|------|-------------|
| content | string | Full file contents |
| encoding | string | Always `utf-8` |

**Errors:** `404` if artifact not found, `500` if file cannot be read

---

## Typical Workflow

```
1. POST /api/providers          Create a provider (API key config)
2. POST /api/providers/{id}/test   Verify connectivity
3. GET  /api/role-cards         Browse built-in experts
4. POST /api/rooms              Create a room with participants
5. POST /api/rooms/{id}/sources Attach files or folders
6. POST /api/rooms/{id}/start   Begin discussion (SSE stream)
7. GET  /api/rooms/{id}/messages  Review all messages
8. POST /api/rooms/{id}/synthesize Generate final artifact
9. GET  /api/artifacts/{id}/content Read the output
```
