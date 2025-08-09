## Security Posture

This document defines the baseline security principles and controls for Kenny v2.

### Principles
- Local-first by default: process and store data locally whenever feasible.
- Least privilege: components only have the minimum access they need.
- Deny-by-default egress: outbound network traffic is blocked unless allowlisted (see ADR-0012).
- Explicit user approvals for sensitive actions, e.g., calendar changes (see ADR-0007).
- Privacy-by-design: minimize data collection, retain only what is necessary.

### Data Handling
- Data classes: messages, contacts, events, embeddings, metrics.
- Storage: local storage with encryption at rest where supported by the platform.
- Retention: retain only as long as needed for feature functionality; provide deletion pathways.

### Access Controls
- Separate service identities for modules; avoid shared credentials.
- Secrets management: load secrets from local secure storage; never hardcode.

### Network Egress
- Enforce allowlist per ADR-0012. Any new destination requires justification and review.
- Log allowed/blocked egress events locally with minimal metadata.

### Approvals and UX
- Calendar and similar sensitive actions require explicit user approval (ADR-0007).
- Default approval channel is WhatsApp; fallback to local web chat (ADR-0018).

### Logging and Observability
- Collect minimal necessary logs and metrics locally. Avoid sending logs off-device unless explicitly allowlisted.
- Redact sensitive fields where possible.

### Testing and Verification
- Include automated checks that fail builds if code introduces non-allowlisted egress.
- Manual review for new integrations to confirm least-privilege and approval flows.

### References
- ADR-0012: Deny-by-default network egress with explicit allowlist
- ADR-0007: Require explicit human approval for calendar actions
- ADR-0018: Default conversation channel for approvals is WhatsApp