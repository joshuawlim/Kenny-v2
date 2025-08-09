## ADR-0010: WhatsApp two-way – local Web automation first, Business API as fallback

### Status
Accepted

### Context
- MVP uses WhatsApp read-only via WhatsApp Web (ADR-0002). The user wants conversation with the agent and may need sending in the future.
- Priorities: robustness first, but prefer local-only. WhatsApp Business API is robust but requires cloud/webhooks and Meta processing. Web automation is local but more fragile.

### Decision
- Phase 2: implement optional sending via WhatsApp Web automation (Playwright) locally. Default disabled.
- If fragility becomes problematic, consider switching to WhatsApp Business API as a non-local exception (explicitly documented and opt-in).

### Consequences
- Keeps solution local-first with a clear escape hatch.
- Requires maintenance when WhatsApp Web changes UI; mitigated by selector versioning and tests.

### Implementation Notes
- Config flags:
  - `WHATSAPP_ENABLE_SENDING=false` (default)
  - `WHATSAPP_SYNC_LOOKBACK_DAYS=30`
  - `WHATSAPP_SYNC_INTERVAL_MINUTES=10`
- Safeguards:
  - Confirm recipient/thread before send; dry-run preview in Web UI.
  - Mark agent conversation thread and exclude from triage (ADR-0008).
- Fallback path:
  - If adopted, Business API requires a public webhook endpoint, number provisioning, and cloud processing. Not local-only; would be isolated in a connector service.


