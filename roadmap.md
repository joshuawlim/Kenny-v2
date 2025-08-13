# Kenny v2 Project Roadmap

**Project**: Kenny v2 - Local-first, multi-agent personal assistant  
**Architecture**: Coordinator-led multi-agent system with LangGraph orchestration  
**Current Status**: Phase 0.2 COMPLETED - Coordinator Service with LangGraph operational  
**Target**: Fully operational multi-agent system with local-first privacy controls  

## Roadmap Overview

This roadmap breaks down the project into sequential development phases, with each phase focusing on specific agents and capabilities. Success measures and objectives are defined for each step to ensure clear completion criteria.

---

## Phase 0: Foundation & Infrastructure (Weeks 1-2)

### 0.1 Agent Registry Service ✅ **COMPLETED**
**Objective**: Create central service for agent registration and capability discovery

**Components**:
- Python FastAPI service for agent registration
- Agent manifest validation using JSON Schema
- Health check monitoring for registered agents
- Capability routing and discovery

**Success Measures**:
- [x] Agent Registry service starts and responds to health checks
- [x] Agent manifests can be registered and validated against schema
- [x] Capability discovery returns accurate agent listings
- [x] Health monitoring detects agent status changes
- [x] All endpoints return proper HTTP status codes and error messages

**Implementation Status**: 
- ✅ Core registry logic implemented with async support
- ✅ FastAPI application with all required endpoints
- ✅ Pydantic V2 models with comprehensive validation
- ✅ Docker containerization and health checks
- ✅ Integration with existing infrastructure (docker-compose, Caddy)
- ✅ Comprehensive test suite (21/21 tests passing)
- ✅ Egress domain validation per ADR-0012
- ✅ Health monitoring with configurable intervals

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

### 0.2 Coordinator Skeleton (LangGraph) ✅ **COMPLETED**
**Objective**: Create basic coordinator service with LangGraph integration

**Components**:
- Python service with LangGraph orchestration
- Basic routing and planning nodes
- Agent communication framework
- Policy engine stub

**Success Measures**:
- [x] Coordinator service starts and responds to health checks
- [x] LangGraph nodes can be defined and executed
- [x] Basic routing between nodes functions correctly
- [x] Agent communication framework can send/receive messages
- [x] Policy engine stub accepts basic rules

**Implementation Status**: 
- ✅ Core coordinator logic implemented with LangGraph integration
- ✅ Four-node execution graph: router → planner → executor → reviewer
- ✅ Smart intent classification for mail, calendar, and general operations
- ✅ Policy enforcement engine with approval workflows
- ✅ Agent communication framework for registry integration
- ✅ FastAPI application with coordinator and policy endpoints
- ✅ Comprehensive test suite (14/14 tests passing)
- ✅ Docker containerization and health checks
- ✅ Local testing script for verification

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

### 0.3 Base Agent Framework (Agent SDK)
**Objective**: Create foundation for all service agents

**Components**:
- Base agent class with common functionality
- Capability handler framework
- Tool integration patterns
- Health check and monitoring

**Success Measures**:
- [ ] Base agent class can be inherited and extended
- [ ] Capability handlers can be registered and executed
- [ ] Tool integration patterns work consistently
- [ ] Health checks return proper status information
- [ ] Agent registration with registry works correctly

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

---

## Phase 1: Core Agent Extraction (Weeks 3-4)

### 1.1 Mail Agent
**Objective**: Extract mail functionality into a dedicated agent

**Current Implementation**: Embedded in `services/api/src/index.js`

**Success Measures**:
- [ ] Mail agent starts and registers with agent registry
- [ ] All existing mail functionality works through agent interface
- [ ] Agent manifest declares correct capabilities and data scopes
- [ ] macOS Bridge integration functions correctly
- [ ] API service can communicate with mail agent
- [ ] Performance matches or exceeds current implementation

**Capabilities to Implement**:
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

### 1.2 Contacts Agent
**Objective**: Create agent for contact management and enrichment

**Current Implementation**: Data model exists, no service implementation

