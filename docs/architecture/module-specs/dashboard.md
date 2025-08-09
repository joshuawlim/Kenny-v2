## Module Spec: Observability Dashboard (Phase 2)

### Purpose
Provide a local dashboard for health and value metrics.

### Scope (Phase 2)
- Health: per-source sync status, last run, lag, errors
- Value: messages/emails analyzed, proposals created/approved, events created
- Trends: daily counters (last 30/90 days)
 - Component health: Ollama (:11434), Bridge (:5100), Postgres (:5432)
 - Toggles: Image Processing (default OFF) and a global kill switch; both persisted locally
 - Egress/Audit pane: show current allowlist and recent audit entries (image processing logs when enabled)

### Data Sources
- `sync_runs`
- `metrics_counters_daily` (name, date, value)

### Emitted Counters (examples)
- `messages_analyzed_total`
- `emails_analyzed_total`
- `proposals_created_total`
- `proposals_approved_total`
- `events_created_total`
- `sync_errors_total{source}`

### UI
- Route: `/dashboard`
- Panels: Health (per source), Value (KPIs), Trends (charts), Export CSV, Component Health, Egress/Audit, Toggles

### Config
- `DASHBOARD_ENABLED=false` (toggle)
- `METRICS_RETENTION_DAYS=180`
 - `IMAGE_PROCESSING_ENABLED=false` (global, default OFF)


