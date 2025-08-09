## Module Spec: Approvals Workflow (Calendar Events)

### Purpose
Provide a user-facing queue where the agent proposes events extracted from messages/emails and the user explicitly approves or rejects creation.

### Scope (MVP)
- Proposals only for calendar events.
- Single approval action posts one event to a selected calendar via the macOS Bridge.

### Flow
1) Triage workers/LLM identify actionable items and create a Proposal record with suggested title/time/attendees.
2) UI displays proposals with source message context and an “Approve” button. Chat-first approvals are supported in Web Chat; macOS notifications are not used by default.
3) On approval, the UI requires the user to pick a target calendar (default can be suggested via `CALENDAR_DEFAULT_CALENDAR_ID`), then the API calls the Bridge `POST /v1/calendar/events`.
4) Store result id, mark proposal as approved, and optionally write back a confirmation reply in the originating channel (Phase 2, off by default).

### Optional confirmation reply (Phase 2)
- If the source channel supports sending (e.g., iMessage or WhatsApp with sending enabled), the system can send a brief confirmation back to the requester after event creation. This is disabled by default and requires explicit user approval.

### Data Model
- `proposals`:
  - `id` TEXT PK
  - `type` TEXT CHECK (type IN ('calendar_event'))
  - `source_message_id` INTEGER NOT NULL
  - `title` TEXT NOT NULL
  - `start` TEXT NOT NULL
  - `end` TEXT NOT NULL
  - `attendees` TEXT NULL (JSON)
  - `notes` TEXT NULL
  - `confidence` REAL NULL
  - `status` TEXT CHECK (status IN ('pending','approved','rejected')) DEFAULT 'pending'
  - `created_at` TEXT NOT NULL
  - `updated_at` TEXT NOT NULL
  - `result_ref` TEXT NULL -- created event id

Indexes:
- `idx_proposals_status_created_at` on (`status`,`created_at`)

### Config
- `CALENDAR_REQUIRE_APPROVAL=true` (default)
- `CALENDAR_DEFAULT_CALENDAR_ID` (optional)
 - `AGENT_DEFAULT_CHANNEL=whatsapp|imessage|web`
 - `APPROVALS_CHAT_FIRST=true` (default)


