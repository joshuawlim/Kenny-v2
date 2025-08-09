## Module Spec: Mail ETL (Inbox & Sent)

### Purpose
Synchronize Apple Mail messages (Inbox and Sent) into the unified `messages` table, read-only.

### Scope (MVP)
- Mailboxes: Inbox, Sent
- Fields: id, thread id, from, to/cc, subject, date, snippet
- Body: fetched lazily on demand for recent messages; not fetched by default

### Flow
1) Scheduler (every 10 minutes) triggers per-mailbox sync jobs.
2) For each mailbox, call macOS Bridge:
   - `GET /v1/mail/messages?mailbox=Inbox&since=ISO8601&limit=500`
   - Iterate with pagination until no more results.
3) Map to `messages` rows:
   - `platform='mail'`
   - `external_id` ← Mail-provided id (or Message-ID header if available)
   - `thread_external_id` ← conversation/thread id if available
   - `mailbox` ← 'Inbox' or 'Sent'
   - `sender_id` ← email address (string) for now; later map to `contacts`
   - `recipient_ids` ← emails array (JSON string)
   - `subject`, `content_snippet`, `ts`, `is_outgoing`
   - `source_app='Apple Mail'`
4) Upsert strategy:
   - Insert if `(platform, external_id)` not present
   - Else update mutable fields (snippet, subject, thread id) and `updated_at`
5) Store progress:
   - Update `sync_state` with `source='mail:Inbox'` or `mail:Sent'` and last message timestamp

### On-demand body fetch
- API: `GET /v1/mail/messages/body?id=MAIL_ID`
- Worker fetches and stores in `messages.content_body` only when required for NLP tasks, respecting a max age window (e.g., 30 days).

### Error handling
- Backoff on Bridge errors, retry with jitter.
- Detect permission errors and surface actionable logs.
- Paginate to avoid large AppleScript calls (100–200 items per page).

### Configuration
- `MAIL_SYNC_MAILBOXES=Inbox,Sent`
- `MAIL_SYNC_INTERVAL_MINUTES=10`
- `MAIL_BODY_MAX_AGE_DAYS=30`

### Metrics (optional)
- `mail_sync_messages_fetched{mailbox}`
- `mail_sync_upserts{mailbox}`
- `mail_sync_errors{mailbox}`
 - `mail_sync_cycle_seconds{mailbox}`

### Health
- Expose a worker `/health` that includes last successful sync timestamp per mailbox.


