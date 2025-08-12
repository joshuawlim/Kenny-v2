## Kenny v2

This repository uses a lightweight architecture governance approach so that design decisions are explicit, versioned, and easy to evolve.

### Architecture Docs
- See `docs/architecture/` for:
  - Principles and non-functional requirements (NFRs)
  - Architecture Decision Records (ADRs)
  - C4 diagrams
  - Module specifications and templates
  - Multi‑agent architecture spec and implementation plan (`docs/architecture/multi-agent-architecture.md`, `docs/architecture/implementation-plan.md`)

### How we make architecture decisions
1. Create an ADR using the template in `docs/architecture/templates/adr-template.md`.
2. Link the ADR in your PR and summarize the change in the PR description.
3. Update diagrams/specs under `docs/architecture/` as needed.

### Contributing to architecture
- Propose changes via ADRs.
- Keep module boundaries and interfaces documented using the module spec template.
- Update diagrams with each significant change.



### Getting Started (MVP - local only)
Prereqs on macOS (host):
- Docker Desktop
- Ollama (`brew install ollama`; then `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text`)
- Python 3.11+, Xcode Command Line Tools

Permissions (System Settings → Privacy & Security):
- Grant Full Disk Access, Accessibility, and Automation to your terminal/editor and the macOS Bridge app when prompted.

Bring-up sequence:
1) Run Ollama on host: it listens on `http://localhost:11434` by default.
2) Start the macOS Bridge (host) at `http://localhost:5100` (see `docs/architecture/module-specs/macos-bridge.md`).
3) Compose services:
   ```bash
   cd infra
   docker compose up --build
   ```
4) Open `http://localhost:8080` for the Web UI. Chat with the agent at `/chat` (local Web Chat). WhatsApp chat remains read-only in MVP.

Note: The system is being refactored to a coordinator‑led multi‑agent architecture. Current services (`services/api`, `services/workers`, `services/ui`) remain functional during migration. See the multi‑agent docs for the target design and migration phases.

WhatsApp (read-only) pairing (once):
- The workers will guide a one-time QR scan for WhatsApp Web and persist the session to a Docker volume (`whatsapp_profile`).

See ADRs for design choices:
- `docs/architecture/decision-records/ADR-0002-whatsapp-readonly.md`
- `docs/architecture/decision-records/ADR-0003-ollama-local-llm.md`
- `docs/architecture/decision-records/ADR-0004-apple-mail-readonly.md`
- `docs/architecture/decision-records/ADR-0005-mail-scope-inbox-sent.md`
- `docs/architecture/decision-records/ADR-0007-calendar-approval.md`
- `docs/architecture/decision-records/ADR-0008-conversational-channels.md`
- `docs/architecture/decision-records/ADR-0009-agent-persona-kenny-and-local-chat-history.md`
- `docs/architecture/decision-records/ADR-0010-whatsapp-two-way-local-web-first.md`
- `docs/architecture/decision-records/ADR-0011-imessage-two-way-phase-2.md`
- `docs/architecture/decision-records/ADR-0012-local-egress-allowlist.md`
- `docs/architecture/decision-records/ADR-0014-memory-learning.md`
- `docs/architecture/decision-records/ADR-0015-website-whitelist-access.md`
- `docs/architecture/decision-records/ADR-0016-contacts-knowledge-base.md`
- `docs/architecture/decision-records/ADR-0017-observability-dashboard.md`
- `docs/architecture/decision-records/ADR-0018-default-conversation-channel-whatsapp.md` (Default is now Web Chat; see ADR for details)
- `docs/architecture/decision-records/ADR-0019-whatsapp-image-understanding-local.md`
- `docs/architecture/decision-records/ADR-0020-storage-architecture-local-sqlite-plus-postgres-media.md`
- `docs/architecture/decision-records/ADR-0021-multi-agent-architecture.md`
- `docs/architecture/decision-records/ADR-0022-orchestration-framework-langgraph.md`
- `docs/architecture/decision-records/ADR-0023-agent-manifest-and-registry.md`

