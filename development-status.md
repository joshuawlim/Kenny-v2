# Kenny v2 System Prompt

## Project Overview
Kenny v2 is a local-first, multi-agent personal assistant system built with Python FastAPI services and LangGraph orchestration. The system prioritizes privacy and local data processing while providing intelligent automation capabilities.

## Architecture
- **Multi-Agent System**: Coordinator-led orchestration using LangGraph
- **Local-First**: All processing occurs locally with no external dependencies
- **Privacy-Focused**: User data never leaves the local environment
- **Modular Design**: Agents can be developed and deployed independently

## Current Status

### ✅ Phase 2: FULLY COMPLETED - Intelligent Coordinator Orchestration
**Completion Date**: August 15, 2025  
**Total Test Coverage**: 82/82 tests passing across all components  
**Status**: Production-ready with intelligent multi-agent orchestration

### ✅ Phase 1: FULLY COMPLETED - All Foundation Agents Operational
**Completion Date**: August 14, 2025  
**Total Test Coverage**: 68/68 tests passing across all agents  
**Status**: Production-ready with live data integration

#### **Phase 0**: Foundation & Infrastructure ✅ COMPLETED
- Agent Registry Service (21/21 tests passing)
- Coordinator Service with LangGraph (14/14 tests passing - enhanced to 14/14)  
- Base Agent Framework/Agent SDK (16/16 tests passing)

#### **Phase 2**: Intelligent Coordinator Implementation ✅ COMPLETED  
- **Smart Request Routing**: LLM-based intent classification with fallback (14/14 tests passing)
- **Multi-Agent Orchestration**: Advanced LangGraph workflow with 4-node execution
- **Live Agent Integration**: HTTP communication framework with all operational agents
- **Policy Engine Integration**: Real-time compliance checking and approval workflows
- **Performance**: ~400ms coordination latency with graceful error handling

#### **Phase 1.1**: Mail Agent ✅ COMPLETED WITH LIVE INTEGRATION
- Live Apple Mail integration working (19/19 tests passing)
- **NEW**: Replaced mock data with bridge-first live data integration
- **NEW**: Contextual reply generation with message content analysis
- Performance: first request ~44s, cached requests ~0.008s
- Bridge caching with 120s TTL

#### **Phase 1.2**: Contacts Agent ✅ COMPLETED WITH ENRICHMENT
- Contact management and enrichment agent (25/25 tests passing)
- Three capabilities: resolve, enrich, merge
- **Phase 1.2.2**: ✅ Live macOS Contacts.app integration
  - Performance: first request ~4-30s (JXA), cached requests ~0.001s (120s TTL)
  - Integration test suite: 13/14 tests passing (92.9% success rate)
- **Phase 1.2.3**: ✅ Contact Enrichment Integration  
  - Message analysis with cross-agent memory integration (10/10 tests passing)
  - Pattern-based enrichment from iMessage, Email, WhatsApp conversations
  - Cross-agent communication framework operational

#### **Phase 1.3**: Memory/RAG Agent ✅ COMPLETED
- Semantic storage and retrieval with ChromaDB + Ollama (24/24 tests passing)
- **NEW**: Fixed deprecated datetime usage - no warnings in test suite
- Cross-agent integration for enrichment data storage
- Performance optimized vector similarity search

### 🔄 Next Phase: Phase 3 Communication & Integration Agents
**Status**: Ready to begin - Intelligent coordinator operational  
**Priority**: WhatsApp, iMessage, and Calendar agent implementation

## Development Setup

### Quick Start (All Services)
```bash
# Terminal 1: Agent Registry
cd services/agent-registry && python3 -m uvicorn src.main:app --port 8001

# Terminal 2: Coordinator  
cd services/coordinator && python3 -m uvicorn src.main:app --port 8002

# Terminal 3: Mail Agent
cd services/mail-agent && python3 -m uvicorn src.main:app --port 8000

# Terminal 4: Bridge (Live Mode)
cd bridge && MAIL_BRIDGE_MODE=live python3 app.py
```

### Individual Service Setup
1. **Agent Registry** (Port 8001): `cd services/agent-registry && python3 -m uvicorn src.main:app --port 8001`
2. **Coordinator** (Port 8002): `cd services/coordinator && python3 -m uvicorn src.main:app --port 8002`
3. **Mail Agent** (Port 8000): `cd services/mail-agent && python3 -m uvicorn src.main:app --port 8000`
4. **Bridge** (Port 5100): `cd bridge && MAIL_BRIDGE_MODE=live python3 app.py`

### Environment Variables
```bash
# Bridge Mode
export MAIL_BRIDGE_MODE=live  # or 'demo' for test data

# Mail Agent Bridge URL
export MAC_BRIDGE_URL=http://127.0.0.1:5100
```

## Testing

### Unit Tests
```bash
# Run in each service directory
python3 -m pytest tests/ -v
```

### Integration Tests
```bash
# Mail Agent E2E Test
curl -X POST http://localhost:8000/capabilities/messages.search \
  -H "Content-Type: application/json" \
  -d '{"input": {"mailbox": "Inbox", "limit": 3}}'

# Bridge Direct Test  
curl "http://localhost:5100/v1/mail/messages?mailbox=Inbox&limit=3"
```

### Performance Testing
- **First Request**: ~44 seconds (JXA execution)
- **Cached Requests**: ~0.008 seconds (instant)
- **Cache Duration**: 2 minutes

