# Architecture

This directory centralizes design knowledge and decisions for Kenny v2. It follows a pragmatic, documentation-as-code approach.

### Contents
- `architecture-principles.md`: Guiding principles
- `non-functional-requirements.md`: Quality attributes (NFRs)
- `security-posture.md`: Local-first security posture and threat model
- `decision-records/`: Architecture Decision Records (ADRs)
- `templates/`: ADR and Module Spec templates
- `diagrams/`: C4-style diagrams (Mermaid)
- `data-model.md`: Tables and schemas for MVP
- `module-specs/`: Module specifications
  - `multi-agent-architecture.md`: Coordinator-led multi-agent spec
  - `implementation-plan.md`: Migration plan to multi-agent system
  - `etl-mail.md`: Mail ETL design (Inbox & Sent) - **IMPLEMENTED**
  - `memory-learning.md`: Memory and learning loop - **PLANNED**
  - `web-whitelist-access.md`: Whitelisted website access - **PLANNED**
  - `contacts-knowledge.md`: Contacts knowledge base - **PLANNED**
  - `dashboard.md`: Observability dashboard - **PLANNED**
  - `search-and-embeddings.md`: Local embeddings and hybrid search - **PLANNED**

### Process
1. Capture significant decisions as ADRs.
2. Keep diagrams current with changes.
3. For new/changed modules, add or update a Module Spec.
4. Keep security allowlists and egress rules in ADRs up to date (see `ADR-0012`).

### C4 Mapping
- Context: System scope and external actors (`diagrams/context.mmd`)
- Container: Deployable/runtime units (`diagrams/container.mmd`)
- Component: Internal components and interfaces (add `component-*.mmd` as needed)
- Data: Logical data model (`diagrams/data.mmd`)

### Conventions
- Diagrams are Mermaid `.mmd` files.
- Reference files and modules using backticks and repository-relative paths.
- Prefer clear, high-verbosity prose with precise terminology.
