# Module Spec: iMessage ETL (last 30 days)
## Purpose
Synchronize iMessage (Messages.app) into the unified `messages` table.
## Scope (MVP)
- Lookback: last 30 days (configurable)
- Read-only. No sending.
- Exclude attachments for MVP.
## Source
- Database: `~/Library/Messages/chat.db` (SQLite). Requires Full Disk Access.
- Key tables/fields: `message`, `chat`, `chat_message_join`, `handle`.
## Flow
1) Determine `since_ts = now - IMESSAGE_SYNC_LOOKBACK_DAYS`.
2) Query `message` rows with `date`/`date_read`/`date_delivered` >= `since_ts` (convert Apple epoch to Unix when needed), join to `chat` and `handle` for thread and participant metadata.
3) Map to `messages` rows:
   - `platform='imessage'`
   - `external_id` ← `message.ROWID`
   - `thread_external_id` ← `chat.guid`
   - `sender_id` ← sender handle (phone/email)
   - `recipient_ids` ← array of participant handles (excluding sender)
   - `content_snippet` ← `text`
   - `ts` ← message timestamp (ISO8601)
   - `is_outgoing` ← `is_from_me`
   - `source_app='Messages'`
   - `is_agent_channel` ← 1 if thread is the designated agent chat thread (Phase 2), else 0
   - `exclude_from_automation` ← mirror `is_agent_channel`
4) Upsert by (`platform`,`external_id`).
5) Update `sync_state` with `source='imessage'` and last processed timestamp/ROWID.
## Error Handling
- Detect locked DB; retry with backoff.
- Handle schema changes across macOS versions by querying pragma and adapting joins.
## Configuration
- `IMESSAGE_SYNC_LOOKBACK_DAYS=30`
- `IMESSAGE_SYNC_INTERVAL_MINUTES=10`
## Metrics (recommended)
- `imessage_sync_messages_fetched`
- `imessage_sync_upserts`
- `imessage_sync_errors`
- `imessage_sync_cycle_seconds`
## Health
- Expose a worker `/health` that includes last successful sync timestamp for iMessage.
