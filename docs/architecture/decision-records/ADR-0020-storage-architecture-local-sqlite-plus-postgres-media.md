# ADR-0020: Storage architecture — SQLite primary; Postgres for media/extractions (optional)

Date: 2025-08-09
Status: Accepted

## Context
- MVP prioritizes local-first simplicity and portability.
- Current `docker-compose.yml` sets `DB_URL` and `VDB_URL` to SQLite files and includes a Postgres service used only when image attachments and extraction pipelines are enabled.
- `data-model.md` defines core domain tables in SQLite and places attachments/extractions in Postgres to support richer metadata and potential future orchestration.

## Decision
- Use SQLite as the primary OLTP store for all core domain data: `messages`, `proposals`, `events`, `agent_messages`, embeddings (via SQLite VSS), and operational metadata.
- Keep Postgres optional and scoped to media/extraction workloads: `attachments`, `extractions` tables. Enforce referential integrity to SQLite in the application layer only (no cross-DB foreign keys).
- Ship with Postgres enabled in Compose for forward compatibility, but allow the system to run with media processing disabled (`IMAGE_PROCESSING_ENABLED=false`) without using Postgres paths.

## Consequences
- Pros: local-first, simple ops (no external DB), easy backups (volume copy), good enough performance at MVP scale.
- Cons: cross-store consistency is app-enforced; migrations must coordinate two stores when media is enabled.

## Implementation Notes
- API (`services/api`) uses SQLite in-process. Ensure WAL mode is set and create required indices.
- Workers read/write SQLite for ETL cursors and messages; only write to Postgres when `IMAGE_PROCESSING_ENABLED=true` and attachments are present.
- Backups: document copying volumes `app_data`, `attachments`, and `pg_data` when Postgres is in use.
- Observability: emit counters for cross-store write failures; degrade gracefully if Postgres is unavailable and media processing is disabled.

## References
- `infra/docker-compose.yml`
- `docs/architecture/data-model.md`
- ADR-0019 (WhatsApp image understanding — local)