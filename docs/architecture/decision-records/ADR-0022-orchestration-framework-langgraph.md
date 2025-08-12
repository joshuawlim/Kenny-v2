# ADR-0022: Use LangGraph for Coordinator Orchestration

Date: 2025-08-12
Status: Accepted

## Context

The Coordinator must implement deterministic routing, planning, bounded loops, and policy/reviewer gates with strong debuggability. Options include LangGraph (LangChain), AutoGen, and CrewAI.

## Decision

Use LangGraph for the Coordinator and graph control, with a Reviewer node and agents invoked as tools.

## Rationale

- Deterministic edges/state and excellent debugging/tracing
- Native multi-agent patterns and tool calling
- Straightforward policy gating and bounded steps/timeouts

## Consequences

- Coordinator runs as a Python service with LangGraph
- Agents can remain language-agnostic behind HTTP/gRPC or local adapters

## Alternatives Considered

- AutoGen: better for conversational collaboration but less deterministic
- CrewAI: prescriptive pipelines fit approvals; more rigid for dynamic planning

## References

- `docs/architecture/multi-agent-architecture.md#implementation-framework`
