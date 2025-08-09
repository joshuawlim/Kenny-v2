## ADR-0005: Mail scope limited to Inbox and Sent (MVP)

### Status
Accepted

### Context
The user confirmed Apple Mail is the primary client and approved limiting sync to Inbox and Sent to keep the MVP focused and performant.

### Decision
Only synchronize messages from the Inbox and Sent mailboxes. Other folders/labels are out of scope for MVP.

### Consequences
- Simpler ETL and lower runtime cost.
- Reduced permissions prompts and AppleScript workload.
- Some messages in other folders will not appear until scope expands.

### Implementation Notes
- Configure workers with `MAIL_SYNC_MAILBOXES=Inbox,Sent`.
- Expose mailbox parameter in Bridge endpoint (`mailbox=`) and validate allowed values.


