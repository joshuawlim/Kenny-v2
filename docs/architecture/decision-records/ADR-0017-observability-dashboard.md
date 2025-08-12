## ADR-0017: Phase 2 Observability Dashboard (health and value metrics)

### Status
Accepted

### Context
- Requirement: Track the agent’s health and value: messages/emails analyzed, proposals raised, approvals, calendar events created, and sync health.
- Constraint: Local-first; keep data in SQLite and expose via local UI.

### Decision
- Implement a local dashboard (Phase 2) showing:
  - Health: source sync status/lag, last successful run, error counts
  - Throughput: messages/emails analyzed per day
  - Workflow: proposals created vs approved, time-to-approval
  - Outcomes: calendar events created by Kenny
- Backed by lightweight counters and sync run records in SQLite. No external telemetry.

### Consequences
- Pros: Quantifies value and reliability; helps prioritize improvements.
- Cons: Requires emitting counters and maintaining small rollups.

### Implementation Notes
- Tables: `sync_runs`, `metrics_counters_daily` (see data model).
- Emit counters from workers and API at key points (post-sync, post-classification, post-approval, post-event-create).
- UI: `/dashboard` with charts and status panels; export CSV.
