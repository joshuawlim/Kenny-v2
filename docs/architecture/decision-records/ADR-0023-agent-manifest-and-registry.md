# ADR-0023: Agent Manifest and Registry

Date: 2025-08-12
Status: Accepted

## Context

The Coordinator needs a consistent way to discover agent capabilities, data scopes, tool access needs, and egress domains to route requests and enforce policies.

## Decision

Adopt an Agent Manifest (JSON) validated at registration time and stand up an Agent Registry service to store and serve manifests and health.

Manifest fields include:

- `agent_id`, `version`, `display_name`, `description`
- `capabilities[]` with `verb`, `input_schema`, `output_schema`, `safety_annotations`, `sla`
- `data_scopes[]`, `tool_access[]`, `egress_domains[]`
- `health_check` config and free-form `metadata`

## Consequences

- Deterministic routing and planning based on declared capabilities
- Enforce egress allowlists from manifests (deny-by-default otherwise)
- Health-aware execution and circuit breaking

## References

- `docs/architecture/schemas/agent-manifest.json`
- `docs/architecture/multi-agent-architecture.md#contracts-and-capability-model`