**Success Measures**:
- [ ] Contacts agent starts and registers with agent registry
- [ ] Contact resolution can find and disambiguate contacts
- [ ] Contact enrichment adds additional information
- [ ] Contact merging handles duplicate resolution
- [ ] Local contacts database integration works correctly
- [ ] All capabilities return properly structured data

**Capabilities to Implement**:
- `contacts.resolve` - Find and disambiguate contacts
- `contacts.enrich` - Add additional contact information
- `contacts.merge` - Merge duplicate contacts

### 1.3 Memory/RAG Agent
**Objective**: Create agent for memory and retrieval operations

**Current Implementation**: Data model exists, no service implementation

**Success Measures**:
- [ ] Memory agent starts and registers with agent registry
- [ ] Embedding generation works with local Ollama models
- [ ] Memory storage and retrieval functions correctly
- [ ] Semantic search returns relevant results
- [ ] Cross-platform memory aggregation works
- [ ] Retention policies are enforced correctly

**Capabilities to Implement**:
- `memory.retrieve` - Semantic search across stored data
- `memory.embed` - Generate embeddings for text
- `memory.store` - Store new memories with metadata

---

## Phase 2: Coordinator Implementation (Weeks 5-6)

### 2.1 Routing and Planning
**Objective**: Implement intelligent request routing and task planning

**Components**:
- Intent classification using LLM
- Capability mapping and discovery
- Task DAG generation
- Plan optimization and validation

**Success Measures**:
- [ ] Intent classification correctly identifies user requests
- [ ] Capability mapping finds appropriate agents for tasks
- [ ] Task DAG generation creates valid execution plans
- [ ] Plan optimization improves execution efficiency
- [ ] Plan validation catches invalid configurations
- [ ] Fallback handling works for unknown intents

**Implementation**:
- Router node with intent classification
- Planner node with task decomposition
- Plan validation and optimization
- Fallback handling for unknown intents

### 2.2 Execution Engine
**Objective**: Implement reliable agent execution with error handling

**Components**:
- Agent execution orchestration
- Error handling and retry logic
- Circuit breakers and timeouts
- Result aggregation and validation

**Success Measures**:
- [ ] Agent execution follows planned DAG correctly
- [ ] Error handling recovers from agent failures
- [ ] Retry logic works for transient failures
- [ ] Circuit breakers prevent cascading failures
- [ ] Timeouts are enforced correctly
- [ ] Result aggregation combines agent outputs properly

**Implementation**:
- Executor node with agent communication
- Error handling and recovery
- Result validation and aggregation
- Performance monitoring and metrics

### 2.3 Policy Engine
**Objective**: Implement approval workflows and policy enforcement

**Components**:
- Approval rule engine
- Egress allowlist enforcement
- Data access controls
- Audit logging and compliance

**Success Measures**:
- [ ] Approval rules are enforced correctly
- [ ] Egress allowlist blocks unauthorized network access
- [ ] Data access controls limit agent permissions
- [ ] Audit logging captures all operations
- [ ] Policy violations are detected and blocked
- [ ] Approval workflows function end-to-end

**Implementation**:
- Policy rule definitions
- Approval workflow management
- Access control enforcement
- Comprehensive audit logging

---

## Phase 3: Communication & Integration Agents (Weeks 7-8)

### 3.1 WhatsApp Agent
**Objective**: Create agent for WhatsApp integration with read-only capabilities

**Current Implementation**: ADR-0019 defines local image understanding requirements

**Success Measures**:
- [ ] WhatsApp agent starts and registers with agent registry
- [ ] Chat history can be searched and retrieved
- [ ] Reply proposals are generated correctly
- [ ] Local image understanding works (OCR/vision models)
- [ ] No network egress occurs (local-only operation)
- [ ] Agent respects read-only constraints

**Capabilities to Implement**:
- `chats.search` - Search chat history by contact and keywords
- `chats.propose_reply` - Generate reply suggestions
- `chats.read` - Read chat messages and media

### 3.2 iMessage Agent
**Objective**: Create agent for iMessage integration

**Current Implementation**: macOS Bridge integration available

**Success Measures**:
- [ ] iMessage agent starts and registers with agent registry
- [ ] Message reading and searching works correctly
- [ ] Reply proposals are generated appropriately
- [ ] macOS Bridge integration functions properly
- [ ] Read operations work without approval
- [ ] Write operations require explicit approval

