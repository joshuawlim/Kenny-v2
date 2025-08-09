## Architecture

This directory centralizes design knowledge and decisions for Kenny v2. It follows a pragmatic, documentation-as-code approach.

### Contents
- `architecture-principles.md`: Guiding principles
- `non-functional-requirements.md`: Quality attributes (NFRs)
- `decision-records/`: Architecture Decision Records (ADRs)
- `templates/`: ADR and Module Spec templates
- `diagrams/`: C4-style diagrams (Mermaid)

### Process
1. Capture significant decisions as ADRs.
2. Keep diagrams current with changes.
3. For new/changed modules, add or update a Module Spec.

### C4 Mapping
- Context: System scope and external actors (`diagrams/context.mmd`)
- Container: Deployable/runtime units (add `container.mmd` when ready)
- Component: Internal components and interfaces (add `component-*.mmd` as needed)

### Conventions
- Diagrams are Mermaid `.mmd` files.
- Reference files and modules using backticks and repository-relative paths.
- Prefer clear, high-verbosity prose with precise terminology.


