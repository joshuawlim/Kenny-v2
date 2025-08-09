## ADR-0004: Apple Mail integration (read-only via AppleScript + frameworks)

### Status
Accepted

### Context
- Requirement: The agent should access email content for triage and insights.
- Constraint: Local-only architecture on macOS with containers for the main app. Apple Mail is the user's primary client on this Mac.
- Options for data access: parsing `~/Library/Mail/V*` on-disk stores (complex and fragile), Apple Mail Scripting bridge (AppleScript), and MailKit (limited). For MVP and privacy, the most stable route is AppleScript for selective fields.

### Decision
- Use Apple Mail’s scripting dictionary (AppleScript executed from the macOS Bridge) to read metadata and, when needed, the plain-text body for recent messages.
- Start with read-only access to selected mailboxes (Inbox, Sent). Scope can expand later.
- Extract minimal fields for sync: id, thread id (conversation id), from, to/cc, subject, date, snippet, and optionally plain-text body for the last 30 days.
- Rate-limit and page results to avoid UI lockups.

### Consequences
- Pros:
  - Works with the user’s existing Apple Mail setup; no server creds stored separately.
  - Keeps parsing logic simple and privacy-preserving.
  - Robust across macOS updates compared to direct mailbox file parsing.
- Cons:
  - AppleScript calls can be slower than direct file reads.
  - Requires Accessibility/Automation permissions and can surface system prompts.

### Alternatives Considered
1) Directly read `~/Library/Mail/V*` and index: high complexity and breakage risk.
2) IMAP sync directly from mail providers: violates the principle of using the local client and requires credentials.

### Implementation Notes (MVP)
- Bridge endpoints:
  - `GET /v1/mail/messages?mailbox=Inbox&since=ISO8601&limit=500`
  - `GET /v1/mail/messages/body?id=MAIL_ID` (optional on-demand)
- ETL sync strategy:
  - Poll every 10 minutes for Inbox and Sent, last 30 days window, upsert by `id`.
  - Body fetched lazily when classification/summarization requires it.
- Privacy defaults:
  - Store headers + snippet by default; full body only when needed and for recent mail.


