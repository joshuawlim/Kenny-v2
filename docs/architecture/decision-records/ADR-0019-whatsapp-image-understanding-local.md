## ADR-0019: WhatsApp image understanding (local-only, infra hooks)

### Status
Accepted — Sprint 1 adds infra hooks (schema, Postgres, toggles, health); extraction remains disabled by default.

### Context
- WhatsApp images (screenshots, invites) often contain commitments and actionable data.
- We need local-only extraction with strong auditability and zero egress, consistent with ADR-0012 (egress allowlist) and the local-first security posture.

### Decision
- Introduce a local pipeline for media handling:
  - Store image files on disk with checksums.
  - Persist attachment and extraction metadata in Postgres (localhost-only).
  - Use local OCR/vision tools only. Image processing is opt-in and disabled by default.
- Keep core app records in SQLite; use Postgres specifically for richer metadata around attachments/extractions.
- Bind Postgres to localhost; no external exposure.
- Add an audit trail recording extractor name, timestamps, attachment/message ids, and file paths touched.

### Consequences
- Pros: better provenance, structured extraction path, future extensibility for multimodal.
- Cons: adds Postgres dependency and compute overhead when enabled; cross-store links (SQLite ↔ Postgres) are app-enforced.

### Implementation Notes (Sprint 1)
- Infra:
  - Add Postgres in docker-compose with a local volume and healthcheck; expose 5432 on localhost only.
  - Add config toggles: `IMAGE_PROCESSING_ENABLED=false` (default OFF), `ATTACHMENTS_DIR=/data/attachments`.
  - UI: show health for Ollama (:11434), Bridge (:5100), and Postgres (:5432). Provide an Image Processing toggle (OFF) and a global kill switch. Show an egress/audit pane (expected empty initially).
- ETL (WhatsApp):
  - Capture attachment metadata and persist files locally during ingestion.
  - Queue images for extraction (no-op when `IMAGE_PROCESSING_ENABLED=false`).
- Search: remain text-only (messages + agent_messages). Prepare to include `extractions.text` later.
- Security & Audit: reiterate zero egress; log extractor activity locally only.

### Alternatives Considered
- Store everything in SQLite: simpler, but Postgres chosen for richer metadata patterns and potential job orchestration needs.


