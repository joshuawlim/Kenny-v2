# Multi-Agent Architecture Specification

## Overview
Kenny v2 refactored into a coordinator-led multi-agent system where each service (Mail, iMessage, WhatsApp, Calendar, Contacts, etc.) operates as an isolated agent with clear interfaces, while maintaining privacy-first, local-first principles.

## Architecture Principles

### Core Design Patterns
- **Supervisor/Coordinator Pattern**: Single coordinator routes requests, manages hand-offs, and enforces policies
- **Agents-as-Tools**: Coordinator calls agents as tools with structured arguments and bounded loops
- **Hierarchical Control**: Clear separation between coordination logic and agent implementation

### Key Benefits
- **Modularity**: Each integration is an isolated agent with its own tools, prompts, memory, and lifecycle
- **Extensibility**: Adding new services means adding new agents that advertise capabilities via stable contracts
- **Safety**: Agents operate with least privilege; coordinator enforces egress allowlists, approvals, and audit trails
- **Observability**: Deterministic control over routing, timeouts, retries, and failure modes

## System Architecture

### Coordinator (Supervisor)
**Responsibilities:**
- Intent classification and capability discovery
- Request routing and plan decomposition
- Adjudication and approvals management
- Conflict resolution and guardrails
- Conversation/session management (default via Web Chat; optional channels: Telegram/WhatsApp/iMessage)

**State Management:**
- Global conversation/session state
- Task DAG (Directed Acyclic Graph)
- Policy context (egress allowlist, PII scopes)

**Core Components:**
- Agent Registry: Dynamic capability discovery
- Plan Executor: Task orchestration and execution
- Policy Engine: Approval rules and egress controls
- Tracing/Logs: Comprehensive observability

### Service Agents

#### Mail Agent
- **Capabilities**: `messages.search`, `messages.read`, `messages.propose_reply`
- **Tools**: Apple Mail bridge integration
- **Data Scope**: Local index/embeddings, read-only operations
- **Constraints**: 30-day scan window, Inbox/Sent only

#### iMessage Agent
- **Capabilities**: `messages.read`, `messages.search`, `messages.propose_reply`
- **Tools**: macOS Bridge integration
- **Data Scope**: Local message database
- **Constraints**: Read operations only, write requires approval

#### WhatsApp Agent
- **Capabilities**: `chats.search`, `chats.propose_reply` (read-only MVP)
- **Tools**: WhatsApp Web automation profile
- **Data Scope**: Local chat history
- **Constraints**: Read-only operations, future: proposal→explicit-send

#### Calendar Agent
- **Capabilities**: `calendar.propose_event`, `calendar.write_event`
- **Tools**: Apple Calendar integration
- **Data Scope**: Local calendar data
- **Constraints**: Propose events only, write requires UI approval

#### Contacts Agent
- **Capabilities**: `contacts.resolve`, `contacts.enrich`, `contacts.merge`
- **Tools**: Local contacts database
- **Data Scope**: Normalized contacts knowledge base
- **Constraints**: Local storage only, no external sync

#### Memory/RAG Agent
- **Capabilities**: `memory.retrieve`, `memory.embed`, `memory.store`
- **Tools**: Local embedding models (Ollama)
- **Data Scope**: Cross-platform memory and retrieval
- **Constraints**: Local processing only, per-source retention policies

#### Web Agent (Website Worker)
- **Capabilities**: `web.fetch`, `web.scrape`, `web.qa`
- **Tools**: Constrained browsing per allowlist
- **Data Scope**: Whitelisted website content
- **Constraints**: Egress allowlist enforcement, rate limiting

#### Observability Agent
- **Capabilities**: `health.status`, `metrics.collect`, `audit.log`
- **Tools**: System monitoring and metrics collection
- **Data Scope**: System health and performance data
- **Constraints**: Local metrics only, no external reporting

## Coordination Pattern

### Request Flow
1. **Intent Classification**: Coordinator analyzes user request
2. **Capability Discovery**: Agent Registry provides available capabilities
3. **Plan Generation**: Coordinator creates task DAG
4. **Execution**: Agents called as tools with structured arguments
5. **Result Aggregation**: Coordinator combines agent outputs
6. **Response**: Final result returned to user

### Agent Communication
- **Structured Messages**: JSON with headers (request_id, session_id, policy_ctx, step_budget)
- **Typed Interfaces**: Input/output schemas for all capabilities
- **Bounded Loops**: Coordinator enforces max handoffs and reflection steps
- **Error Handling**: Graceful degradation and circuit breakers

## Contracts and Capability Model

### Agent Manifest
Each agent registers with the Agent Registry at startup, declaring:

```json
{
  "agent_id": "mail-agent",
  "capabilities": [
    {
      "verb": "messages.search",
      "input_schema": {...},
      "output_schema": {...},
      "safety_annotations": ["read-only"],
      "sla": {"latency_ms": 100, "rate_limit": 100}
    }
  ],
  "data_scopes": ["mail:inbox", "mail:sent"],
  "tool_access": ["macos-bridge"],
  "egress_domains": []
}
```

### Capability Verbs
- **messages.search**: Find messages by query and filters
- **messages.read**: Retrieve full message content
- **messages.propose_reply**: Generate reply suggestions
- **calendar.propose_event**: Create event proposals
- **calendar.write_event**: Create approved events
- **contacts.resolve**: Find and disambiguate contacts
- **memory.retrieve**: Semantic search across stored data
- **web.fetch**: Retrieve content from whitelisted sites

