# Multi-Agent Implementation Plan

## Overview
This document outlines the concrete steps to refactor Kenny v2 from its current monolithic architecture to a coordinator-led multi-agent system.

## Current State Analysis

### Existing Components
- **API Service**: Express.js service handling mail ETL, status, and audit
- **Bridge Service**: Python FastAPI stub for macOS integration
- **UI Service**: React-based web interface
- **Workers**: Background processing services
- **Data Layer**: SQLite for messages, PostgreSQL for media

### Current Architecture Issues
- **Monolithic API**: All functionality in single Express.js service
- **Tight Coupling**: Mail ETL directly embedded in API service
- **Limited Extensibility**: Adding new services requires API modifications
- **Mixed Responsibilities**: API handles both coordination and service logic

## Target Architecture

### Multi-Agent System
- **Coordinator**: Python service with LangGraph orchestration
- **Service Agents**: Isolated agents for each domain (Mail, WhatsApp, Calendar, etc.)
- **Agent Registry**: Dynamic capability discovery and registration
- **Policy Engine**: Approval workflows and egress controls

## Implementation Phases

### Phase 0: Foundations (Week 1-2)

#### 0.1 Agent Registry Service
**Goal**: Create the central service for agent registration and capability discovery

**Components**:
- Python FastAPI service for agent registration
- Agent manifest validation using JSON Schema
- Health check monitoring for registered agents
- Capability routing and discovery

**Files to Create**:
```
services/agent-registry/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Pydantic models
│   ├── registry.py          # Agent registry logic
│   └── schemas.py           # JSON Schema validation
└── tests/
    └── test_registry.py
```

**API Endpoints**:
- `POST /agents/register` - Agent registration
- `GET /agents` - List all registered agents
- `GET /agents/{agent_id}` - Get agent details
- `GET /capabilities` - List all available capabilities
- `GET /capabilities/{verb}` - Get capability details

#### 0.2 Coordinator Skeleton
**Goal**: Create the basic coordinator service with LangGraph integration

**Components**:
- Python service with LangGraph orchestration
- Basic routing and planning nodes
- Agent communication framework
- Policy engine stub

**Files to Create**:
```
services/coordinator/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── main.py              # FastAPI + LangGraph app
│   ├── coordinator.py       # Main coordinator logic
│   ├── nodes/
│   │   ├── router.py        # Intent classification
│   │   ├── planner.py       # Task planning
│   │   ├── executor.py      # Agent execution
│   │   └── reviewer.py      # Safety review
│   ├── agents/
│   │   └── agent_client.py  # Agent communication
│   └── policy/
│       └── engine.py        # Policy enforcement
└── tests/
    └── test_coordinator.py
```

#### 0.3 Base Agent Framework
**Goal**: Create the foundation for all service agents

**Components**:
- Base agent class with common functionality
- Capability handler framework
- Tool integration patterns
- Health check and monitoring

**Files to Create**:
```
services/agent-sdk/
├── setup.py
├── kenny_agent/
│   ├── __init__.py
│   ├── base_agent.py        # Base agent class
│   ├── base_handler.py      # Base capability handler
│   ├── base_tool.py         # Base tool class
│   ├── health.py            # Health check utilities
│   └── registry.py          # Registration utilities
└── tests/
    └── test_base_agent.py
```

### Phase 1: Agent Extraction (Week 3-4)

#### 1.1 Mail Agent
**Goal**: Extract mail functionality into a dedicated agent

**Current Implementation**: Embedded in `services/api/src/index.js`

**Extraction Steps**:
1. Create `services/mail-agent/` directory
2. Move mail ETL logic from API service
3. Implement agent manifest with capabilities
4. Create capability handlers for search, read, propose_reply
5. Integrate with macOS Bridge service
6. Update API service to use mail agent

**Capabilities**:
- `messages.search` - Search mail by query and filters
- `messages.read` - Retrieve full message content
- `messages.propose_reply` - Generate reply suggestions

**Files to Create**:
```
services/mail-agent/
├── Dockerfile
├── requirements.txt
├── manifest.json            # Agent capabilities
├── src/
│   ├── main.py              # Agent entry point
│   ├── agent.py             # Mail agent implementation
│   ├── handlers/
│   │   ├── search.py        # Search capability
│   │   ├── read.py          # Read capability
│   │   └── propose_reply.py # Reply proposal
│   └── tools/
│       └── mail_bridge.py   # macOS Bridge integration
└── tests/
    └── test_mail_agent.py
```

#### 1.2 Contacts Agent
**Goal**: Create agent for contact management and enrichment

**Current Implementation**: Data model exists, no service implementation

**Implementation Steps**:
1. Create `services/contacts-agent/` directory
2. Implement contact resolution and enrichment
3. Create capability handlers for resolve, enrich, merge
4. Integrate with local contacts database
5. Add to agent registry

**Capabilities**:
- `contacts.resolve` - Find and disambiguate contacts
- `contacts.enrich` - Add additional contact information
- `contacts.merge` - Merge duplicate contacts

#### 1.3 Memory/RAG Agent
**Goal**: Create agent for memory and retrieval operations

**Current Implementation**: Data model exists, no service implementation

**Implementation Steps**:
1. Create `services/memory-agent/` directory
2. Implement embedding generation and storage
3. Create capability handlers for retrieve, embed, store
4. Integrate with Ollama for local embeddings
5. Add to agent registry

**Capabilities**:
- `memory.retrieve` - Semantic search across stored data
- `memory.embed` - Generate embeddings for text
- `memory.store` - Store new memories with metadata

