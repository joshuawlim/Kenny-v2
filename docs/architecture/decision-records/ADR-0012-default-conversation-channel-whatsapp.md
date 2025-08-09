## ADR-0012: Default conversational channel is WhatsApp (Phase 2)

### Status
Accepted

### Context
- The user wants Kenny to act as a Management Assistant reachable by others, so WhatsApp is the preferred channel once sending is enabled.
- MVP remains local Web Chat only; WhatsApp is read-only initially (ADR-0002, ADR-0010 for two-way plan).

### Decision
- Set default conversational channel to WhatsApp when two-way messaging is enabled (Phase 2). Web Chat remains available.
- Reuse the user's main WhatsApp account and designate a specific chat/thread for agent conversations with Kenny.
 - For now, use a 1:1 chat with Kenny. Later, optionally switch to a dedicated WhatsApp number for Kenny to operate more autonomously.

### Consequences
- External contacts can message Kenny over WhatsApp (subject to the chosen two-way mechanism). This enables workflows like calendar requests from others.
- Requires robust duplication/exclusion handling so agent chats are not triaged as general messages (see ADR-0008).

### Implementation Notes
- Configuration:
  - `AGENT_DEFAULT_CHANNEL=whatsapp`
  - Identify the agent’s WhatsApp thread via one of:
    - `WHATSAPP_AGENT_CONTACT` (phone or saved contact name) for a 1:1 chat, or
    - `WHATSAPP_AGENT_THREAD_NAME` (group/chat name) for a small group.
  - Alternatively, select the thread from a detected chat list in the Settings UI; the system will persist the resolved `thread_external_id`.
  - Current recommendation: set `WHATSAPP_AGENT_CONTACT` and leave `WHATSAPP_AGENT_THREAD_NAME` empty.
- Worker logic:
  - Detect agent-addressed WhatsApp messages (designated thread or messages starting with the agent name, e.g., "Kenny,") and mark them as agent channel.
  - Route such messages to the chat pipeline and proposal creation, not to general triage.

#### Future Option: Dedicated Number
- Provision a separate WhatsApp number for Kenny and pair it for Web automation to avoid mixing personal and agent conversations. This can simplify detection and reduce duplication.


