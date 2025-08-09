## Module Spec: macOS Bridge

### Purpose
Expose a minimal local HTTP API on macOS to read (and later write) data from system apps that are not accessible from containers: Contacts, Calendar, Mail, Messages. Keeps privileged automation on host and everything else in Docker.

### Scope (MVP)
- Read-only endpoints for Contacts, iMessage, Calendar events, and Mail headers/content (recent only).
 - Calendar writes are gated by upstream approval (see ADR-0007).
- No write actions in MVP (Phase 2 will add calendar event creation and message sending).

### Responsibilities
- Implement data access via the most robust mechanism per app:
  - Messages (iMessage): read from `~/Library/Messages/chat.db` (SQLite) with Full Disk Access.
  - Contacts: use Contacts.framework via PyObjC (`pyobjc-framework-Contacts`).
  - Calendar: use EventKit via PyObjC (`pyobjc-framework-EventKit`).
  - Mail: AppleScript for selected mailboxes (subject, sender, date, snippet, message id; optionally full text for recent messages).
- Normalize into simple JSON schemas used by ETL.
- Handle permissions prompts and fail gracefully with actionable errors.

### Security
- Listens only on `127.0.0.1:5100`.
- No external network exposure. Enforce a simple local API key or OS user check.
- Optional per-request rate limits (e.g., token bucket) to protect AppleScript automation.
- Avoid storing data; act as a pass-through.

### HTTP API (proposed)
- `GET /health` → `{ status: 'ok' }`
- `GET /v1/contacts?updated_since=ISO8601` → `[Contact]`
- `GET /v1/messages/imessage?since=ISO8601&limit=1000` → `[Message]`
- `GET /v1/calendar/events?start=ISO8601&end=ISO8601` → `[Event]`
- `GET /v1/calendar/list` → `[ { id, name, account, is_default } ]`
- `GET /v1/mail/messages?mailbox=Inbox&since=ISO8601&limit=500` → `[MailMessage]`
- `GET /v1/mail/messages/body?id=MAIL_ID` → `{ id, body }` (lazy fetch)
 - `POST /v1/calendar/events` → `{ id }` with body `{ calendar_id, title, start, end, attendees[]?, notes? }`
 - Phase 2 (not MVP): `POST /v1/calendar/events`, `POST /v1/messages/imessage:send`, `POST /v1/mail/messages:send`

### Error taxonomy
- `BRIDGE_PERMISSION_DENIED` (user needs to grant Full Disk/Automation/Accessibility)
- `BRIDGE_RATE_LIMITED` (client exceeded local rate limit)
- `BRIDGE_SOURCE_LOCKED` (e.g., iMessage DB locked)
- `BRIDGE_INVALID_ARGUMENT` (validation error)
- `BRIDGE_INTERNAL_ERROR`

### Data Shapes (simplified)
- Contact: `{ id, name, phones[], emails[], job_title?, interests[] }`
- Message: `{ id, platform, thread_id, sender_id, recipient_ids[], ts, content }`
- Event: `{ id, title, start, end, attendees[], source }`
- MailMessage: `{ id, thread_id, from, to[], subject, ts, snippet, body? }`

### Dependencies
- Python 3.11+
- `pyobjc` bundles (`Contacts`, `EventKit`), AppleScript via `osascript` or `py-applescript`.

### Permissions (System Settings → Privacy & Security)
- Full Disk Access (read iMessage DB and Mail files)
- Accessibility and Automation (to control Mail/Contacts where AppleScript is used)

### Operational Notes
- Return incremental deltas using timestamps/rowids where possible to reduce payloads.
- Include `source_app` and `last_sync_ts` in responses for auditing.
- Throttle AppleScript calls; paginate messages (e.g., 100–200 per page) to avoid UI blocking.
- Prefer plain-text body; avoid attachments/media in MVP.
- Default allowed mailboxes: `Inbox`, `Sent` (configurable via env in workers); reject others for MVP.
- Default lookback if `since` is omitted (computed by workers): 30 days.
- Validate `calendar_id` against `GET /v1/calendar/list` and reject unknown ids.
 - Log structured events with request ids for correlation with API/workers.