### Phase 2: Coordinator Implementation (Week 5-6)

#### 2.1 Routing and Planning
**Goal**: Implement intelligent request routing and task planning

**Components**:
- Intent classification using LLM
- Capability mapping and discovery
- Task DAG generation
- Plan optimization and validation

**Implementation**:
- Router node with intent classification
- Planner node with task decomposition
- Plan validation and optimization
- Fallback handling for unknown intents

#### 2.2 Execution Engine
**Goal**: Implement reliable agent execution with error handling

**Components**:
- Agent execution orchestration
- Error handling and retry logic
- Circuit breakers and timeouts
- Result aggregation and validation

**Implementation**:
- Executor node with agent communication
- Error handling and recovery
- Result validation and aggregation
- Performance monitoring and metrics

#### 2.3 Policy Engine
**Goal**: Implement approval workflows and policy enforcement

**Components**:
- Approval rule engine
- Egress allowlist enforcement
- Data access controls
- Audit logging and compliance

**Implementation**:
- Policy rule definitions
- Approval workflow management
- Access control enforcement
- Comprehensive audit logging

### Phase 3: Observability and Safety (Week 7-8)

#### 3.1 Comprehensive Tracing
**Goal**: Implement end-to-end request tracing

**Components**:
- Request tracing across coordinator and agents
- Performance metrics collection
- Error tracking and debugging
- Audit trail generation

**Implementation**:
- Distributed tracing with correlation IDs
- Performance metrics collection
- Error aggregation and reporting
- Debug information collection

#### 3.2 Health Monitoring
**Goal**: Implement comprehensive system health monitoring

**Components**:
- Agent health status monitoring
- System performance metrics
- Alert generation and notification
- Health dashboard integration

**Implementation**:
- Health check aggregation
- Performance metrics collection
- Alert rule engine
- Dashboard integration

### Phase 4: Extensibility and Testing (Week 9-10)

#### 4.1 Agent SDK
**Goal**: Provide comprehensive SDK for new agent development

**Components**:
- Agent development templates
- Testing frameworks and utilities
- Deployment and packaging tools
- Documentation and examples

**Implementation**:
- SDK package with templates
- Testing utilities and frameworks
- Deployment automation
- Comprehensive documentation

#### 4.2 Conformance Testing
**Goal**: Ensure all agents follow system contracts

**Components**:
- Capability conformance testing
- Policy enforcement verification
- Performance and reliability testing
- Security and privacy testing

**Implementation**:
- Automated conformance tests
- Policy enforcement verification
- Performance benchmarking
- Security testing framework

## Migration Strategy

### Incremental Migration
1. **Parallel Operation**: Run new agents alongside existing services
2. **Feature Flags**: Use feature flags to switch between old and new implementations
3. **Gradual Rollout**: Migrate one service at a time
4. **Rollback Plan**: Maintain ability to quickly revert to previous implementation

### Data Migration
1. **Schema Compatibility**: Maintain backward compatibility during transition
2. **Data Validation**: Verify data integrity after migration
3. **Performance Monitoring**: Track performance impact of changes
4. **User Experience**: Ensure no degradation in user experience

### Testing Strategy
1. **Unit Testing**: Comprehensive unit tests for all components
2. **Integration Testing**: Test interactions between coordinator and agents
3. **End-to-End Testing**: Test complete user workflows
4. **Performance Testing**: Verify performance under load
5. **Security Testing**: Verify security and privacy controls

## Success Criteria

### Technical Metrics
- **Response Time**: Maintain or improve current performance
- **Reliability**: Reduce system failures and improve error handling
- **Extensibility**: Reduce time to add new service integrations
- **Observability**: Improve debugging and monitoring capabilities

### User Experience Metrics
- **Approval Workflow**: Streamlined calendar and message approvals
- **Privacy Control**: Enhanced user control over data and operations
- **System Transparency**: Better visibility into system operations
- **Error Handling**: Improved error messages and recovery

### Operational Metrics
- **Debugging**: Reduced time to diagnose issues
- **Monitoring**: Improved system health visibility
- **Maintenance**: Easier system updates and modifications
- **Deployment**: Faster and more reliable deployments

## Risk Mitigation

### Technical Risks
- **Performance Degradation**: Comprehensive performance testing and monitoring
- **Integration Complexity**: Incremental migration with rollback capability
- **Data Loss**: Comprehensive backup and validation procedures
- **Security Vulnerabilities**: Security testing and code review

### Operational Risks
- **Service Disruption**: Parallel operation during migration
- **User Experience**: Continuous monitoring and user feedback
- **Team Learning**: Comprehensive documentation and training
- **Timeline Slippage**: Phased approach with clear milestones

## Next Steps

### Immediate Actions (This Week)
1. **Review and Approve**: Get stakeholder approval for this plan
2. **Resource Allocation**: Assign team members to implementation phases
3. **Environment Setup**: Prepare development and testing environments
4. **Dependency Installation**: Install required tools and frameworks

### Week 1-2 Goals
1. **Agent Registry**: Complete agent registry service implementation
2. **Coordinator Skeleton**: Create basic coordinator with LangGraph
3. **Base Framework**: Implement base agent framework
4. **Testing**: Establish testing framework and initial tests

### Success Metrics
- **Week 2**: Agent registry operational with coordinator skeleton
- **Week 4**: Mail agent extracted and operational
- **Week 6**: Basic coordinator functionality operational
- **Week 8**: Comprehensive observability implemented
- **Week 10**: Full multi-agent system operational with SDK
