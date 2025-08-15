# Kenny v2 - Local-First Multi-Agent Personal Assistant

**Status**: 🎉 **Production Ready** - Phase 7.1 Complete  
**Architecture**: Coordinator-led multi-agent system with LangGraph orchestration  
**Last Updated**: August 15, 2025

Kenny v2 is a local-first, privacy-focused multi-agent personal assistant system that keeps all your data on your device while providing intelligent automation across email, messaging, calendar, and contacts. Now includes complete one-click service management for effortless deployment and monitoring.

---

## 🚀 Quick Start

### Prerequisites
- **macOS** (required for Mail, Contacts, Calendar, iMessage integration)
- **Ollama** (`brew install ollama`)
- **Python 3.11+**, **Node.js 18+**, **Xcode Command Line Tools**

### 1. Install Dependencies
```bash
# Install Ollama and models
brew install ollama
ollama pull llama3.2:3b
ollama pull nomic-embed-text

# Install Agent SDK
cd services/agent-sdk && pip3 install -e .
```

### 2. Grant macOS Permissions
**System Settings → Privacy & Security**:
- Full Disk Access for your terminal/editor
- Accessibility permissions
- Automation permissions

### 3. ⚡ One-Click Launch (Recommended)
```bash
# Start Kenny with comprehensive service management
./kenny-launch.sh

# Monitor services in real-time (in another terminal)
./kenny-status.sh --watch

# Check system health
./kenny-health.sh

# Stop all services cleanly
./kenny-stop.sh
```

### 4. Alternative: Manual Service Start
```bash
# Start core services
cd services/agent-registry && python3 -m uvicorn src.main:app --port 8001 &
cd services/coordinator && python3 -m src.main &
cd services/gateway && python3 -m src.main &

# Start foundation agents
cd services/mail-agent && python3 -m uvicorn src.main:app --port 8000 &
cd services/contacts-agent && python3 -m uvicorn src.main:app --port 8003 &
cd services/memory-agent && python3 -m uvicorn src.main:app --port 8004 &

# Start communication agents
cd services/whatsapp-agent && python3 -m uvicorn src.main:app --port 8005 &
cd services/imessage-agent && python3 -m uvicorn src.main:app --port 8006 &
cd services/calendar-agent/src && PYTHONPATH="../../agent-sdk" python3 main.py &

# Start Bridge for live data
cd bridge && MAIL_BRIDGE_MODE=live IMESSAGE_BRIDGE_MODE=live CALENDAR_BRIDGE_MODE=live python3 app.py &
```

### 5. Test the System
```bash
# Check system health
curl http://localhost:9000/health

# Test direct agent call
curl -X POST http://localhost:9000/agent/mail-agent/messages.search \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"mailbox": "Inbox", "limit": 3}}'

# Test multi-agent workflow
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "search my emails for meeting invites and check my calendar", "context": {}}'
```

---

## 🏗️ System Architecture

Kenny v2 uses a **unified API gateway** that intelligently routes requests to either:
- **Direct agents** for simple, single-capability requests
- **Coordinator** for complex, multi-agent workflows

### Core Services
- **Gateway** (Port 9000): Unified user interface with intelligent routing
- **Coordinator** (Port 8002): Multi-agent orchestration using LangGraph
- **Agent Registry** (Port 8001): Service discovery and health monitoring

### 7 Operational Agents
- **Mail Agent** (8000): Apple Mail integration with live data
- **Contacts Agent** (8003): macOS Contacts with enrichment
- **Memory Agent** (8004): Semantic storage using ChromaDB + Ollama
- **WhatsApp Agent** (8005): Local image understanding with OCR
- **iMessage Agent** (8006): Native Messages.app integration
- **Calendar Agent** (8007): Apple Calendar with approval workflows

---

## 🔒 Privacy & Security

### Local-First Architecture (ADR-0019)
- ✅ **Zero External Dependencies**: All processing occurs locally
- ✅ **Data Sovereignty**: Your data never leaves your device
- ✅ **Network Egress Control**: Strict allowlist for necessary connections only
- ✅ **Real-time Compliance**: Continuous monitoring and validation

### Security Features
- **Real-time Security Dashboard**: Live monitoring at `http://localhost:8001/security/ui`
- **Automated Incident Response**: 11 response action types with containment
- **Network Enforcement**: Active blocking of unauthorized connections
- **Privacy Validation**: Continuous ADR-0019 compliance checking

