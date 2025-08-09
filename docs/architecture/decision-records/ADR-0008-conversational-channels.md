## ADR-0008: Conversational channels and duplication exclusion

### Status
Accepted

### Context
- The user prefers interacting with the agent as a conversational assistant (e.g., Management Assistant/Chief of Staff).
- Preference order: WhatsApp chat is ideal; macOS notifications not desired. Web chat is acceptable.
- Core constraint: local-first architecture on macOS.
- MVP for WhatsApp is read-only (ADR-0002). Two-way WhatsApp automation carries ToS and maintenance risk; WhatsApp Business API involves cloud vendors.

### Decision
- Primary conversation channel for MVP: local Web Chat (served at `http://localhost:8080`).
- Optional local channel (Phase 2): iMessage chat via macOS Bridge (send/receive). This remains fully local.
- WhatsApp two-way chat is out-of-scope for MVP. It can be revisited in Phase 2 with explicit risk acceptance:
  - Option A (local, higher ToS risk): WhatsApp Web automation for sending (headless browser).
  - Option B (cloud, violates local-only): WhatsApp Business API via a BSP (not recommended for this project’s constraint).
- Exclude agent conversations from analytics/triage to avoid duplication. Conversations with the agent are flagged and filtered out from message triage and insights.

### Consequences
- Users can converse via the web chat immediately without changing messaging apps.
- A path exists for fully local iMessage chat later.
- WhatsApp remains read-only for MVP, reducing risk and complexity.
- Clear exclusion rules prevent agent-chat loops and duplicate insights.

### Implementation Notes
- Web Chat UI at `/chat`, backed by the Agent API. Conversation state stored locally in SQLite.
- Add flags/columns to mark messages as `is_agent_channel` and/or `exclude_from_automation`.
- iMessage channel (Phase 2): add send endpoint in Bridge and map a dedicated thread; mark that thread as excluded from triage.


