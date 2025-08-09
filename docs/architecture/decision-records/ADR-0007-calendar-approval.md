## ADR-0007: Calendar event creation requires explicit user approval

### Status
Accepted

### Context
- The user’s default calendar is shared. Automatically writing events could create noise or leak tentative plans.
- The agent proposes events based on messages/emails and should only create them after confirmation.

### Decision
- All calendar writes require explicit user approval in the UI (or other approval channel) before calling the Bridge to create the event.
- The system should support choosing the target calendar per event. A default target calendar can be configured but approval still applies.

### Consequences
- Safer user experience with no unintended calendar writes.
- Slightly higher interaction cost; mitigated by a streamlined “Approve & Create” flow.

### Implementation Notes
- UI: An Approvals queue shows proposed events with title, time, attendees, source message, and a confidence/reason.
- API: Only on approval does the API call `POST /v1/calendar/events` on the macOS Bridge with an explicit `calendar_id`.
- Settings: `CALENDAR_REQUIRE_APPROVAL=true`. Optional `CALENDAR_DEFAULT_CALENDAR_ID` to suggest a calendar at approval time.


