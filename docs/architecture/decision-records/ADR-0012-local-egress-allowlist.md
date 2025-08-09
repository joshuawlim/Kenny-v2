# ADR-0012: Deny-by-default network egress with explicit allowlist

Date: 2025-08-09
Status: Proposed

## Context
To uphold privacy and minimize data leakage risks, the system should operate locally by default and only communicate externally when strictly necessary and explicitly allowed.

## Decision
- Enforce deny-by-default for all outbound network egress from Kenny v2 components.
- Maintain a minimal, versioned allowlist of approved destinations (domains or IPs) required for core functionality.
- Log egress decisions locally (allowed/blocked) with minimal, non-sensitive metadata to support auditing.
- Changes to the allowlist require an ADR or PR review with explicit justification.

## Consequences
- Strong privacy posture and reduced risk of accidental data exfiltration.
- Additional effort to onboard new integrations (must be justified and allowlisted).
- Operational clarity: any unexpected egress attempts are blocked and visible.

## Alternatives Considered
- Permit-by-default with monitoring: Simpler initially, but higher risk and harder to audit.
- Per-service bespoke rules: Harder to reason about globally, invites drift.

## References
- docs/architecture/security-posture.md
- ADR-0007: Calendar actions require explicit human approval
- ADR-0018: Default WhatsApp channel for approvals