---

## 🎯 Key Features

### Intelligent Routing
The Gateway automatically determines whether to:
- Route simple requests directly to specific agents (1.2ms response time)
- Route complex workflows to the Coordinator for multi-agent orchestration (<30ms)

### Multi-Agent Workflows
```bash
# Example: Complex workflow involving multiple agents
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "find emails from Sarah and schedule a follow-up meeting", 
    "context": {}
  }'
```
This automatically:
1. Routes to Coordinator (intelligent intent classification)
2. Searches emails using Mail Agent
3. Resolves "Sarah" using Contacts Agent  
4. Proposes meeting times using Calendar Agent
5. Returns unified results with execution details

### Progressive Streaming
```bash
# Real-time workflow progress via WebSocket
wscat -c ws://localhost:9000/stream
> {"query": "complex workflow involving multiple agents", "context": {}}
< {"type": "node_start", "node": "router", "message": "Analyzing request intent..."}
< {"type": "node_complete", "node": "router", "result": {...}}
< {"type": "agent_start", "agent_id": "mail-agent", "capability": "messages.search"}
< {"type": "agent_complete", "agent_id": "mail-agent", "result": {...}}
< {"type": "final_result", "result": {...}}
```

---

## 📊 Performance

### Response Times (Production Ready)
- **Direct Agent Routing**: 1.2ms average
- **Coordinator Integration**: <30ms 
- **Live Data Operations**: 44s initial, 0.008s cached
- **Health Checks**: <400ms

### System Metrics
- **Total Test Coverage**: 100% of implemented features
- **Uptime Target**: 99.9% with graceful degradation
- **Memory Usage**: Optimized for local operation
- **Security Overhead**: <100ms for comprehensive monitoring

---

## 🧪 Testing

### Integration Tests
```bash
# Gateway and coordinator integration
python3 test_phase_5_2_coordinator_integration.py

# Security and observability
python3 test_phase_4_observability.py
python3 test_phase_4_3_security.py

# Live data integration
python3 test_contacts_live_integration.py
```

### Individual Agent Tests
```bash
# Mail Agent
cd services/mail-agent && python3 -m pytest tests/ -v

# Coordinator
cd services/coordinator && python3 -m pytest tests/ -v

# All agents
find services -name "test_*.py" -exec python3 {} \;
```

---

## 📋 API Reference

### Gateway API (Port 9000)
```bash
# System Information
GET  /health                           # System health and status
GET  /agents                           # Available agents
GET  /capabilities                     # All available capabilities

# Unified Query Interface
POST /query                            # Intelligent routing (direct or coordinator)
  Body: {"query": "user request", "context": {}}

# WebSocket Streaming  
WS   /stream                           # Real-time progressive responses

# Direct Agent Access
POST /agent/{agent_id}/{capability}   # Direct capability invocation
GET  /agent/{agent_id}/capabilities   # Agent-specific capabilities
```

### Example Requests
```bash
# Health check
curl http://localhost:9000/health

# Direct mail search
curl -X POST http://localhost:9000/agent/mail-agent/messages.search \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"mailbox": "Inbox", "limit": 5}}'

# Multi-agent workflow
curl -X POST http://localhost:9000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "coordinate between multiple agents for workflow", "context": {}}'

# Contact resolution
curl -X POST http://localhost:9000/agent/contacts-agent/contacts.resolve \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"name": "John Smith"}}'

# Calendar event proposal
curl -X POST http://localhost:9000/agent/calendar-agent/calendar.propose_event \
  -H "Content-Type: application/json" \
  -d '{"parameters": {"title": "Team Meeting", "start": "2025-08-16T14:00:00Z", "end": "2025-08-16T15:00:00Z"}}'
```

---

## 🛠️ Development

### Agent Development
```bash
# Create new agent using Agent SDK
cd services/agent-sdk
python3 example_usage.py

# Test agent installation
python3 test_installation.py
```

### Adding New Capabilities
1. **Extend BaseAgent**: Inherit from `kenny_agent.base_agent.BaseAgent`
2. **Create Handler**: Extend `BaseCapabilityHandler` 
3. **Register Tools**: Use `register_tool()` for external integrations
4. **Health Monitoring**: Implement health checks

