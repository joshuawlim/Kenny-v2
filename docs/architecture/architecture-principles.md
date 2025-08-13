# Architecture Principles

- Simplicity first: choose the simplest design that meets requirements.
- Clear boundaries: modules encapsulate responsibilities behind stable interfaces.
- API-first: design contracts before implementation where possible.
- Observability built-in: metrics, logs, and traces for critical paths.
- Security by default: least-privilege, secure-by-default configs, secrets management.
- Local-first privacy: run workloads locally by default; avoid cloud dependencies. All outbound network traffic is allowlisted (see ADR-0012).
- Human-in-the-loop for writes: any user-visible write (e.g., calendar events) requires explicit approval.
- Resilience and scalability: graceful degradation, backpressure, idempotency.
- Operational excellence: automate testing, builds, deployments, and rollbacks.
- Evolutionary architecture: support incremental change via modularity and ADRs.