## Implementation Framework

### Recommendation: LangGraph
- **Rationale**: Deterministic edges, strong debugging, native multi-agent patterns
- **Benefits**: Easy policy encoding, bounded loops, reproducible traces
- **Deployment**: Python orchestration container with agent communication

### Alternative Considerations
- **AutoGen**: For conversation-centric collaboration (less deterministic)
- **CrewAI**: For role-defined crews and approval-heavy pipelines

## Security and Privacy

### Egress Controls
- **Deny-by-default**: Network level egress blocking
- **Coordinator whitelisting**: Only agent-declared domains allowed
- **WebAgent isolation**: Single agent with general outbound HTTP access

### Data Privacy
- **Least privilege**: Agents access only required data
- **Local processing**: All embeddings and analysis done locally
- **Audit trails**: Comprehensive logging of all operations
- **User control**: Explicit approval for any write operations

## Deployment Architecture

### Local-First Design
- **Ollama**: Host or containerized per environment
- **Agent Communication**: Localhost/Unix sockets for security
- **Data Isolation**: Docker volumes per agent data domain
- **Backup/Restore**: Preserved isolation for data management

### Container Strategy
- **Coordinator**: Python container with LangGraph orchestration
- **Service Agents**: Separate containers/processes per domain
- **Bridge Services**: macOS host integration via Docker networking
- **Data Persistence**: Volume mounts for SQLite and PostgreSQL

## Migration Path

### Phase 0: Foundations
- Define Agent Manifest JSON Schema
- Build Agent Registry service
- Create coordinator skeleton with LangGraph
- Implement Policy Engine stub

### Phase 1: Agent Extraction
- Extract existing integrations into agent modules
- Implement agent adapters for current services
- Maintain existing functionality during transition

### Phase 2: Coordinator Implementation
- Build routing and planning nodes
- Implement execution and review nodes
- Add bounded steps and timeouts

### Phase 3: Observability
- Implement comprehensive tracing
- Add health metrics and alerting
- Create policy enforcement dashboard

### Phase 4: Extensibility
- Provide Agent SDK template
- Add conformance testing
- Document extension patterns

## Success Metrics

### Technical Metrics
- **Response Time**: Maintain or improve current performance
- **Reliability**: Reduce system failures and improve error handling
- **Extensibility**: Time to add new service integrations

### User Experience Metrics
- **Approval Workflow**: Streamlined calendar and message approvals
- **Privacy Control**: Enhanced user control over data and operations
- **System Transparency**: Better visibility into system operations

### Operational Metrics
- **Debugging**: Reduced time to diagnose issues
- **Monitoring**: Improved system health visibility
- **Maintenance**: Easier system updates and modifications

## Message and State Model

- Typed messages: JSON envelope with `request_id`, `session_id`, `user_id`, `policy_ctx`, `step_budget` and a typed payload per capability schema.
- Short‑lived per‑task scratchpad plus session memory governed by retention policies (per‑source TTL, redact strategies).
- Bounded loops: the coordinator enforces max handoffs and reflection steps to avoid infinite bouncing.

## Core Flows

1) Simple query (read‑only)
- Plan: Mail.messages.search → Memory.memory.summarize → Reviewer → Response.

2) Write with approval
- Plan: Contacts.resolve → WebChat.session.notify (default) or Channel.search (Telegram/WhatsApp/iMessage, if enabled) → Calendar.calendar.propose_event → UI approval → Calendar.calendar.write_event.

3) Cross‑channel task
- Plan: Mail.messages.search(thread) → Memory.memory.summarize → WhatsApp.chats.propose_reply → Reviewer → UI approval → WhatsApp.chats.send (if enabled).

## Example Capability Map (abbreviated)

- MailAgent:
  - `messages.search({query, time_range}) → {message_ids, snippets, meta}`
  - `messages.read({message_id}) → {headers, body, attachments}`
  - `messages.propose_reply({thread_id, summary}) → {draft_text}`

- CalendarAgent:
  - `calendar.propose_event({title, attendees, window, duration, constraints}) → {event_draft}`
  - `calendar.write_event({event_draft, calendar_id}) → {event_id}`

- WhatsAppAgent:
  - `chats.search({contact, time_range, keywords}) → {messages}`
  - `chats.propose_reply({thread_id, summary}) → {draft_text}`

- MemoryAgent:
  - `memory.retrieve({sources, query, k}) → {chunks, citations}`
  - `memory.embed({text, tags}) → {vector_id}`

See `schemas/agent-manifest.json` for the manifest schema and capability verb format.

## Guardrails

- Hard step budgets and timeouts prevent infinite bounce.
- Tools remain private to agents; the coordinator only sees high‑level capabilities.
- Per‑step structured logs and trace view across the plan DAG improve debuggability.
- Coordinator maintains an execution budget; cache stable sub‑results in MemoryAgent.

## Adding a New Service

1) Implement NewServiceAgent using the SDK template.
2) Define capabilities and JSON Schemas in `manifest.json` with policy annotations.
3) Add a router rule mapping intents → capabilities.
4) Provide e2e tests for conformance, policy enforcement, and planner integration.
5) Update egress allowlist and policy config if external domains are required.

## References

- Databricks: Agent system design patterns
- LangGraph: Multi‑agent concepts and supervisor patterns
- SuperAGI: Designing multi‑agent systems (patterns and pitfalls)
