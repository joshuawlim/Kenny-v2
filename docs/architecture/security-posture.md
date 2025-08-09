## Security Posture (Local-First)

### Threat Model (MVP)
- Single trusted user operating on a single macOS machine.
- Primary risks: unintended data egress, over-permissioned host access, accidental writes (e.g., calendar), and fragile integrations (e.g., WhatsApp Web) leading to misbehavior.

### Principles
- Local-first by default; no cloud dependencies for core features.
- Outbound egress allowlisting (see `decision-records/ADR-0012-local-egress-allowlist.md`).
- Human-in-the-loop for any user-visible write (calendar, messaging in Phase 2).
- Least privilege for host permissions (Full Disk, Accessibility, Automation), only for the Bridge.

### Network Controls
- Allowlist the following outbound endpoints only:
  - `http://host.docker.internal:11434` (Ollama)
  - `http://host.docker.internal:5100` (macOS Bridge)
  - `https://web.whatsapp.com` (only if WhatsApp sync enabled)
- Recommend OS-level enforcement (macOS firewall, Little Snitch profiles).
 - Proxy/UI/API are bound to localhost via Caddy; no remote exposure in MVP.

### Data Handling
- SQLite databases stored in local Docker volumes (`app_data`), embeddings in `vectors.db`.
- No third-party telemetry. Logs remain local.
- Email bodies limited to recent window; attachments/media not stored in MVP.
- Optional retention knobs for agent chat and embeddings (future work).

### UI and API Security (MVP)
- Web UI and API served only on localhost via Caddy.
- Same-origin only; no remote exposure in MVP. CSRF mitigated by local-only deployment.
- If remote access is later introduced, enable CSRF tokens and session hardening.

### Auditing and Approvals
- All calendar writes gated by explicit approval in UI (see `ADR-0007`).
- Log structured audit entries for approvals with proposal id, calendar id, and result id.

### Operational Guidance
- Health endpoints on API, workers, Bridge.
- Metrics for ETL throughput, errors, and LLM latency.
- Documented backup/restore for local volumes; recommend periodic offline backups.


