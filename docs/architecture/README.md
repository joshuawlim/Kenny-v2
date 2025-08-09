## Architecture

This directory centralizes design knowledge and decisions for Kenny v2. It follows a pragmatic, documentation-as-code approach.

### Contents
- `architecture-principles.md`: Guiding principles
- `non-functional-requirements.md`: Quality attributes (NFRs)
- `security-posture.md`: Local-first security posture and threat model
- `decision-records/`: Architecture Decision Records (ADRs)
- `templates/`: ADR and Module Spec templates
- `diagrams/`: C4-style diagrams (Mermaid)
 - `data-model.md`: Tables and schemas for MVP
 - `module-specs/etl-mail.md`: Mail ETL design (Inbox & Sent)
  - `module-specs/memory-learning.md`: Memory and learning loop
  - `module-specs/web-whitelist-access.md`: Whitelisted website access
  - `module-specs/contacts-knowledge.md`: Contacts knowledge base
  - `module-specs/dashboard.md`: Observability dashboard
  - `module-specs/search-and-embeddings.md`: Local embeddings and hybrid search

### Process
1. Capture significant decisions as ADRs.
2. Keep diagrams current with changes.
3. For new/changed modules, add or update a Module Spec.
4. Keep security allowlists and egress rules in ADRs up to date (see `ADR-0012`).

### C4 Mapping
- Context: System scope and external actors (`diagrams/context.mmd`)
- Container: Deployable/runtime units (add `container.mmd` when ready)
- Component: Internal components and interfaces (add `component-*.mmd` as needed)

### Conventions
- Diagrams are Mermaid `.mmd` files.
- Reference files and modules using backticks and repository-relative paths.
- Prefer clear, high-verbosity prose with precise terminology.


