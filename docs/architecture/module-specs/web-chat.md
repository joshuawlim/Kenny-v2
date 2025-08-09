## Module Spec: Web Chat UI

### Purpose
Provide a local web interface to converse with the agent, browse proposed actions (e.g., calendar events), and approve or decline them.

### Scope (MVP)
- Chat with the agent (multi-turn), grounded on local data.
- Approve calendar proposals from the approvals queue.
- Search messages/contacts.
 - Persona name: "Kenny" (configurable via `AGENT_PERSONA_NAME`).

### UI
- Route: `/chat`
- Panels: chat stream, proposals sidebar, search bar.
- Messages show role (user/assistant) and optional linked sources.

### Backend
- Uses Agent API for:
  - `POST /v1/chat` → stream responses from Ollama
  - `GET /v1/proposals` and `POST /v1/proposals/{id}/approve`
  - `GET /v1/search?q=...` (messages/contacts)
 - Configuration:
   - `AGENT_PERSONA_NAME=Kenny`
   - `ENABLE_WEB_CHAT=true`
    - `APPROVALS_CHAT_FIRST=true` (use chat for approvals by default)

### Data
- `agent_conversations`:
  - `id` TEXT PK
  - `created_at` TEXT
- `agent_messages`:
  - `id` TEXT PK
  - `conversation_id` TEXT
  - `role` TEXT CHECK(role IN ('user','assistant'))
  - `content` TEXT
  - `created_at` TEXT

### Duplication Avoidance
- All agent chat messages are stored in dedicated tables and are not inserted into the unified `messages` table.
- The approvals actions refer to `proposals` which link to source messages; agent chat is not considered a source signal for triage.
 - For channels that support sending (Phase 2), the specific agent conversation thread is marked as `is_agent_channel=1` and excluded from automation.


