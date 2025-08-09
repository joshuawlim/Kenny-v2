## ADR-0002: WhatsApp integration (read-only via WhatsApp Web)

### Status
Accepted

### Context
- Requirement: The agent should access WhatsApp conversations. For MVP, read-only is acceptable.
- Constraint: Everything must run locally (with normal internet access). Prefer Docker Compose for the main system.
- Risks: Unofficial APIs for WhatsApp are brittle and may violate ToS. WhatsApp Desktop’s on-disk data format is undocumented and changes. Mobile-device pairing via reverse-engineered libraries is unreliable.

### Decision
- Use WhatsApp Web controlled locally via a headless browser (Playwright) from a background worker. The worker runs inside Docker and connects to `web.whatsapp.com` using a persistent browser profile stored in a Docker volume.
- Perform read-only synchronization of chats and messages into the local SQLite database. No send/modify actions in MVP.
- Authenticate once by scanning a QR code (rendered in the Web UI or via a temporary devtools tunnel) and persist the session state in the browser profile volume.
- Respect rate limiting and avoid aggressive scraping. Pull deltas periodically (e.g., every 5–10 minutes) and on demand.

### Consequences
- Pros:
  - Fully local execution of the automation (headless browser in Docker).
  - Avoids reverse-engineered private protocols. More resilient than parsing WhatsApp Desktop’s internal LevelDB/IndexedDB.
  - Simple mental model; easy to disable.
- Cons:
  - Requires a one-time QR login and session maintenance.
  - Subject to UI changes in WhatsApp Web; requires upkeep.
  - Limited to read-only for MVP.

### Alternatives Considered
1) Parse WhatsApp Desktop local data stores: brittle, undocumented, and format may change without notice.
2) Use community libraries (e.g., Baileys/go-whatsapp): higher maintenance and ToS risk.
3) Manual export/import: too manual for continuous sync.

### Implementation Notes (MVP)
- Container: `workers` includes Playwright + Chromium. Persist user data dir at `/data/whatsapp_profile`.
- Scheduler: periodic sync job enumerates chats, reads recent messages, upserts into `messages` table with `platform = "whatsapp"`.
- Privacy: Only load message content and metadata needed for your features; redact media by default.


