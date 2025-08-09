## ADR-0009: Agent persona name “Kenny” and local searchable chat history

### Status
Accepted

### Context
- The user wants the conversational agent to present itself as “Kenny.”
- All agent chat history should be stored locally and be searchable via the Web UI.
- This aligns with the local-first privacy constraint.

### Decision
- Set default persona name to “Kenny.”
- Persist all agent chat conversations/messages locally and make them searchable in the Web UI.
- Exclude agent chat from automation/triage of external messages to prevent duplication (see ADR-0008).

### Consequences
- Consistent UX and branding for the agent.
- Users can retrieve past decisions and context via local search.
- Storage growth over time; acceptable for MVP, can add retention later if desired.

### Implementation Notes
- Configuration: `AGENT_PERSONA_NAME=Kenny` provided to API/UI.
- Data model: use `agent_conversations` and `agent_messages` tables; optional FTS for message content.
- Security/Privacy: chat content stays on device; no cloud sync.


