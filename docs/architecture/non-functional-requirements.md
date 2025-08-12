# Non-Functional Requirements (NFRs)

Target quality attributes for the MVP. Update as measurements are gathered.

- Performance
  - API `POST /v1/chat`: p95 end-to-first-token ≤ 1.8s with `llama3.1:8b` on M4 Pro; p95 full-turn ≤ 6s for 200-token completion.
  - Bridge endpoints (read): p95 ≤ 500ms for contacts/calendar list; p95 ≤ 2s for paged mail batch (100 items).
  - Workers sync cycle: complete incremental sync per source within 2 minutes at idle load.
- Throughput
  - Sustain 5 concurrent chat sessions locally without degradation beyond 20% over performance targets.
- Availability
  - Single-user local mode; target ≥ 99% daily uptime of API/Bridge while running.
- Reliability
  - Zero data loss for accepted writes (proposals, approvals). ETL idempotent with at-least-once upserts.
- Security & Privacy
  - Local-only by default. Outbound egress restricted to allowlist (see ADR-0012) and OS firewall recommended.
  - No third-party telemetry. Secrets stored locally; no cloud sync.
- Scalability
  - Support growth to 100k `messages` rows and 50k `agent_messages` with p95 search ≤ 300ms using SQLite FTS/VSS.
- Observability
  - Health endpoints on API, workers, Bridge. Emit counters: sync fetched/upserts/errors, proposals created/approved, LLM latency histograms.
- Maintainability
  - Docs kept in ADRs and module specs. Lint passes clean. Clear module boundaries.
- Portability
  - macOS host required for Bridge permissions. Containers otherwise portable; Ollama on host.
