## ADR-0015: Whitelisted website access (local, restricted egress)

### Status
Accepted

### Context
- Requirement: Kenny should access a set of approved websites (e.g., school parent portals) to fetch schedules/announcements for planning.
- Constraints: Local-first, restrict outbound egress to an allowlist (see ADR-0012 local egress allowlist).

### Decision
- Add a local headless browser worker (Playwright) that only connects to allowlisted domains.
- Credentials managed locally (macOS Keychain preferred; fallback to `.env` with caution).
- Fetched pages are cached locally and parsed into structured entries for downstream use.

### Consequences
- Pros: Enables planning with relevant external info while keeping tight control of egress.
- Cons: Website changes may break parsers; requires maintenance.

### Implementation Notes
- Configuration: `WHITELISTED_SITES` (comma-separated domains/URLs), `EGRESS_ALLOWLIST` aligned with ADR-0012.
- Worker features: login flows, session persistence per site, scheduled fetch windows, HTML snapshot archiving for auditability.
- Privacy: store minimal necessary data; redact PII not needed for planning.