**Capabilities to Implement**:
- `messages.read` - Read iMessage content
- `messages.search` - Search message history
- `messages.propose_reply` - Generate reply suggestions

### 3.3 Calendar Agent
**Objective**: Create agent for Apple Calendar integration

**Current Implementation**: No current implementation

**Success Measures**:
- [ ] Calendar agent starts and registers with agent registry
- [ ] Event proposals can be created and presented
- [ ] Calendar writes require explicit approval
- [ ] Apple Calendar integration works correctly
- [ ] Event constraints and scheduling logic functions
- [ ] Approval workflows integrate with Web Chat

**Capabilities to Implement**:
- `calendar.propose_event` - Create event proposals
- `calendar.write_event` - Create approved events
- `calendar.read` - Read calendar data

---

## Phase 4: Observability & Safety (Weeks 9-10)

### 4.1 Comprehensive Tracing
**Objective**: Implement end-to-end request tracing

**Components**:
- Request tracing across coordinator and agents
- Performance metrics collection
- Error tracking and debugging
- Audit trail generation

**Success Measures**:
- [ ] Request tracing covers coordinator and all agents
- [ ] Performance metrics are collected accurately
- [ ] Error tracking provides debugging information
- [ ] Audit trails capture all operations
- [ ] Tracing data is searchable and filterable
- [ ] Performance impact of tracing is minimal

**Implementation**:
- Distributed tracing with correlation IDs
- Performance metrics collection
- Error aggregation and reporting
- Debug information collection

### 4.2 Health Monitoring
**Objective**: Implement comprehensive system health monitoring

**Components**:
- Agent health status monitoring
- System performance metrics
- Alert generation and notification
- Health dashboard integration

**Success Measures**:
- [ ] Agent health status is monitored continuously
- [ ] System performance metrics are collected
- [ ] Alerts are generated for critical issues
- [ ] Health dashboard displays current status
- [ ] Health checks are lightweight and reliable
- [ ] Historical health data is preserved

**Implementation**:
- Health check aggregation
- Performance metrics collection
- Alert rule engine
- Dashboard integration

### 4.3 Security & Privacy Controls
**Objective**: Implement comprehensive security and privacy controls

**Components**:
- Egress allowlist enforcement
- Data access controls
- Privacy-preserving operations
- Security audit logging

**Success Measures**:
- [ ] Egress allowlist blocks unauthorized network access
- [ ] Data access controls limit agent permissions
- [ ] Privacy-preserving operations work correctly
- [ ] Security audit logging captures all security events
- [ ] No data leaks occur during normal operation
- [ ] Security controls are tested and validated

---

## Phase 5: Extensibility & Testing (Weeks 11-12)

### 5.1 Agent SDK
**Objective**: Provide comprehensive SDK for new agent development

**Components**:
- Agent development templates
- Testing frameworks and utilities
- Deployment and packaging tools
- Documentation and examples

**Success Measures**:
- [ ] SDK package can be installed and imported
- [ ] Agent templates create working agents
- [ ] Testing utilities support comprehensive testing
- [ ] Deployment tools work correctly
- [ ] Documentation is clear and complete
- [ ] Example agents demonstrate best practices

**Implementation**:
- SDK package with templates
- Testing utilities and frameworks
- Deployment automation
- Comprehensive documentation

### 5.2 Conformance Testing
**Objective**: Ensure all agents follow system contracts

**Components**:
- Capability conformance testing
- Policy enforcement verification
- Performance and reliability testing
- Security and privacy testing

**Success Measures**:
- [ ] All agents pass conformance tests
- [ ] Policy enforcement is verified correctly
- [ ] Performance benchmarks are established
- [ ] Security testing framework works
- [ ] Test coverage is comprehensive
- [ ] Automated testing runs successfully

**Implementation**:
- Automated conformance tests
- Policy enforcement verification
- Performance benchmarking
- Security testing framework

### 5.3 Integration Testing
**Objective**: Verify end-to-end system functionality

**Components**:
- Complete workflow testing
- Cross-agent communication testing
- Error handling and recovery testing
- Performance and load testing

