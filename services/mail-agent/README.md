# Mail Agent

The Mail Agent is a dedicated service agent in the Kenny v2 multi-agent system that provides read-only mail functionality including search, read, and reply proposals.

## Overview

The Mail Agent extracts mail functionality from the main API service and provides it through a dedicated agent interface. It integrates with the macOS Bridge service to access mail data and provides three main capabilities:

- **messages.search** - Search mail messages by query and filters
- **messages.read** - Read full message content by ID  
- **messages.propose_reply** - Generate reply suggestions for messages

## Architecture

The Mail Agent is built using the Kenny Agent SDK and follows the established patterns:

- **BaseAgent** - Extends the base agent class with mail-specific functionality
- **Capability Handlers** - Implement specific mail operations
- **Tools** - Integrate with external services (macOS Bridge)
- **FastAPI** - Exposes REST endpoints for capability execution

## Capabilities

### messages.search

Search for mail messages using various filters.

**Input Schema:**
```json
{
  "query": "string",
  "from": "string",
  "to": "string", 
  "mailbox": "Inbox|Sent",
  "since": "date-time",
  "until": "date-time",
  "limit": "integer (1-500)"
}
```

**Output Schema:**
```json
{
  "results": [
    {
      "id": "string",
      "thread_id": "string|null",
      "from": "string|null",
      "to": ["string"],
      "subject": "string|null",
      "snippet": "string|null",
      "ts": "date-time",
      "mailbox": "string|null"
    }
  ],
  "count": "integer"
}
```

### messages.read

Read full message content by message ID.

**Input Schema:**
```json
{
  "id": "string"
}
```

**Output Schema:**
```json
{
  "id": "string",
  "headers": "object",
  "body_text": "string|null",
  "body_html": "string|null"
}
```

### messages.propose_reply

Generate reply suggestions for a message.

**Input Schema:**
```json
{
  "id": "string",
  "context": "string"
}
```

**Output Schema:**
```json
{
  "suggestions": ["string"]
}
```

## Safety Features

All capabilities are marked with safety annotations:
- **read-only** - No data modification
- **local-only** - No network egress
- **no-egress** - No external data transmission

## Data Scopes

The Mail Agent has access to:
- `mail:inbox` - Inbox mail messages
- `mail:sent` - Sent mail messages

## Tool Access

The Mail Agent requires access to:
- `macos-bridge` - macOS Bridge service for mail operations
- `sqlite-db` - Local SQLite database for message storage
- `ollama` - Local LLM for reply generation

## Configuration

### Environment Variables

- `MAC_BRIDGE_URL` - URL for the macOS Bridge service (default: `http://localhost:5100`)

### Live Data E2E Check

1. Start the bridge in live mode:
```bash
cd bridge
MAIL_BRIDGE_MODE=live python3 app.py
```
2. Start the mail agent:
```bash
cd services/mail-agent
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```
3. Verify via agent (expect non-mock results):
```bash
curl -s -X POST http://localhost:8000/capabilities/messages.search \
  -H "Content-Type: application/json" \
  -d '{"input": {"mailbox": "Inbox", "limit": 3}}' | jq .
```

### Health Check

- **Endpoint**: `/health`
- **Interval**: 60 seconds
- **Timeout**: 10 seconds

## API Endpoints

### Health Check
- `GET /health` - Agent health status

### Capabilities
- `GET /capabilities` - List all available capabilities
- `POST /capabilities/{verb}` - Execute a capability

### Information
- `GET /` - Agent information and status

## Development

### Prerequisites

- Python 3.11+
- Kenny Agent SDK
- FastAPI
- Uvicorn

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up the Agent SDK:
```bash
# From the project root
cd services/agent-sdk
pip install -e .
```

### Running Locally

```bash
cd services/mail-agent
python3 -m uvicorn src.main:app --host 0.0.0.0 --port 8000
```

### Testing

Run the test suite:
```bash
python3 -m pytest tests/ -v
```

Run the integration test:
```bash
python3 test_server.py
```

### Docker

Build the container:
```bash
docker build -t mail-agent .
```

Run the container:
```bash
docker run -p 8000:8000 mail-agent
```

## Integration

### Agent Registry

The Mail Agent registers with the Agent Registry using a manifest that conforms to the registry schema. The manifest includes:

- Agent identification and metadata
- Capability definitions with input/output schemas
- Safety annotations and data scopes
- Tool access requirements
- Health check configuration

### Coordinator

The Coordinator service can discover and invoke Mail Agent capabilities through:

1. **Discovery**: Query the registry for available capabilities
2. **Execution**: POST to `/capabilities/{verb}` with input parameters
3. **Health Monitoring**: Regular health checks via `/health` endpoint

## Future Enhancements

- **Full Message Retrieval**: Integrate with macOS Bridge for complete message content
- **LLM Integration**: Use local Ollama models for intelligent reply generation
- **Search Optimization**: Implement advanced search algorithms and indexing
- **Caching**: Add message caching for improved performance
- **Threading**: Support for conversation threading and context

## Security

- **Local-First**: All operations occur locally with no external data transmission
- **Read-Only**: No message modification or sending capabilities
- **Access Control**: Strict data scope limitations
- **Audit Logging**: All operations are logged for compliance

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure the Agent SDK is properly installed and in the Python path
2. **Connection Errors**: Verify the macOS Bridge service is accessible
3. **Schema Validation**: Check that capability schemas match the registry requirements

### Health Checks

Monitor the `/health` endpoint for:
- Agent operational status
- Capability registration status
- Tool accessibility
- Overall system health

## License

This project is part of the Kenny v2 multi-agent system and follows the same licensing terms.
