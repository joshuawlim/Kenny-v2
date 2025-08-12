# Session Continuation Prompt

**Project**: Kenny v2 - Multi-Agent Personal Assistant Migration  
**Current Status**: Infrastructure cleaned up, ready to begin Phase 0.1  
**Last Session**: Completed infrastructure review and cleanup  

### **What Was Accomplished:**
- ✅ Reviewed and analyzed current Docker infrastructure against new multi-agent architecture
- ✅ Stopped and removed `workers` container (not aligned with agent-based design)
- ✅ Cleaned up docker-compose.yml (removed workers service and unused volumes)
- ✅ Confirmed current running services: postgres, api, ui, proxy
- ✅ Infrastructure now properly aligned for multi-agent migration
- ✅ **COMPLETED**: Updated data model to support multi-agent architecture (Phase 0.1 prerequisite)

### **Current Architecture State:**
- **Running Containers**: postgres, api, ui, proxy
- **API Service**: Will be refactored into coordinator (Phase 0.2)
- **Workers**: Functionality will be distributed to individual agents
- **Database**: PostgreSQL remains for cross-agent data storage
- **Proxy**: Caddy will be updated to route to new agent services

### **Next Phase to Implement:**
**Phase 0.1: Agent Registry Service** *(Data Model Prerequisite: ✅ COMPLETED)*

**Objective**: Create central service for agent registration and capability discovery

**Components to Build**:
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

**API Endpoints to Implement**:
- `POST /agents/register` - Agent registration
- `GET /agents` - List all registered agents
- `GET /agents/{agent_id}` - Get agent details
- `GET /capabilities` - List all available capabilities
- `GET /capabilities/{verb}` - Get capability details

**Success Measures** (from roadmap):
- [ ] Agent Registry service starts and responds to health checks
- [ ] Agent manifests can be registered and validated against schema
- [ ] Capability discovery returns accurate agent listings
- [ ] Health monitoring detects agent status changes
- [ ] All endpoints return proper HTTP status codes and error messages

### **Key Context for Next Session:**
- **Working Directory**: `/Users/joshwlim/Documents/Kenny v2`
- **Architecture**: Coordinator-led multi-agent system with LangGraph
- **Local-First**: All operations default to local processing
- **Network Egress**: Strictly controlled via allowlist per ADR-0012
- **Approval Workflows**: Calendar actions require explicit human approval via Web Chat
- **Current API**: Embedded in `services/api/src/index.js` (will be extracted to agents)

### **Files to Reference:**
- `docs/architecture/schemas/agent-manifest.json` - Agent manifest schema
- `docs/architecture/multi-agent-architecture.md` - Multi-agent architecture spec
- `docs/architecture/decision-records/ADR-0023-agent-manifest-and-registry.md` - Registry design decisions
- `roadmap.md` - Complete project roadmap with success measures

### **Next Session Goals:**
1. Create the Agent Registry service directory structure
2. Implement FastAPI application with agent registration endpoints
3. Create Pydantic models for agent manifests and capabilities
4. Implement JSON Schema validation for agent registration
5. Add health check monitoring for registered agents
6. Create basic tests for the registry functionality
7. Integrate with existing docker-compose infrastructure

**Ready to proceed with Phase 0.1 Agent Registry Service implementation. Data model foundation is complete.**
