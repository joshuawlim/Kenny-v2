# Kenny v2 System Prompt

## Project Overview
Kenny v2 is a local-first, multi-agent personal assistant system built with Python FastAPI services and LangGraph orchestration. The system prioritizes privacy and local data processing while providing intelligent automation capabilities.

## Architecture
- **Multi-Agent System**: Coordinator-led orchestration using LangGraph
- **Local-First**: All processing occurs locally with no external dependencies
- **Privacy-Focused**: User data never leaves the local environment
- **Modular Design**: Agents can be developed and deployed independently

## Current Status
- **Phase 0**: Foundation & Infrastructure ✅ COMPLETED
  - Agent Registry Service (21/21 tests passing)
  - Coordinator Service with LangGraph (14/14 tests passing)
  - Base Agent Framework/Agent SDK (16/16 tests passing)
- **Phase 1.1**: Mail Agent ✅ COMPLETED WITH PERFORMANCE OPTIMIZATIONS
  - Live Apple Mail integration working
  - Performance: first request ~44s, cached requests ~0.008s
  - Bridge caching with 120s TTL

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

### Phase 1.2: Contacts Agent (Ready to Begin)
**Prerequisites**: ✅ All Phase 0 + Phase 1.1 complete
**Objective**: Create agent for contact management and enrichment

**Quick Setup for Next Feature**:
```bash
# 1. Ensure all services are running (see Quick Start above)
# 2. Create new agent directory: services/contacts-agent/
# 3. Follow Agent SDK patterns from mail-agent
# 4. Add bridge endpoints in bridge/app.py for contacts
# 5. Test with coordinator integration
```

**Success Measures**:
- [ ] Contacts agent starts and registers with agent registry
- [ ] Contact resolution can find and disambiguate contacts  
- [ ] Contact enrichment adds additional information
- [ ] Contact merging handles duplicate resolution
- [ ] Local contacts database integration works correctly

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
