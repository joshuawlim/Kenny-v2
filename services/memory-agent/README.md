# Kenny Memory Agent

A comprehensive memory and retrieval agent that provides semantic search, embedding generation, and intelligent memory management for the Kenny v2 system.

## Features

- **Semantic Search**: Vector-based similarity search across stored memories
- **Text Embedding Generation**: Local embedding generation using Ollama models  
- **Memory Storage**: Persistent memory storage with metadata and tagging
- **Local-First**: All processing happens locally with no external API calls
- **Configurable Models**: Support for multiple embedding models
- **Caching**: Intelligent caching for improved performance
- **Retention Policies**: Automated cleanup based on configurable retention rules

## Capabilities

### `memory.retrieve`
Perform semantic search across stored memories using vector similarity.

**Parameters:**
- `query` (string, required): Search query text
- `limit` (integer, optional): Maximum results to return (default: 10)
- `similarity_threshold` (number, optional): Minimum similarity score (default: 0.7)
- `data_scopes` (array, optional): Filter by data scopes
- `time_range` (object, optional): Filter by time range

### `memory.embed`
Generate embeddings for text using local Ollama models.

**Parameters:**
- `texts` (array, required): Text(s) to generate embeddings for
- `model` (string, optional): Model to use (default: "nomic-embed-text")
- `normalize` (boolean, optional): Normalize embeddings (default: true)
- `cache_key` (string, optional): Cache key for batch operations

### `memory.store`
Store new memories with automatic embedding generation and metadata.

**Parameters:**
- `content` (string, required): Memory content to store
- `metadata` (object, required): Source, data scope, and additional metadata
- `auto_embed` (boolean, optional): Generate embeddings automatically (default: true)
- `embedding_model` (string, optional): Model for embeddings (default: "nomic-embed-text")

## Quick Start

### Prerequisites

1. **Ollama**: Install and run Ollama locally
   ```bash
   # Install Ollama (macOS)
   brew install ollama
   
   # Start Ollama service
   ollama serve
   
   # Pull required models
   ollama pull nomic-embed-text
   ```

2. **Python Dependencies**: Install required packages
   ```bash
   cd services/memory-agent
   pip install -r requirements.txt
   ```

### Running the Agent

```bash
# Start the memory agent
python3 -m uvicorn src.main:app --port 8004

# Or using the provided script
python3 src/main.py
```

The agent will be available at `http://localhost:8004`

### API Examples

#### Store a Memory
```bash
curl -X POST http://localhost:8004/capabilities/memory.store \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "content": "Meeting notes from project discussion about new features",
      "metadata": {
        "source": "calendar", 
        "data_scope": "calendar:events",
        "tags": ["meeting", "project"],
        "importance": 0.8
      }
    }
  }'
```

#### Search Memories
```bash
curl -X POST http://localhost:8004/capabilities/memory.retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "project meeting notes",
      "limit": 5,
      "similarity_threshold": 0.7
    }
  }'
```

#### Generate Embeddings
```bash
curl -X POST http://localhost:8004/capabilities/memory.embed \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "texts": ["Hello world", "Machine learning"],
      "model": "nomic-embed-text"
    }
  }'
```

## Configuration

### Environment Variables

- `MEMORY_AGENT_PORT`: Service port (default: 8004)
- `AGENT_REGISTRY_URL`: Agent registry URL (default: http://localhost:8001)
- `OLLAMA_BASE_URL`: Ollama service URL (default: http://localhost:11434)

### Storage Locations

- **Memory Database**: `~/Library/Application Support/Kenny/memory_db/`
- **Backups**: `~/Library/Application Support/Kenny/backups/`

## Architecture

### Components

1. **MemoryAgent**: Main agent class coordinating all operations
2. **Capability Handlers**:
   - `MemoryRetrieveHandler`: Semantic search implementation
   - `MemoryEmbedHandler`: Embedding generation 
   - `MemoryStoreHandler`: Memory storage with metadata
3. **Tools**:
   - `OllamaClientTool`: Local embedding model integration
   - `ChromaClientTool`: Vector database operations

### Data Flow

1. **Storage**: Content → Embedding → ChromaDB storage
2. **Retrieval**: Query → Embedding → Vector search → Ranked results
3. **Caching**: Embeddings cached for improved performance

## Testing

```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test categories
python3 -m pytest tests/test_memory_agent.py::TestMemoryAgent -v
```

**Test Coverage**: 24/24 tests passing (100%)

## Docker Deployment

```bash
# Build image
docker build -t memory-agent .

# Run container
docker run -p 8004:8004 memory-agent
```

## Performance

- **First embedding**: ~2s for 1KB text (model loading)
- **Cached embeddings**: ~0.1s (from cache)
- **Semantic search**: <500ms for 10K memories
- **Storage**: ~1s including embedding generation

## Health Monitoring

- **Health endpoint**: `GET /health`
- **Status endpoint**: `GET /stats`
- **Automatic health checks** every 60 seconds

## Integration

The Memory Agent integrates with:
- **Agent Registry**: Automatic capability discovery
- **Coordinator**: Orchestrated multi-agent workflows  
- **Other Agents**: Cross-agent memory enrichment
- **Kenny v2 System**: Full ecosystem integration

## Support

For issues, debugging, or feature requests, check the logs at:
- Agent logs: Service stdout/stderr
- ChromaDB logs: `~/Library/Application Support/Kenny/memory_db/`