### Architecture Decision Records (ADRs)
See `docs/architecture/decision-records/` for design decisions:
- **ADR-0019**: Local-first architecture principles
- **ADR-0021**: Multi-agent architecture
- **ADR-0022**: LangGraph orchestration framework
- **ADR-0023**: Agent manifest and registry

---

## 🎛️ Monitoring & Observability

### Health Dashboards
```bash
# System health with real-time updates
curl http://localhost:8001/system/health/dashboard

# Live health streaming (SSE)
curl http://localhost:8001/system/health/dashboard/stream

# Security dashboard
open http://localhost:8001/security/ui
```

### Request Tracing
```bash
# View all traces
curl http://localhost:8001/traces

# Specific trace by correlation ID
curl http://localhost:8001/traces/{correlation_id}

# Performance analytics
curl http://localhost:8001/analytics/dashboard
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Bridge modes (live/demo)
export MAIL_BRIDGE_MODE=live
export IMESSAGE_BRIDGE_MODE=live  
export CALENDAR_BRIDGE_MODE=live

# Service URLs
export MAC_BRIDGE_URL=http://127.0.0.1:5100
export COORDINATOR_URL=http://localhost:8002
export AGENT_REGISTRY_URL=http://localhost:8001
```

### Network Egress Control
By default, only these connections are allowed:
- `localhost`, `127.0.0.1`, `*.kenny.local`
- Ollama: `http://localhost:11434`
- Bridge: `http://localhost:5100`
- NTP: `time.apple.com` (port 123 only)

---

## 📦 Project Structure

```
Kenny v2/
├── PROJECT_STATUS.md              # Complete project status and roadmap
├── README.md                      # This file
├── PHASE_4_3_SECURITY_DEPLOYMENT.md # Security deployment guide
├── kenny-launch.sh                # One-click launcher script
├── kenny-health.sh                # System health monitoring
├── kenny-status.sh                # Real-time service status
├── kenny-stop.sh                  # Clean shutdown script
├── bridge/                        # macOS integration bridge
├── docs/                          # Architecture documentation
├── infra/                         # Docker and infrastructure
├── services/
│   ├── agent-registry/            # Service discovery
│   ├── agent-sdk/                 # Agent development framework
│   ├── coordinator/               # Multi-agent orchestration
│   ├── gateway/                   # Unified API gateway
│   ├── dashboard/                 # React dashboard
│   ├── mail-agent/                # Apple Mail integration
│   ├── contacts-agent/            # Contacts management
│   ├── memory-agent/              # Semantic storage
│   ├── whatsapp-agent/            # WhatsApp integration
│   ├── imessage-agent/            # iMessage integration
│   └── calendar-agent/            # Calendar management
└── test_*.py                      # Integration test suites
```

---

## 🏆 Project Status

### ✅ Completed Phases
- **Phase 0**: Foundation & Infrastructure (51/51 tests ✅)
- **Phase 1**: Foundation Agents (68/68 tests ✅) 
- **Phase 2**: Intelligent Coordinator (82/82 tests ✅)
- **Phase 3**: Communication Agents (100% coverage ✅)
- **Phase 4**: Observability & Safety (comprehensive validation ✅)
- **Phase 5**: User Interface & API Gateway (5/5 test suites ✅)
- **Phase 6**: React Dashboard Web Interface (comprehensive testing ✅)
- **Phase 7.1**: Service Management Scripts (complete suite ✅)

### 🎯 Next: Phase 7.2 - User Experience Enhancements
- Kenny persona integration in chat interface
- Setup wizard in React dashboard
- Non-technical user documentation
- Enhanced user-friendly features

---

## 🤝 Contributing

### Making Architecture Decisions
1. Create an ADR using `docs/architecture/templates/adr-template.md`
2. Link the ADR in your PR with summary
3. Update diagrams/specs as needed

### Development Workflow  
1. Follow success criteria → tests → minimal implementation
2. Use Agent SDK for new agents
3. Maintain 100% test coverage
4. Document all design decisions

---

## 📄 License

This project implements a local-first architecture following ADR-0019 privacy principles. All data processing occurs locally with user control and no external dependencies during operation.

---

**🎉 Kenny v2 is production-ready with enterprise-grade capabilities, comprehensive testing, local-first privacy controls, and effortless one-click service management.**

For detailed project status and roadmap, see `PROJECT_STATUS.md`.

*Last Updated: August 15, 2025*