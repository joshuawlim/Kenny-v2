# Agent SDK Template

This template provides everything needed to create a new agent for the Kenny multi-agent system.

## Quick Start

1. **Copy the template**: Clone this directory and rename it for your agent
2. **Define capabilities**: Update `manifest.json` with your agent's capabilities
3. **Implement handlers**: Add your business logic in the handler functions
4. **Test**: Use the provided test harness to verify functionality
5. **Register**: Your agent will automatically register with the Agent Registry

## Directory Structure

```
agent-sdk-template/
├── README.md                 # This file
├── manifest.json            # Agent capability definition
├── agent.py                 # Main agent implementation
├── handlers/                # Capability handlers
│   ├── __init__.py
│   └── example_handler.py
├── tools/                   # Tool integrations
│   ├── __init__.py
│   └── example_tool.py
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_agent.py
│   └── test_handlers.py
├── requirements.txt          # Python dependencies
└── Dockerfile               # Container definition
```

## Creating Your Agent

### 1. Define Capabilities

Update `manifest.json` to declare what your agent can do:

```json
{
  "agent_id": "your-agent-name",
  "display_name": "Your Agent Display Name",
  "description": "What your agent does",
  "capabilities": [
    {
      "verb": "your.action",
      "input_schema": {
        "type": "object",
        "properties": {
          "input_param": {"type": "string"}
        }
      },
      "output_schema": {
        "type": "object",
        "properties": {
          "result": {"type": "string"}
        }
      },
      "safety_annotations": ["read-only"],
      "description": "What this capability does"
    }
  ],
  "data_scopes": ["your:data"],
  "tool_access": ["your-tool"],
  "egress_domains": []
}
```

### 2. Implement Handlers

Create handlers for each capability in the `handlers/` directory:

```python
# handlers/your_handler.py
from typing import Dict, Any
from ..base_handler import BaseHandler

class YourActionHandler(BaseHandler):
    """Handler for your.action capability"""
    
    def handle(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Your business logic here
        input_param = inputs.get("input_param", "")
        
        # Process the request
        result = self._process_input(input_param)
        
        return {
            "result": result,
            "metadata": {
                "processed_at": self._get_timestamp(),
                "confidence": 0.95
            }
        }
    
    def _process_input(self, input_param: str) -> str:
        # Implement your processing logic
        return f"Processed: {input_param}"
```

### 3. Add Tools

Implement tools your agent needs in the `tools/` directory:

```python
# tools/your_tool.py
class YourTool:
    """Integration with external service or local resource"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._initialize()
    
    def _initialize(self):
        # Setup connections, load configs, etc.
        pass
    
    def do_something(self, param: str) -> str:
        # Implement tool functionality
        return f"Tool result: {param}"
```

### 4. Update Main Agent

Modify `agent.py` to include your handlers and tools:

```python
# agent.py
from .handlers.your_handler import YourActionHandler
from .tools.your_tool import YourTool

class YourAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Initialize tools
        self.your_tool = YourTool(config.get("your_tool", {}))
        
        # Register handlers
        self.register_handler("your.action", YourActionHandler())
    
    def get_manifest(self) -> Dict[str, Any]:
        # Load and return your manifest.json
        return self._load_manifest()
```

## Testing

### Run Tests

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=. --cov-report=html
```

### Test Your Capabilities

```python
# tests/test_handlers.py
def test_your_action_handler():
    handler = YourActionHandler()
    inputs = {"input_param": "test input"}
    
    result = handler.handle(inputs)
    
    assert "result" in result
    assert result["result"] == "Processed: test input"
```

## Deployment

### Local Development

```bash
# Run agent locally
python agent.py

# Or with uvicorn for HTTP interface
uvicorn agent:app --host 0.0.0.0 --port 8000
```

### Docker

```bash
# Build image
docker build -t your-agent .

# Run container
docker run -p 8000:8000 your-agent
```

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: your-agent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: your-agent
  template:
    metadata:
      labels:
        app: your-agent
    spec:
      containers:
      - name: your-agent
        image: your-agent:latest
        ports:
        - containerPort: 8000
```

## Best Practices

### Security
- **Least privilege**: Only request access to tools and data you need
- **Input validation**: Always validate and sanitize inputs
- **Error handling**: Don't expose sensitive information in error messages
- **Audit logging**: Log all operations for debugging and compliance

### Performance
- **Async operations**: Use async/await for I/O operations
- **Caching**: Cache frequently accessed data when appropriate
- **Rate limiting**: Respect rate limits and implement backoff
- **Resource cleanup**: Properly close connections and clean up resources

### Reliability
- **Health checks**: Implement comprehensive health checks
- **Circuit breakers**: Add circuit breakers for external dependencies
- **Retry logic**: Implement exponential backoff for transient failures
- **Monitoring**: Expose metrics for observability

### Testing
- **Unit tests**: Test individual components in isolation
- **Integration tests**: Test interactions with external services
- **End-to-end tests**: Test complete user workflows
- **Performance tests**: Verify performance under load

## Troubleshooting

### Common Issues

1. **Agent not registering**: Check manifest.json format and network connectivity
2. **Capability not found**: Verify verb format matches `domain.action` pattern
3. **Tool access denied**: Ensure tool_access includes required tools
4. **Health check failing**: Verify health endpoint is accessible

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Health Check

Test your agent's health endpoint:

```bash
curl http://localhost:8000/health
```

## Getting Help

- **Documentation**: Check the main architecture docs
- **Examples**: Look at existing agents for reference
- **Issues**: Report bugs and request features via GitHub
- **Community**: Join the Kenny development community

## Next Steps

1. **Review existing agents**: Study how other agents are implemented
2. **Test thoroughly**: Ensure your agent works reliably
3. **Document**: Add clear documentation for your capabilities
4. **Contribute**: Share improvements back to the community
