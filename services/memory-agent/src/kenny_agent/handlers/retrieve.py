"""
Memory retrieval capability handler.

Provides semantic search capabilities across stored memories using
vector similarity and metadata filtering.
"""

import sys
import time
import logging
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler
from typing import Dict, Any, List


class MemoryRetrieveHandler(BaseCapabilityHandler):
    """Handler for memory.retrieve capability - semantic search across stored data."""
    
    def __init__(self, ollama_client=None, chroma_client=None):
        """Initialize the memory retrieve handler."""
        self.ollama_client = ollama_client
        self.chroma_client = chroma_client
        self.logger = logging.getLogger(__name__)
        
        super().__init__(
            capability="memory.retrieve",
            description="Perform semantic search across stored memories using vector similarity",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query text for semantic matching",
                        "minLength": 1
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100
                    },
                    "similarity_threshold": {
                        "type": "number",
                        "description": "Minimum similarity score (0.0-1.0) for results",
                        "default": 0.7,
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "data_scopes": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Filter results to specific data scopes (e.g., 'mail', 'contacts')",
                        "default": []
                    },
                    "time_range": {
                        "type": "object",
                        "properties": {
                            "start": {"type": "string", "format": "date-time"},
                            "end": {"type": "string", "format": "date-time"}
                        },
                        "description": "Optional time range filter for memories"
                    }
                },
                "required": ["query"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "memories": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "content": {"type": "string"},
                                "similarity_score": {"type": "number"},
                                "metadata": {
                                    "type": "object",
                                    "properties": {
                                        "source": {"type": "string"},
                                        "data_scope": {"type": "string"},
                                        "created_at": {"type": "string", "format": "date-time"},
                                        "updated_at": {"type": "string", "format": "date-time"},
                                        "tags": {"type": "array", "items": {"type": "string"}},
                                        "context": {"type": "object"}
                                    }
                                }
                            }
                        }
                    },
                    "total_found": {"type": "integer"},
                    "search_metadata": {
                        "type": "object",
                        "properties": {
                            "query_embedding_time": {"type": "number"},
                            "search_time": {"type": "number"},
                            "embedding_model": {"type": "string"}
                        }
                    }
                }
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute memory retrieval with semantic search.
        
        Args:
            parameters: Contains query and search parameters
            
        Returns:
            Dict containing matching memories with similarity scores
        """
        try:
            query = parameters.get("query")
            limit = parameters.get("limit", 10)
            similarity_threshold = parameters.get("similarity_threshold", 0.7)
            data_scopes = parameters.get("data_scopes", [])
            time_range = parameters.get("time_range")
            
            # Check if tools are available
            if not self.ollama_client:
                raise ValueError("Ollama client tool not available")
            if not self.chroma_client:
                raise ValueError("ChromaDB client tool not available")
            
            # Generate embedding for the query
            embedding_start_time = time.time()
            query_embedding = await self.ollama_client.generate_embedding(query)
            embedding_time = time.time() - embedding_start_time
            
            # Perform vector search
            search_start_time = time.time()
            search_results = await self.chroma_client.similarity_search(
                query_embedding=query_embedding,
                limit=limit,
                similarity_threshold=similarity_threshold,
                data_scopes=data_scopes,
                time_range=time_range
            )
            search_time = time.time() - search_start_time
            
            # Format results
            memories = []
            for result in search_results.get("results", []):
                memories.append({
                    "id": result["id"],
                    "content": result["content"],
                    "similarity_score": result["similarity_score"],
                    "metadata": result["metadata"]
                })
            
            return {
                "memories": memories,
                "total_found": len(memories),
                "search_metadata": {
                    "query_embedding_time": embedding_time,
                    "search_time": search_time,
                    "embedding_model": self.ollama_client.get_current_model()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in memory retrieve: {e}")
            # Return empty results on error
            return {
                "memories": [],
                "total_found": 0,
                "search_metadata": {
                    "error": str(e)
                }
            }