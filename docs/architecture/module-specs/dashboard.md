## Module Spec: Observability Dashboard (Phase 2)

### Purpose
Provide a local dashboard for health and value metrics.

### Scope (Phase 2)
- Health: per-source sync status, last run, lag, errors
- Value: messages/emails analyzed, proposals created/approved, events created
- Trends: daily counters (last 30/90 days)

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
- Panels: Health (per source), Value (KPIs), Trends (charts), Export CSV

### Config
- `DASHBOARD_ENABLED=false` (toggle)
- `METRICS_RETENTION_DAYS=180`