**Success Measures**:
- [ ] Complete workflows function end-to-end
- [ ] Cross-agent communication works reliably
- [ ] Error handling and recovery functions correctly
- [ ] Performance meets or exceeds requirements
- [ ] System handles load gracefully
- [ ] All integration points are tested

---

## Phase 6: Production Readiness (Weeks 13-14)

### 6.1 Performance Optimization
**Objective**: Optimize system performance and resource usage

**Components**:
- Performance profiling and analysis
- Resource usage optimization
- Caching and optimization strategies
- Load testing and capacity planning

**Success Measures**:
- [ ] Response times meet performance targets
- [ ] Resource usage is optimized
- [ ] Caching improves performance
- [ ] System handles expected load
- [ ] Performance is consistent and predictable
- [ ] Optimization metrics are measurable

### 6.2 Documentation & Training
**Objective**: Complete comprehensive documentation and training materials

**Components**:
- User documentation
- Developer documentation
- Operations documentation
- Training materials and examples

**Success Measures**:
- [ ] User documentation is complete and clear
- [ ] Developer documentation covers all aspects
- [ ] Operations documentation is comprehensive
- [ ] Training materials are effective
- [ ] Documentation is kept current
- [ ] Examples demonstrate best practices

### 6.3 Deployment & Operations
**Objective**: Establish production deployment and operations procedures

**Components**:
- Production deployment procedures
- Monitoring and alerting setup
- Backup and recovery procedures
- Incident response procedures

**Success Measures**:
- [ ] Production deployment is automated and reliable
- [ ] Monitoring and alerting work correctly
- [ ] Backup and recovery procedures are tested
- [ ] Incident response procedures are documented
- [ ] Operations team is trained and ready
- [ ] System is production-ready

---

## Success Criteria Summary

### Technical Metrics
- **Response Time**: Maintain or improve current performance (< 2 seconds for simple queries)
- **Reliability**: 99.9% uptime with graceful degradation
- **Extensibility**: New agents can be added in < 1 week
- **Observability**: All operations are traceable and debuggable

### User Experience Metrics
- **Approval Workflow**: Calendar and message approvals complete in < 30 seconds
- **Privacy Control**: Zero data leaks, all operations respect user preferences
- **System Transparency**: Users can see and understand all system operations
- **Error Handling**: Clear error messages and recovery options

### Operational Metrics
- **Debugging**: Issues can be diagnosed in < 15 minutes
- **Monitoring**: System health is visible in real-time
- **Maintenance**: System updates can be completed in < 1 hour
- **Deployment**: New versions can be deployed in < 30 minutes

---

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

---

## Next Steps

### Immediate Actions (This Week)
1. **Review and Approve**: Get stakeholder approval for this roadmap
2. **Resource Allocation**: Assign team members to implementation phases
3. **Environment Setup**: Prepare development and testing environments
4. **Dependency Installation**: Install required tools and frameworks

### Week 1-2 Goals
1. **Agent Registry**: ✅ COMPLETED - Agent registry service operational
2. **Coordinator Skeleton**: ✅ COMPLETED - Coordinator service with LangGraph operational
3. **Base Framework**: 🔄 NEXT - Implement base agent framework (Agent SDK)
4. **Testing**: ✅ COMPLETED - Testing framework established with comprehensive coverage

### Success Metrics by Phase
- **Week 2**: ✅ Agent registry operational, ✅ Coordinator service operational
- **Week 4**: Mail agent extracted and operational
- **Week 6**: Basic coordinator functionality operational
- **Week 8**: Communication agents operational
- **Week 10**: Comprehensive observability implemented
- **Week 12**: Full multi-agent system operational with SDK
- **Week 14**: Production-ready system with complete documentation

---

## Notes

- **Local-First**: All operations default to local processing
- **Network Egress**: Strictly controlled via allowlist per ADR-0012
- **Approval Workflows**: Calendar actions require explicit human approval via Web Chat
- **Privacy**: All data processing occurs locally with user control
- **Extensibility**: New agents can be added without coordinator changes
- **Testing**: Each phase includes comprehensive testing before proceeding to next phase
