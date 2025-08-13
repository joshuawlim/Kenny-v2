# ADR-0018: Default conversation channel for approvals is Web Chat

Date: 2025-08-09
Status: Accepted

## Context
We need a reliable, user-friendly channel to converse with the Coordinator agent ("Kenny") and to request/capture explicit approvals (e.g., calendar events). To preserve privacy and simplicity, the default experience should be entirely local and web-based, while keeping options open to adopt native chat channels later.

## Decision
- Use the local Web Chat as the default conversation channel for interacting with Kenny and for approvals.
- Preserve future options to enable other channels (opt-in), including Telegram, WhatsApp, and iMessage. These are disabled by default and must comply with the egress allowlist and approval policies.
- For Phase 2 and beyond, the user can choose a preferred channel via configuration, but the system ships with Web Chat as default.

## Consequences
- Web Chat provides a consistent, local-first UX with no additional platform permissions.
- Optional channels introduce integration complexity and duplication risks; they remain off by default and require clear routing and deduplication rules when enabled.

## Alternatives Considered
- macOS notifications: Platform-specific and not chat-centric.
- Email: Asynchronous and slower feedback loop compared to chat.

## References
- ADR-0007: Require explicit human approval for calendar actions
- ADR-0012: Deny-by-default network egress with explicit allowlist
- docs/architecture/security-posture.md