Mail scope (MVP): Inbox and Sent only; bodies fetched on-demand for recent emails.

Default scan window: last 30 days for Mail, iMessage, and WhatsApp. Configure via env in `infra/docker-compose.yml`.

Calendar writes require approval:
- The agent will propose events, and you approve them in the UI before any write occurs (see `ADR-0007`).
- You can optionally set `CALENDAR_DEFAULT_CALENDAR_ID` to suggest a target calendar during approval.

Agent persona and chat:
- Default persona name is "Kenny" (`AGENT_PERSONA_NAME`).
- Agent chat history is stored locally and searchable in the Web UI.
  - Default conversational channel can be chosen later (Phase 2) via `AGENT_DEFAULT_CHANNEL=web|telegram|whatsapp|imessage`. Web Chat is the default and primary in MVP.
  - For WhatsApp agent chat (when send is enabled in Phase 2), you can set one of:
    - `WHATSAPP_AGENT_CONTACT` (1:1 chat; phone or saved contact name)
    - `WHATSAPP_AGENT_THREAD_NAME` (group chat name). Leave both empty to choose in the Settings UI later.

### Egress control (local-only)
By default, services operate without external egress except where strictly required.

- Allowlist outbound network traffic to:
  - `http://host.docker.internal:11434` (Ollama on host)
  - `http://host.docker.internal:5100` (macOS Bridge on host)
  - `https://web.whatsapp.com` (only if WhatsApp sync is enabled)
  - Any sites in `WHITELISTED_SITES` for the website access worker

### Feature toggles (Phase 2)
- Learning loop: `LEARNING_ENABLED=false` by default. Enable later via settings or env.
- Website access worker: leave `WHITELISTED_SITES` empty for now; add domains later and ensure `EGRESS_ALLOWLIST` is updated.
- Recommended: enforce with macOS firewall rules or Little Snitch and keep this list in sync with `ADR-0012`.

### Backups and restore (local data)
Local data is stored in Docker volumes:
- `app_data` (SQLite DBs), `whatsapp_profile` (WhatsApp Web session)

Backup (platform-agnostic via a helper container). Replace `<APP_DATA_VOL>` and `<WA_PROFILE_VOL>` with your actual volume names from `docker volume ls` (they are usually `<project>_app_data` and `<project>_whatsapp_profile`):
```bash
cd infra
docker compose stop
# Backup app_data
docker run --rm -v <APP_DATA_VOL>:/data -v "$(pwd)":/backup alpine sh -c "cd /data && tar -czf /backup/app_data.tgz ."
# Backup whatsapp_profile
docker run --rm -v <WA_PROFILE_VOL>:/data -v "$(pwd)":/backup alpine sh -c "cd /data && tar -czf /backup/whatsapp_profile.tgz ."
```

Restore:
```bash
cd infra
docker compose down
docker run --rm -v <APP_DATA_VOL>:/data -v "$(pwd)":/backup alpine sh -c "cd /data && tar -xzf /backup/app_data.tgz"
docker run --rm -v <WA_PROFILE_VOL>:/data -v "$(pwd)":/backup alpine sh -c "cd /data && tar -xzf /backup/whatsapp_profile.tgz"
docker compose up -d
```

### Observability (MVP)
- Health endpoints: API, workers, and Bridge expose `/health`.
- Suggested metrics: sync counts/lag per source, proposal throughput, Ollama latency, Bridge error rates. See module specs for details.

### Dashboard (Phase 2)
- Local dashboard at `/dashboard` (toggle via `DASHBOARD_ENABLED`).
- Shows health (sync status/lag), throughput (analyzed/day), workflow (proposals vs approvals), and outcomes (events created).

Future option (hybrid WhatsApp):
- You can later provision a separate WhatsApp Business API number for Kenny. In that model, the system reads your personal WhatsApp locally via Web automation and sends external messages via the Business API connector (cloud), with clear routing rules and explicit opt-in.

