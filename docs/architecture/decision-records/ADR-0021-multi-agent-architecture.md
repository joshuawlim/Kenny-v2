# ADR-0021: Coordinator-led Multi-Agent Architecture

Date: 2025-08-12
Status: Accepted

## Context

Kenny v2 began as a monolithic set of services where coordination and domain logic were intertwined. This hindered extensibility, debuggability, and policy enforcement (egress allowlists, approvals). We need a modular, evolvable design that preserves the local-first, privacy-first posture.

## Decision

Adopt a Supervisor/Coordinator pattern with agents-as-tools:

- A single Coordinator performs intent classification, capability discovery, routing, planning (task DAG), execution, and review gates.
- Each integration/domain runs as a Service Agent (Mail, iMessage, WhatsApp, Calendar, Contacts, Memory/RAG, Web, Observability) exposing high-level capabilities with typed inputs/outputs and safety annotations.
- An Agent Registry provides dynamic capability discovery from agent manifests.
- A Policy Engine centralizes approvals and egress allowlist enforcement.
- A Reviewer/Verifier gate validates safety and policy compliance for user-visible outputs or writes.

## Consequences

- Modularity and extensibility: adding a service is adding a new agent with a manifest.
- Predictable control: bounded loops, retries, and failure handling live in the Coordinator.
- Privacy and safety: least privilege per agent; coordinator-enforced approvals and deny-by-default egress.
- Observability: per-step tracing and audit trails across a plan DAG.

## Alternatives Considered

- Free-form multi-agent networks: rejected due to unpredictability and latency.
- Single monolithic agent: rejected due to poor modularity and policy isolation.

## References

- `docs/architecture/multi-agent-architecture.md`
- `docs/architecture/schemas/agent-manifest.json`
- ADR-0012 (Local egress allowlist)
