# Memory and Learning Module Specification

## Overview
Memory and learning module provides persistent storage and retrieval of conversation history, user preferences, and learned patterns for the Kenny persona.

## Design Decisions
- **Local storage**: Per ADR-0014, all memory data stored locally
- **SQLite primary**: Main storage in SQLite for performance
- **PostgreSQL media**: Large content (images, attachments) in PostgreSQL
- **Searchable**: Full-text search across conversation history

## Interface
```python
class MemoryLearning:
    def store_conversation(self, conversation: Conversation) -> str
    def retrieve_context(self, query: str, limit: int = 10) -> List[Memory]
    def learn_preference(self, user_id: str, preference: Preference) -> None
    def get_user_profile(self, user_id: str) -> UserProfile
```

## Data Model
- `Conversation`: id, platform, participants, messages, timestamp, metadata
- `Memory`: id, conversation_id, content, embedding, tags, importance_score
- `UserProfile`: id, preferences, interaction_patterns, trust_level
- `Preference`: category, value, confidence, last_updated

## Learning Loop
1. **Capture**: Store all conversations with metadata
2. **Process**: Extract key information and generate embeddings
3. **Learn**: Identify patterns in user preferences and behavior
4. **Apply**: Use learned patterns to improve future interactions

## Search & Retrieval
- **Hybrid search**: Combine semantic (embeddings) and keyword search
- **Context window**: Retrieve relevant conversation history for context
- **Relevance scoring**: Rank memories by recency and importance

## Security & Privacy
- **Local processing**: All embeddings generated locally
- **No cloud egress**: Per security posture requirements
- **User control**: Users can delete specific memories or entire history

## Performance
- **Indexing**: Full-text search indices on conversation content
- **Embeddings**: Vector similarity search for semantic retrieval
- **Caching**: Frequently accessed user profiles and preferences


