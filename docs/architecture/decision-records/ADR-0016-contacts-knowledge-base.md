## ADR-0016: Contacts knowledge base (occupations, family, birthdays, interests)

### Status
Accepted

### Context
- Requirement: Kenny should maintain a richer contacts knowledge base to support executive-assistant workflows.
- Base contacts are sourced from macOS Contacts; enrichment should come from messages/emails and user edits.

### Decision
- Extend the local schema to include birthdays, relationships, occupations, and interests with provenance and confidence.
- Use message/email extraction (NER via LLM) and user confirmations to populate/curate the knowledge base.

### Consequences
- Pros: Better context for scheduling and prioritization; enables reminders (birthdays) and personalized proposals.
- Cons: Requires deduplication and conflict resolution across sources.

### Implementation Notes
- Add tables: `contact_relations`, `contact_enrichment`, `knowledge_sources`.
- UI: allow quick edits/confirmations and show provenance for each attribute.
- Privacy: stays local; export/import optional later.


