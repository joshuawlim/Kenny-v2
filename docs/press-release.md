# Kenny v2 — Local‑First Management Assistant (PR/FAQ)

## For Immediate Release

Kenny v2 is a local‑first Management Assistant that runs entirely on your Mac. It unifies recent messages across Apple Mail, iMessage, and WhatsApp (read‑only in MVP), highlights what matters, and drafts safe, human‑approved actions like calendar events. All AI runs locally via Ollama; no cloud dependency, no third‑party telemetry.

### The Problem

Busy people drown in messages and coordination. Existing “AI assistants” push data to the cloud, raising privacy concerns and complicating approvals for sensitive actions like calendar changes.

### The Solution

Kenny organizes recent communications locally, surfaces actionable items, and turns them into explicit proposals that you can approve in a simple chat‑first workflow. Nothing leaves your machine unless you explicitly allow it. Calendar writes are gated by approval every time.

### How It Works (MVP)

- Local‑only architecture on macOS with a lightweight macOS Bridge for system data access (Contacts, Calendar, Mail, Messages).
- Read‑only ETL pipelines synchronize the last 30 days of Apple Mail (Inbox & Sent), iMessage, and WhatsApp Web into a unified `messages` store.
- Hybrid search blends local embeddings (nomic‑embed‑text via Ollama) with fast keyword search over SQLite.
- Web Chat UI at `http://localhost:8080/chat` to converse with Kenny, browse proposals, and approve calendar events.
- Strict outbound egress allowlist; by default only `Ollama` (host), `macOS Bridge` (host), and `web.whatsapp.com` if WhatsApp sync is enabled.

### Key Benefits

- Privacy by design: local models, local storage, zero third‑party telemetry.
- Signal over noise: unified, recent message view focused on actionability.
- Human‑in‑the‑loop safety: calendar writes require explicit approval with the target calendar chosen each time.
- Simple bring‑up: Docker Compose services plus Ollama on the host.

### MVP Features

- Unified messages: Apple Mail (Inbox & Sent), iMessage, WhatsApp (read‑only) for the last 30 days.
- Approvals queue: calendar event proposals with source context; one‑click Approve creates the event via the Bridge.
- Local Web Chat: converse with Kenny, approve proposals, and search messages/contacts.
- Local search and embeddings: fast keyword and semantic search across messages and agent chat.
- Contacts knowledge base (curated): optional enrichment with provenance and confidence.
- Whitelisted website access (optional): fetch from approved sites (e.g., school calendars) with tight egress controls.
- Daily recap reminders: end‑of‑day digest of key items and inbound messages, delivered locally in the Web Chat (no external egress).

### Security & Privacy

- Local‑first: runs on your Mac; Ollama on the host for LLM and embeddings.
- Outbound allowlist: deny by default; allow only required endpoints.
- Minimal data collection: store only what is needed; no attachments/media in MVP; email body fetched on demand for recent items.
- Audited writes: every calendar event write is tied to an approved proposal.

### Availability

MVP targets macOS with Ollama installed. Bring‑up is documented in the repository README (Docker Compose for services, Ollama on host). Web UI is served locally at `http://localhost:8080`.

### Roadmap (Phase 2 highlights)

- Two‑way iMessage chat (local‑only) via the macOS Bridge.
- Optional WhatsApp sending via local Web automation; hybrid Business API as an opt‑in alternative.
- Observability Dashboard: health, throughput, and value metrics.
- Learning loop: incremental improvements from local feedback and curated exemplars.
- Bring Kenny into conversations to take notes: opt‑in “scribe mode” to capture decisions, action items, and attendees; notes stored locally and linked to the source thread; excluded from automation by default.
- Web search and research: expand beyond site‑specific whitelists with a local, allowlist‑constrained research workflow; all outbound requests remain governed by the egress allowlist.

---

## FAQ

### Does Kenny send messages or modify data automatically?

No. In MVP, all messaging integrations are read‑only. The only write Kenny can perform is creating a calendar event—and only after you explicitly approve it in the UI.

### Will this leak my data to the cloud?

No. Kenny is local‑first. LLM inference and embeddings are served by Ollama on your Mac. There is no third‑party telemetry. Network egress is restricted to a short allowlist and can be enforced with macOS firewall/Little Snitch.

### What data does Kenny index?

- Messages from iMessage and WhatsApp (last 30 days).
- Apple Mail Inbox and Sent (headers/snippets by default; recent bodies fetched on demand).
- Optional whitelisted websites for planning. Attachments/media are out of scope for MVP.

### Can I talk to Kenny outside the web UI?

MVP focuses on the local Web Chat at `http://localhost:8080/chat`. Phase 2 introduces fully local iMessage two‑way chat. WhatsApp two‑way is optional and off by default; it can be local Web automation or a hybrid Business API connector if explicitly accepted.

### How are calendar approvals handled?

Kenny proposes events with title, time, attendees, and rationale. You choose the target calendar at approval time. By default, every event requires approval; you may suggest a default calendar to speed confirmation.

### How does search work?

Kenny combines local embeddings (nomic‑embed‑text via Ollama) with SQLite FTS. Results include message references and can link back to source context.

### What if I don’t want learning?

The learning loop is optional and off by default in MVP. When enabled later, it uses only local feedback and exemplars, never cloud training.

### What happens if WhatsApp Web changes?

WhatsApp sync uses Playwright automation and may require selector updates over time. The system degrades gracefully and surfaces health status for quick fixes.

### Where is my data stored and how do I back it up?

SQLite databases and profiles live in local Docker volumes (e.g., `app_data`, `whatsapp_profile`). The README documents simple, portable backup/restore commands.

### Can I expand the lookback window or add folders?

Yes. The default lookback is 30 days for performance and privacy; it’s configurable. Mail scope is Inbox & Sent for MVP and can expand later.

### Who is Kenny for?

Individuals and families who want an executive‑assistant‑style helper that is private by default, reduces coordination overhead, and never writes without approval.
