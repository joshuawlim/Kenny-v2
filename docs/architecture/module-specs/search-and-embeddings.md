# Search and Embeddings Module Specification

## Overview
Search and embeddings module provides local semantic search capabilities across all Kenny data using local LLM embeddings and hybrid search techniques.

## Design Decisions
- **Local embeddings**: Per ADR-0003, use Ollama for local embedding generation
- **Hybrid search**: Combine semantic (embeddings) and keyword search
- **No cloud egress**: All processing done locally for privacy
- **Real-time indexing**: Embeddings generated as data is ingested

## Interface
```python
class SearchAndEmbeddings:
    def generate_embedding(self, text: str) -> List[float]
    def search(self, query: str, filters: Dict = None) -> List[SearchResult]
    def index_content(self, content_id: str, text: str) -> None
    def get_similar(self, content_id: str, limit: int = 10) -> List[SearchResult]
```

## Search Types
- **Semantic search**: Find content with similar meaning using embeddings
- **Keyword search**: Traditional text-based search with relevance scoring
- **Hybrid search**: Combine both approaches for optimal results
- **Faceted search**: Filter by platform, date, sender, etc.

## Data Model
- `Embedding`: id, content_id, embedding_vector, model_version, created_at
- `SearchIndex`: content_id, text_content, metadata, last_indexed
- `SearchResult`: content_id, relevance_score, snippet, metadata

## Embedding Generation
- **Model**: Ollama with local embedding models
- **Batch processing**: Generate embeddings for new content asynchronously
- **Model management**: Support multiple embedding models and versions
- **Quality metrics**: Track embedding quality and consistency

## Search Performance
- **Vector indexing**: Efficient similarity search using HNSW or similar
- **Caching**: Cache frequently accessed embeddings and search results
- **Async processing**: Non-blocking search operations
- **Result ranking**: Intelligent ranking based on multiple factors

## Integration Points
- **Message ingestion**: Generate embeddings for new messages
- **Contact enrichment**: Semantic search across contact information
- **Memory retrieval**: Find relevant conversation history
- **Knowledge base**: Search across all stored information

## Configuration
- **Embedding model**: Configurable Ollama model for embeddings
- **Search parameters**: Adjustable relevance thresholds and result limits
- **Indexing strategy**: Configurable batch sizes and processing intervals
- **Cache settings**: Memory and disk cache configuration


