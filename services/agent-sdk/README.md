# Kenny Agent SDK

Base framework for building agents in the Kenny v2 multi-agent system.

## Overview

The Kenny Agent SDK provides the foundational classes and utilities for creating agents that can register with the agent registry and execute capabilities. This SDK is designed to ensure consistency across all agents in the system while providing flexibility for agent-specific implementations.

## Features

- **BaseAgent**: Abstract base class for all agents with common functionality
- **BaseCapabilityHandler**: Framework for implementing agent capabilities
- **BaseTool**: Framework for implementing agent tools
- **Health Monitoring**: Comprehensive health check and monitoring utilities
- **Registry Integration**: Client for communicating with the agent registry service

## Installation

```bash
# Install the package
pip install -e .

# Install with development dependencies
pip install -e .[dev]

# Install with test dependencies only
pip install -e .[test]
```

## Quick Start

### Creating a Simple Agent

```python
from kenny_agent import BaseAgent, BaseCapabilityHandler
import asyncio

class SearchCapability(BaseCapabilityHandler):
    def __init__(self):
        super().__init__(
            capability="search.query",
            description="Search for information"
        )
    
    async def execute(self, parameters):
        query = parameters.get("query", "")
        return {"results": f"Search results for: {query}"}

class MyAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            agent_id="my-agent",
            name="My Agent",
            description="A simple example agent"
        )
        
        # Register capabilities
        self.register_capability(SearchCapability())
    
    async def start(self):
        print("Agent started")
    
    async def stop(self):
        print("Agent stopped")

# Usage
async def main():
    agent = MyAgent()
    await agent.start()
    
    # Execute capability
    result = await agent.execute_capability("search.query", {"query": "hello"})
    print(result)
    
    await agent.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### Health Monitoring

```python
from kenny_agent import HealthMonitor, HealthCheck, HealthStatus

# Create health checks
def check_database():
    # Simulate database check
    return HealthStatus(
        status="healthy",
        message="Database connection OK",
        details={"response_time": "5ms"}
    )

def check_external_api():
    # Simulate API check
    return HealthStatus(
        status="healthy",
        message="External API accessible",
        details={"endpoint": "https://api.example.com"}
    )

# Create health monitor
monitor = HealthMonitor("my_agent_monitor")
monitor.add_health_check(HealthCheck("database", check_database, critical=True))
monitor.add_health_check(HealthCheck("external_api", check_external_api))

# Get overall health
overall_health = monitor.get_overall_health()
print(f"Overall status: {overall_health.status}")
```

### Registry Integration

```python
from kenny_agent import AgentRegistryClient
import asyncio

async def register_agent():
    client = AgentRegistryClient(base_url="http://localhost:8000")
    
    # Generate agent manifest
    manifest = agent.generate_manifest()
    
    # Register with registry
    result = await client.register_agent(manifest)
    print(f"Registration result: {result}")
    
    # Update health status
    health_data = agent.get_health_status()
    await client.update_health(agent.agent_id, health_data)

# Run registration
asyncio.run(register_agent())
```

## Architecture

### BaseAgent

The `BaseAgent` class provides:

- Capability registration and execution
- Tool registration and management
- Health status monitoring
- Manifest generation for registry registration
- Abstract methods for start/stop lifecycle

### BaseCapabilityHandler

The `BaseCapabilityHandler` class provides:

- Capability definition and metadata
- Parameter validation
- Manifest generation
- Abstract execution method

### BaseTool

The `BaseTool` class provides:

- Tool definition and metadata
- Parameter validation
- Usage tracking
- Abstract execution method

### Health Monitoring

The health monitoring system provides:

- Individual health checks
- Health status aggregation
- Critical failure detection
- Health statistics tracking

### Registry Client

The `AgentRegistryClient` provides:

- Agent registration and unregistration
- Health status updates
- Capability discovery
- Agent search and filtering

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=kenny_agent

# Run specific test file
pytest tests/test_base_agent.py
```

### Code Quality

```bash
# Format code
black kenny_agent/

# Sort imports
isort kenny_agent/

# Lint code
flake8 kenny_agent/

# Type checking
mypy kenny_agent/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For questions and support, please open an issue on GitHub or contact the development team.
