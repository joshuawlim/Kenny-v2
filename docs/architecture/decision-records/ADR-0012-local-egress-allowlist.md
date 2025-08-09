## ADR-0012: Local egress allowlist and enforcement

### Status
Accepted

### Context
- Hard requirement: run as much as possible locally for data security and privacy.
- The system should not communicate with external services except where strictly necessary for functionality.

### Decision
- Adopt an outbound egress allowlist policy for all services:
  - `http://host.docker.internal:11434` (Ollama on host)
  - `http://host.docker.internal:5100` (macOS Bridge on host)
  - `https://web.whatsapp.com` (only if WhatsApp sync is enabled)
- Recommend users enforce allowlist via macOS firewall or Little Snitch profiles. Document the allowlist in README.
- Prohibit third-party telemetry and analytics by default.

### Consequences
- Pros:
  - Predictable, auditable network behavior aligned with local-first.
  - Reduced data exfiltration risk.
- Cons:
  - Slight setup friction for users who choose to enforce OS-level rules.
  - Future optional connectors (e.g., WhatsApp Business API) must be explicitly documented as non-local exceptions.

### Implementation Notes
- Keep allowlist visible in `README.md` and infra docs.
- Feature flags for networked modules must default to off (e.g., `WHATSAPP_ENABLE_SENDING=false`).
- If future hybrid options are added, create a dedicated ADR that lists the additional egress domains and rationale.


