## ADR-0013: WhatsApp hybrid option – read locally via Web, write via Business API (optional)

### Status
Proposed (for future use)

### Context
- The user may later provision a separate WhatsApp number for Kenny to operate autonomously.
- Local-first constraint applies to the core system, but robust outbound messaging to third parties can be handled via WhatsApp Business API if explicitly accepted.

### Decision
- Offer an optional hybrid mode:
  - Read personal messages from the user’s main WhatsApp account locally via WhatsApp Web automation (no cloud dependency).
  - Send outbound messages to external parties using a separate WhatsApp Business API account/number (cloud-based), isolated in a connector service.

### Consequences
- Maintains privacy for inbound personal data (local read) while providing robust delivery for outbound communications.
- Requires accepting cloud processing for outbound messages and hosting a webhook/connector.

### Implementation Notes
- Connector: a small service (could be separate repo) to receive API requests from the local Agent API and call the Business API.
- Exposure: secure public endpoint (e.g., Tailscale Funnel or Cloudflare Tunnel) for Business API webhooks.
- Mapping: store a mapping between local contacts and Business API identities; ensure messages to the user’s own personal WhatsApp are not routed via Business API.
- Configuration flags to enable hybrid mode and route channels accordingly.
