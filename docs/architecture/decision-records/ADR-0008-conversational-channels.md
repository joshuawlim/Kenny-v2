# ADR-0008: Conversational channels and duplication exclusion


## Status
Accepted


## Context
- The user prefers interacting with the agent as a conversational assistant (e.g., Management Assistant/Chief of Staff).
- Core constraint: local-first architecture on macOS.
- MVP should provide a local web chat that requires no external services or platform permissions.
- Optional channels can be considered later, including Telegram, iMessage, and WhatsApp (with caveats: ToS/fragility for WhatsApp Web automation; cloud tradeoffs for Business API).


## Decision
- Primary conversation channel (default): local Web Chat (served at `http://localhost:8080`).
- Optional channels (disabled by default): Telegram, iMessage (via macOS Bridge), and WhatsApp.
  - WhatsApp two-way is out-of-scope for MVP; revisit in Phase 2 with explicit risk acceptance:
    - Option A (local, higher ToS risk): WhatsApp Web automation for sending (headless browser).
    - Option B (cloud, non-local): WhatsApp Business API via a BSP (opt-in only; isolated connector).
- Exclude agent conversations from analytics/triage to avoid duplication. Conversations with the agent are flagged and filtered out from message triage and insights.


## Consequences
- Users can converse via the Web Chat immediately without changing messaging apps.
- Clear path exists to add Telegram/iMessage/WhatsApp later without changing the default UX.
- WhatsApp remains read-only for MVP, reducing risk and complexity.
- Clear exclusion rules prevent agent-chat loops and duplicate insights.


## Implementation Notes
- Web Chat UI at `/chat`, backed by the Agent API. Conversation state stored locally in SQLite.
- Add flags/columns to mark messages as `is_agent_channel` and/or `exclude_from_automation`.
- iMessage channel (Phase 2): add send endpoint in Bridge and map a dedicated thread; mark that thread as excluded from triage.


