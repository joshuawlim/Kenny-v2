# ADR-0001: Adopt lightweight architecture process (ADRs + C4 + Module Specs)

Date: 2025-08-09
Status: Proposed

## Context
We need a pragmatic way to align code with architecture as Kenny v2 evolves. Decisions should be explicit, reviewable, and easy to change.

## Decision
- Use Architecture Decision Records (ADRs) stored under `docs/architecture/decision-records/` with incremental numbering.
- Maintain C4-style diagrams in `docs/architecture/diagrams/` using Mermaid.
- Require a Module Specification for any new/changed module with external interfaces.
- Link ADRs and updated diagrams/specs in related PRs.
- Numbering is monotonically increasing; if conflicts occur (duplicate numbers), keep both files and rely on titles. Supersession must be explicit via a "Status: Superseded by ADR-XXXX" note in the older ADR.

## Consequences
- Lightweight governance adds small overhead but improves clarity and onboarding.
- Clear interfaces and diagrams reduce accidental complexity and coupling.
- Decisions are auditable and reversible via follow-up ADRs.

## Follow-ups
- Define initial NFR targets once product constraints are known.
- Add container and component diagrams as the system shape emerges.