## Next Feature Development

### Phase 3: Communication & Integration Agents 🔄 **NEXT PRIORITY**
**Objective**: Implement WhatsApp, iMessage, and Calendar agents with coordinator integration
**Prerequisites**: ✅ All Phase 1 agents operational + Phase 2 coordinator complete  
**Status**: Ready to begin - Intelligent coordinator foundation complete

**Planned Implementation**:

- [ ] **WhatsApp Agent** 
  - Local WhatsApp integration with read-only capabilities
  - Local image understanding using OCR/vision models (per ADR-0019)
  - Chat history search and reply proposal generation
  - No network egress - fully local operation

- [ ] **iMessage Agent**
  - macOS Bridge integration for iMessage access
  - Message reading, searching, and reply proposals
  - Integration with existing bridge architecture
  - Read operations without approval, write operations with approval

- [ ] **Calendar Agent**
  - Apple Calendar integration via macOS APIs
  - Event proposal and creation capabilities
  - Approval workflow integration with coordinator policy engine
  - Constraint-based scheduling logic

- [ ] **Enhanced Multi-Agent Workflows**
  - Cross-agent coordination via intelligent coordinator
  - Complex workflows spanning multiple communication platforms
  - Policy-driven approval processes for sensitive operations
  - Performance optimization for real-time coordination

**Success Criteria**:
- Communication agents integrate seamlessly with coordinator orchestration
- Multi-platform workflows execute through intelligent routing
- Policy engine enforces approval requirements for write operations
- Performance meets real-time interaction requirements
- All agents maintain local-first privacy principles

### Phase 2 Completion Summary ✅ **COMPLETED**
**Final Status**: Intelligent coordinator orchestration operational with live agent communication
**Completion Date**: August 15, 2025
- ✅ All test failures resolved (82/82 tests passing across all components)
- ✅ Smart request routing with LLM-based intent classification
- ✅ Multi-agent orchestration with parallel, sequential, and single-agent strategies
- ✅ Live agent integration via HTTP communication framework
- ✅ Policy engine integration with real-time compliance checking
- ✅ Performance optimization with ~400ms coordination latency
- ✅ **NEW**: End-to-end coordinator orchestration validated with live agent communication
- ✅ **NEW**: Agent discovery and registration system fully operational
- ✅ **NEW**: Live Apple Mail integration through coordinator (30s initial, 3s cached)

**Quick Setup for Coordinator Testing**:
```bash
# 1. Install Agent SDK: pip3 install -e services/agent-sdk/
# 2. Start all services (see Quick Start above)
# 3. Register agents with registry (automatically done on startup)
# 4. Test coordinator: curl http://localhost:8002/coordinator/graph
# 5. Test orchestration: POST to coordinator/process with user requests
# 6. Verify multi-agent workflows execute correctly with policy compliance
```

## Agent Registration & Startup Procedures

### Prerequisites
```bash
# Install Kenny Agent SDK
cd services/agent-sdk && pip3 install -e .
```

### Service Startup Order
1. **Agent Registry** (Port 8001): Central service discovery
2. **Agent Services** (Ports 8000, 8003, 8004): Individual agents
3. **Bridge** (Port 5100): Live data integration
4. **Coordinator** (Port 8002): Orchestration service

### Agent Registration Process
Each agent automatically registers with the registry on startup using:
- Agent ID: `mail-agent`, `contacts-agent`, `memory-agent`
- Health endpoint: `http://localhost:PORT/health`  
- Capabilities: Defined in agent manifest
- Data scopes: Following pattern `domain:subdomain`

### Validation Commands
```bash
# Check agent registration
curl -s http://localhost:8001/agents | jq '.[]'

# Test coordinator discovery  
curl -s http://localhost:8002/agents | jq '.count'

# Test end-to-end orchestration
curl -X POST http://localhost:8002/coordinator/process \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Search my inbox for recent emails"}'
```

### Phase 1 Completion Summary ✅ **COMPLETED**
**Final Status**: All foundation agents operational with live data integration
**Cleanup Completed**: August 14, 2025
- ✅ All test failures resolved (68/68 tests passing)
- ✅ Mock data replaced with live bridge integration where appropriate  
- ✅ Deprecated code patterns fixed (datetime warnings resolved)
- ✅ Cross-agent communication framework validated and operational

## Development Patterns

### Agent Development (Using Agent SDK)
1. **Extend BaseAgent**: Inherit from `kenny_agent.base_agent.BaseAgent`
2. **Create Capability Handlers**: Extend `BaseCapabilityHandler`
3. **Register Tools**: Use `register_tool()` for external integrations
4. **Health Monitoring**: Implement health checks and monitoring

### Bridge Integration
1. **Add Endpoints**: New routes in `bridge/app.py`
2. **Environment Modes**: Support demo/live via env vars
3. **Caching Strategy**: Implement appropriate TTL for data
4. **Error Handling**: Graceful fallbacks and logging

### Testing Strategy
1. **Unit Tests**: Test individual components
2. **Integration Tests**: Test service interactions
3. **E2E Tests**: Full workflow validation
4. **Performance Tests**: Measure response times and caching

## Notes
- **Local-First**: All operations default to local processing
- **Network Egress**: Strictly controlled via allowlist per ADR-0012
- **Approval Workflows**: Calendar actions require explicit human approval via Web Chat
- **Privacy**: All data processing occurs locally with user control
- **Extensibility**: New agents can be added without coordinator changes
