# Kenny v2 · Development Status

Date: 2025-08-09

Current state

- Local stack runs via `docker compose -f infra/docker-compose.yml up -d` and serves UI at <http://localhost:8080>
- API provides status, kill switch, egress audit, and mail endpoints; SQLite schema created in container volume
- UI shows components, kill switch, egress audit, and Inbox triage with Sync Inbox/Sent and auto-refresh
- Bridge stub running on macOS host exposes `/health` and `/v1/mail/messages` with fake data
- Containers can reach the Bridge via `host.docker.internal` mapping

How to run

- Start stack: `docker compose -f infra/docker-compose.yml up -d`
- Start Bridge stub: `cd bridge && . .venv/bin/activate && .venv/bin/uvicorn app:app --host 127.0.0.1 --port 5100`
- Open UI: <http://localhost:8080> → click "Sync Inbox/Sent"

Next steps

- UI: add error banners when Bridge/API unreachable; surface sync counts/timestamps
- Bridge: replace stub with real Apple Mail read-only; paginate and enforce 30‑day window
- After Mail: add WhatsApp read-only ingestion toggle (Sprint 3)

Notes

- Local-first only; egress limited to allowlist (Ollama, Bridge); calendar writes gated by approval (future)