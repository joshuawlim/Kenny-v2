# Kenny V2.1 - Development Initialization

**Current Version**: V2.0 (Production Ready)  
**Next Version**: V2.1 (Architecture & Performance Focus)  
**V2.0 Release**: See [`docs/releases/RELEASE_V2.0.md`](docs/releases/RELEASE_V2.0.md)  
**Last Updated**: August 16, 2025

---

## V2.1 Vision

Building on V2.0's production-ready foundation, V2.1 addresses critical architectural bottlenecks to achieve **intelligent agent-led services**, **optimized LLM performance**, and **sub-5 second response times** while maintaining local-first principles.

---

## V2.0 Baseline Summary

**Architecture**: 7 operational agents with LangGraph coordinator  
**Performance**: <30ms coordinator, 1.2ms direct routing (but 44s initial Mail response)  
**Interface**: React dashboard (port 3001), API Gateway (port 9000)  
**Launch**: One-click via `./kenny-launch.sh`  

**Current Bottlenecks Identified**:
- **Non-intelligent services**: Mail/Messages/Calendar/Contacts as basic API wrappers
- **Coordinator model issues**: Qwen3:8b safety triggers affecting tool engagement
- **Performance degradation**: 44s initial responses, minimal semantic caching

For complete V2.0 details, see [`docs/releases/RELEASE_V2.0.md`](docs/releases/RELEASE_V2.0.md)

---

## V2.1 Development Priorities

### Phase 1: Agent-Led Service Transformation
**Status**: Phase 1A Complete ✅ | Phase 1B Complete ✅  
**Priority**: CRITICAL  
**Timeline**: Week 1-4  
**Target**: Transform passive services into intelligent agents

**Architecture Changes**:
- ✅ **Embed llama3.2:3b or qwen2.5:3b** in each service for query interpretation
- ✅ **Implement LLM-driven interface layer**: Natural language → structured tool calls
- ✅ **Add semantic caching layer** for repeated queries and performance
- ✅ **Create AgentServiceBase class** extending current service architecture

**Service Transformation**:
```
Current: Coordinator → Direct API → Service Tools
V2.1:    Coordinator → Service LLM → Intelligent Tool Selection → Cached Results
```

**Implementation Steps**:
- ✅ **Phase 1A (Week 1-2)**: Mail Agent transformation as proof of concept
  - ✅ AgentServiceBase framework created (`services/agent-sdk/kenny_agent/agent_service_base.py`)
  - ✅ IntelligentMailAgent deployed with LLM query interpretation
  - ✅ Multi-tier semantic caching (L1/L2/L3) operational
  - ✅ Natural language query endpoint `/query` implemented
  - ✅ Performance monitoring with <5s targets established
  - ✅ Dashboard shows "intelligent_service" agent type
  - ✅ Baseline: 44s → Target: <5s response times
- ✅ **Phase 1B (Week 3-4)**: Extend to Messages, Calendar, Contacts agents
  - ✅ IntelligentContactsAgent with cross-platform enrichment and semantic matching
  - ✅ IntelligentiMessageAgent with conversation intelligence and context analysis
  - ✅ IntelligentCalendarAgent with smart scheduling and conflict resolution
  - ✅ Enhanced Coordinator with best-guess interpretation for imperfect queries
  - ✅ Confidence scoring and fallback mechanisms across all routing
  - ✅ Updated service manifests to reflect "intelligent_service" type
  - ✅ llama3.2:3b model integration validated across all services
  - ✅ Updated kenny-launch.sh to use intelligent agents by default

### Phase 2: Coordinator Model Optimization  
**Status**: Not Started  
**Priority**: HIGH  
**Timeline**: Week 5-6  
**Target**: Replace/supplement Qwen3:8b for faster, reliable tool engagement

**Analysis Framework**:
- **Benchmark Qwen3:8b vs llama3.2:3b-instruct vs qwen2.5:3b-instruct**
- **Test tool calling accuracy, latency, and safety alignment**
- **Measure end-to-end workflow completion rates**

**Recommended Strategy**:
- **Primary**: Switch to **llama3.2:3b-instruct** for speed and reliability
- **Fallback**: Keep Qwen3:8b for complex reasoning requiring multi-step thinking
- **Implement model selection logic** based on query complexity scoring
- **A/B testing framework** for model comparison

### Phase 3: Performance Architecture Optimization
**Status**: Not Started  
**Priority**: HIGH  
**Timeline**: Week 7-8  
**Target**: Sub-5 second end-to-end response times

**Multi-Tier Caching Strategy**:
- **L1 Cache**: In-memory service-level caching for recent queries
- **L2 Cache**: ChromaDB semantic cache for similar query matching  
- **L3 Cache**: SQLite persistent cache for structured data

**Performance Enhancements**:
- **Async streaming responses** with progressive result delivery
- **Parallel agent execution** where workflows allow
- **Smart result aggregation** to minimize redundant processing
- **Connection pooling** for bridge communications
- **Comprehensive performance monitoring** and bottleneck identification

---

## Technical Foundation

### Core Services
- **Gateway** (9000): Unified API with intelligent routing
- **Coordinator** (8002): Multi-agent orchestration
- **Registry** (8001): Service discovery & health
- **Dashboard** (3001): React web interface

### Key Principles
- **Local-First**: ADR-0019 compliant
- **Privacy-Focused**: No external data transmission
- **Modular Architecture**: Independent agent development
- **Intelligent Routing**: Automatic direct/coordinator selection

---

## Quick Start

```bash
# Launch all services
./kenny-launch.sh

# Monitor status
./kenny-status.sh --watch

# Access dashboard
open http://localhost:3001
```

---

## Development Resources

### Architecture
- **ADRs**: `docs/architecture/decision-records/`
- **Diagrams**: `docs/architecture/diagrams/`
- **SDK**: `services/agent-sdk/`

### Testing
```bash
# Integration tests
python3 test_phase_5_2_coordinator_integration.py

# Agent tests
cd services/{agent-name} && python3 -m pytest tests/
```

### Key Files
- **V2.0 Release**: [`docs/releases/RELEASE_V2.0.md`](docs/releases/RELEASE_V2.0.md)
- **Security**: `PHASE_4_3_SECURITY_DEPLOYMENT.md`
- **Architecture**: `docs/architecture/multi-agent-architecture.md`

---

## Success Metrics for V2.1

### Performance Targets
- **End-to-end response time**: <5 seconds (down from 44s)
- **Service intelligence**: 95%+ natural language query success rate
- **Cache hit ratio**: >80% for repeated queries
- **Tool calling accuracy**: >90% across all LLM models

### Architecture Targets  
- **Agent transformation**: 100% of services with embedded LLMs
- **Model optimization**: Coordinator latency <100ms for simple queries
- **Caching coverage**: Multi-tier implementation across all services
- **Performance monitoring**: Real-time bottleneck identification

### Deliverables
- ✅ **AgentServiceBase**: Reusable framework for intelligent services
- 🔲 **Model benchmarking**: Comprehensive performance comparison framework
- ✅ **Caching architecture**: Production-ready multi-tier system
- ✅ **Performance dashboard**: Real-time optimization monitoring

---

**Note**: This document serves as the initialization context for V2.1 development. It references V2.0 release documentation for historical context while focusing on forward-looking development priorities.