# Module Spec: WhatsApp ETL (read-only, last 30 days)


## Purpose
Synchronize WhatsApp messages via WhatsApp Web automation (Playwright) into the `messages` table.


## Scope (MVP)
- Read-only. No sending.
- Lookback: last 30 days (configurable)
- Capture attachment metadata and persist image files locally. Image extraction is disabled by default (toggle).


## Source
- WhatsApp Web (`web.whatsapp.com`) using Playwright Chromium in a container with a persistent user data dir (`/data/whatsapp_profile`).


## Flow
1) Ensure logged-in session (one-time QR pairing persists in profile volume).
2) Enumerate recent chats and scroll to load messages within `WHATSAPP_SYNC_LOOKBACK_DAYS`.
3) Extract message DOM: id, ts, sender, text, chat id.
4) Map to `messages` rows:
   - `platform='whatsapp'`
   - `external_id` ← stable DOM/message id
   - `thread_external_id` ← chat id
   - `sender_id` ← phone or contact name (raw for MVP)
   - `recipient_ids` ← group participants or single recipient
   - `content_snippet` ← text
   - `ts` ← timestamp (ISO8601)
   - `is_outgoing` ← based on message bubble role
   - `source_app='WhatsApp Web'`
   - `is_agent_channel=0` (do not store agent chat here)
   - `exclude_from_automation` ← set to 1 if chat is recognized as an agent conversation thread (Phase 2)

5) Attachment ingestion (images):
   - Detect image attachments in DOM and download to `ATTACHMENTS_DIR` with content-addressed paths (checksum-based).
   - Upsert `attachments` row (Postgres) with `{ message_id, source='whatsapp', media_type, file_path, checksum }`.
   - Update `messages.has_attachments=1`.

6) Queue extraction job (no-op by default):
   - If `IMAGE_PROCESSING_ENABLED=false` (default), do not invoke any extractor; only enqueue metadata for future processing.
   - When enabled in later sprint, route to local OCR/vision module with provenance capture.


## Agent conversation detection (Phase 2)
- Preferred: a dedicated WhatsApp contact/thread for Kenny; set `WHATSAPP_AGENT_CONTACT` (1:1) or `WHATSAPP_AGENT_THREAD_NAME` (group). Mark all messages in that thread as `is_agent_channel=1` and `exclude_from_automation=1`.
- Alternative: keyword addressing (e.g., messages starting with "Kenny," or "@Kenny") when a dedicated thread is not used.
- Detected agent-directed messages are routed to the chat pipeline and may generate proposals (e.g., calendar event suggestions) rather than general triage.
7) Upsert by (`platform`,`external_id`).
8) Update `sync_state` with `source='whatsapp'` and last seen timestamp.


## Error Handling
- Detect session expiry; emit an event to prompt re-scan of QR.
- Backoff on DOM changes; feature-flag selectors.
- Rate-limit scrolling and scraping.


## Configuration
- `WHATSAPP_SYNC_LOOKBACK_DAYS=30`
- `WHATSAPP_SYNC_INTERVAL_MINUTES=10`
 - `WHATSAPP_ENABLE_SENDING=false` (Phase 2)
 - `WHATSAPP_AGENT_CONTACT=` (optional; phone number or saved contact name)
 - `WHATSAPP_AGENT_THREAD_NAME=` (optional; group/chat name)
 - `IMAGE_PROCESSING_ENABLED=false` (global toggle; default OFF)
 - `ATTACHMENTS_DIR=/data/attachments`
 - `PG_URL=postgresql://kenny:kenny@postgres:5432/kenny`


## Metrics (recommended)
- `whatsapp_sync_messages_fetched`
- `whatsapp_sync_upserts`
- `whatsapp_attachments_saved`
- `whatsapp_extraction_jobs_enqueued`
- `whatsapp_sync_errors`
- `whatsapp_sync_cycle_seconds`


## Health
- Expose a worker `/health` that includes last successful sync timestamp and session status (logged-in/expired).
 - Include Postgres readiness in health output.


## Provenance (for extraction when enabled later)
- Link `extractions.attachment_id` to `attachments.id`; include `messages.thread_external_id` and `messages.external_id` in `extractions.provenance` JSON.


