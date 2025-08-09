# ADR-0018: Default conversation channel for approvals is WhatsApp

Date: 2025-08-09
Status: Proposed

## Context
We need a reliable, user-friendly channel to request and capture explicit approvals (e.g., calendar events). The target user primarily uses WhatsApp for quick interactions, and we aim to avoid platform-specific notification systems.

## Decision
- Use WhatsApp as the default conversation channel for sending approval requests and receiving responses.
- Fallback to the local web chat when WhatsApp is unavailable.
- iMessage will be introduced as a two-way channel in a later phase; until then, it remains read-only (where applicable).
- Keep conversations local-first. Any external API usage must comply with the egress allowlist.

## Consequences
- Faster, familiar approval UX for the user increases response rates and trust.
- Requires local WhatsApp integration and careful handling to avoid duplication across channels.

## Alternatives Considered
- macOS notifications: Platform-specific and not chat-centric.
- Email: Asynchronous and slower feedback loop compared to chat.

## References
- ADR-0007: Require explicit human approval for calendar actions
- ADR-0012: Deny-by-default network egress with explicit allowlist
- docs/architecture/security-posture.md