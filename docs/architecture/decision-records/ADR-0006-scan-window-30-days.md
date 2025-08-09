## ADR-0006: Default 30-day lookback for message/email scans (MVP)

### Status
Accepted

### Context
- Requirement: Keep initial sync fast and privacy-preserving while still useful.
- Need a clear default window for messages (iMessage, WhatsApp) and email to avoid syncing years of data.

### Decision
- Use a default 30-day lookback window for:
  - Apple Mail (Inbox, Sent)
  - iMessage (Messages.app database)
  - WhatsApp (via WhatsApp Web)
- Make the window configurable via environment variables.

### Consequences
- Pros: Faster initial sync; less storage and processing; clearer user expectation.
- Cons: Older items won’t be indexed until the window is expanded or a backfill is run.

### Implementation Notes
- Environment variables (workers):
  - `MAIL_BODY_MAX_AGE_DAYS=30` (body fetch window)
  - `MAIL_SYNC_INTERVAL_MINUTES=10`
  - `MAIL_SYNC_MAILBOXES=Inbox,Sent`
  - `IMESSAGE_SYNC_LOOKBACK_DAYS=30`
  - `IMESSAGE_SYNC_INTERVAL_MINUTES=10`
  - `WHATSAPP_SYNC_LOOKBACK_DAYS=30`
  - `WHATSAPP_SYNC_INTERVAL_MINUTES=10`
- Bridge endpoints accept `since=ISO8601`; if omitted, workers will compute `now - LOOKBACK_DAYS`.


