## ADR-0011: iMessage two-way chat in Phase 2 (local-only)

### Status
Accepted

### Context
- The user wants conversational interaction with the agent. iMessage is available locally via Messages.app.
- We already read iMessage from `chat.db`. Sending requires AppleScript integration with Messages.

### Decision
- Implement iMessage sending in Phase 2 via the macOS Bridge using AppleScript to send messages to a designated thread or handle.
- Maintain full local execution (no external services).

### Consequences
- Provides a robust, fully local conversational channel.
- Requires Accessibility/Automation permissions and careful AppleScript error handling.

### Implementation Notes
- Bridge endpoints (Phase 2):
  - `POST /v1/messages/imessage/send` → `{ handle, text }` or `{ thread_id, text }`
- Exclusion: mark the agent’s iMessage thread as `is_agent_channel=1` and `exclude_from_automation=1`.
- UI: allow the user to pick iMessage or Web Chat as the default channel to talk to Kenny.


