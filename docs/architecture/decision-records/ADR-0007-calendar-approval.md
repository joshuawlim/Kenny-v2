# ADR-0007: Require explicit human approval for calendar actions

Date: 2025-08-09
Status: Proposed

## Context
Calendar events can expose sensitive information (titles, attendees, locations) and can create workflow disruptions if created or modified without the owner's consent. We need a trustworthy, user-centered mechanism that preserves privacy and avoids accidental changes.

## Decision
- All calendar actions (create, modify, delete) require explicit human approval from the calendar owner before the action is executed.
- Approval requests are presented with a concise, reviewable summary (title, time window, participants, location/medium, organizer) and a clear approve/decline option.
- The default approval conversation channel is WhatsApp when available. If unavailable, fall back to the local web chat. iMessage support will arrive in a future phase.
- The system MUST NOT auto-create or auto-modify calendar events without prior approval.
- Approvals are recorded locally with minimal metadata sufficient for audit (what, when, result) and no third-party transmission beyond the selected approval channel.

## Consequences
- Slightly slower end-to-end flow for event creation, but significantly improved trust and correctness.
- Clear user control reduces accidental or undesired calendar changes.
- Requires lightweight approval UX and reliable message delivery on the chosen channel(s).

## Alternatives Considered
- Auto-create then notify: Faster but violates principle of explicit approval and risks trust.
- macOS notifications-only: Platform-specific, less consistent with multi-channel conversational approvals.

## References
- ADR-0018: Default conversation channel is WhatsApp for approvals
- ADR-0012: Local egress allowlist (deny-by-default, privacy-preserving)
- docs/architecture/security-posture.md