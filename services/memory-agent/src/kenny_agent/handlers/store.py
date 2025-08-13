"""
Memory storage capability handler.

Provides memory storage capabilities with metadata, tagging, and
automatic embedding generation for new memories.
"""

import sys
import time
import uuid
import logging
from datetime import datetime
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler
from typing import Dict, Any, List, Optional


class MemoryStoreHandler(BaseCapabilityHandler):
    """Handler for memory.store capability - store new memories with metadata."""
    
    def __init__(self, ollama_client=None, chroma_client=None):
        """Initialize the memory store handler."""
        self.ollama_client = ollama_client
        self.chroma_client = chroma_client
        self.logger = logging.getLogger(__name__)
        
        super().__init__(
            capability="memory.store",
            description="Store new memories with automatic embedding generation and metadata",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "Memory content to store",
                        "minLength": 1,
                        "maxLength": 10000
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string", "description": "Source of the memory (e.g., 'mail', 'contacts')"},
                            "data_scope": {"type": "string", "description": "Data scope classification"},
                            "context": {"type": "object", "description": "Additional context data"},
                            "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                            "importance": {"type": "number", "minimum": 0.0, "maximum": 1.0, "description": "Importance score (0.0-1.0)"},
                            "retention_policy": {"type": "string", "description": "Retention policy for this memory"}
                        },
                        "required": ["source", "data_scope"]
                    },
                    "embedding_model": {
                        "type": "string",
                        "description": "Embedding model to use for this memory",
                        "default": "nomic-embed-text"
                    },
                    "auto_embed": {
                        "type": "boolean",
                        "description": "Whether to automatically generate embeddings",
                        "default": True
                    }
                },
                "required": ["content", "metadata"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Unique identifier for the stored memory"},
                    "stored_at": {"type": "string", "format": "date-time"},
                    "embedding_generated": {"type": "boolean"},
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "content_length": {"type": "integer"},
                            "embedding_dimensions": {"type": "integer"},
                            "storage_time": {"type": "number"},
                            "embedding_time": {"type": "number"}
                        }
                    }
                }
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute memory storage with optional embedding generation.
        
        Args:
            parameters: Contains content and metadata to store
            
        Returns:
            Dict containing memory ID and storage metadata
        """
        try:
            content = parameters.get("content")
            metadata = parameters.get("metadata", {})
            embedding_model = parameters.get("embedding_model", "nomic-embed-text")
            auto_embed = parameters.get("auto_embed", True)
            
            if not content:
                raise ValueError("No content provided for storage")
            if not metadata.get("source"):
                raise ValueError("Source metadata is required")
            if not metadata.get("data_scope"):
                raise ValueError("Data scope metadata is required")
            
            # Check if tools are available
            if auto_embed and not self.ollama_client:
                raise ValueError("Ollama client tool not available for embedding generation")
            if not self.chroma_client:
                raise ValueError("ChromaDB client tool not available for storage")
            
            # Generate unique memory ID
            memory_id = str(uuid.uuid4())
            stored_at = datetime.utcnow()
            
            # Prepare memory metadata
            memory_metadata = {
                **metadata,
                "created_at": stored_at.isoformat(),
                "updated_at": stored_at.isoformat(),
                "content_length": len(content),
                "importance": metadata.get("importance", 0.5),
                "tags": metadata.get("tags", [])
            }
            
            start_time = time.time()
            
            # Generate embedding if requested
            embedding = None
            embedding_time = 0
            embedding_dimensions = 0
            
            if auto_embed:
                embedding_start = time.time()
                await self.ollama_client.set_model(embedding_model)
                embedding_result = await self.ollama_client.generate_embedding(content)
                embedding = embedding_result if isinstance(embedding_result, list) else embedding_result.get("embedding", [])
                embedding_time = time.time() - embedding_start
                embedding_dimensions = len(embedding) if embedding else 0
            
            # Store in ChromaDB
            storage_result = await self.chroma_client.store_memory(
                memory_id=memory_id,
                content=content,
                embedding=embedding,
                metadata=memory_metadata
            )
            
            storage_time = time.time() - start_time
            
            if not storage_result.get("success"):
                raise Exception(f"Failed to store memory: {storage_result.get('error')}")
            
            return {
                "memory_id": memory_id,
                "stored_at": stored_at.isoformat(),
                "embedding_generated": auto_embed and embedding is not None,
                "metadata": {
                    "content_length": len(content),
                    "embedding_dimensions": embedding_dimensions,
                    "storage_time": storage_time,
                    "embedding_time": embedding_time
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in memory store: {e}")
            return {
                "memory_id": None,
                "stored_at": None,
                "embedding_generated": False,
                "metadata": {
                    "error": str(e),
                    "content_length": 0,
                    "embedding_dimensions": 0,
                    "storage_time": 0,
                    "embedding_time": 0
                }
            }