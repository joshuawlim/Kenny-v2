"""
ChromaDB client tool for the memory agent.

Provides vector storage and similarity search capabilities using ChromaDB
for semantic memory retrieval and storage.
"""

import sys
import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_tool import BaseTool

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None


class ChromaClientTool(BaseTool):
    """Tool for interacting with ChromaDB for vector storage and similarity search."""
    
    def __init__(self):
        """Initialize the ChromaDB client tool."""
        super().__init__(
            name="chroma_client",
            description="Store and retrieve vectors using ChromaDB for semantic search",
            version="1.0.0"
        )
        
        self.client = None
        self.collection = None
        self.collection_name = "kenny_memories"
        self.logger = logging.getLogger(__name__)
        
        # Configure ChromaDB data directory
        self.data_dir = Path.home() / "Library" / "Application Support" / "Kenny" / "memory_db"
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Initialize the ChromaDB client and collection."""
        try:
            if chromadb is None:
                self.logger.error("ChromaDB library not available")
                return False
            
            # Initialize persistent client
            self.client = chromadb.PersistentClient(
                path=str(self.data_dir),
                settings=Settings(
                    anonymized_telemetry=False,
                    is_persistent=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Kenny v2 Memory Storage"}
            )
            
            self.logger.info(f"ChromaDB initialized with collection: {self.collection_name}")
            self.logger.info(f"Data directory: {self.data_dir}")
            
            # Log collection stats
            count = self.collection.count()
            self.logger.info(f"Collection contains {count} memories")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize ChromaDB client: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        self.client = None
        self.collection = None
        self.logger.info("ChromaDB client cleaned up")
    
    async def store_memory(
        self, 
        memory_id: str,
        content: str,
        embedding: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a memory in ChromaDB.
        
        Args:
            memory_id: Unique identifier for the memory
            content: Text content of the memory
            embedding: Vector embedding for the content
            metadata: Additional metadata for the memory
            
        Returns:
            Dict with storage result and metadata
        """
        try:
            if not self.collection:
                raise RuntimeError("ChromaDB collection not initialized")
            
            # Prepare metadata
            storage_metadata = metadata or {}
            storage_metadata.update({
                "stored_at": datetime.now(timezone.utc).isoformat(),
                "content_length": len(content)
            })
            
            # Store in collection
            if embedding:
                self.collection.add(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[storage_metadata]
                )
            else:
                # Store without embedding (ChromaDB can generate embeddings, but we prefer Ollama)
                self.collection.add(
                    ids=[memory_id],
                    documents=[content],
                    metadatas=[storage_metadata]
                )
            
            return {
                "success": True,
                "memory_id": memory_id,
                "stored_at": storage_metadata["stored_at"]
            }
            
        except Exception as e:
            self.logger.error(f"Error storing memory {memory_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        data_scopes: Optional[List[str]] = None,
        time_range: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Perform similarity search using vector embeddings.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum number of results to return
            similarity_threshold: Minimum similarity score
            data_scopes: Filter by data scopes
            time_range: Optional time range filter
            
        Returns:
            Dict with search results and metadata
        """
        try:
            if not self.collection:
                raise RuntimeError("ChromaDB collection not initialized")
            
            # Build where clause for filtering
            where_clause = {}
            
            if data_scopes:
                where_clause["data_scope"] = {"$in": data_scopes}
            
            if time_range:
                if time_range.get("start"):
                    where_clause["created_at"] = {"$gte": time_range["start"]}
                if time_range.get("end"):
                    if "created_at" not in where_clause:
                        where_clause["created_at"] = {}
                    where_clause["created_at"]["$lte"] = time_range["end"]
            
            # Perform similarity search
            search_results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where_clause if where_clause else None
            )
            
            # Process results
            results = []
            if search_results["ids"] and search_results["ids"][0]:
                ids = search_results["ids"][0]
                documents = search_results["documents"][0]
                metadatas = search_results["metadatas"][0]
                distances = search_results["distances"][0]
                
                for i in range(len(ids)):
                    # Convert distance to similarity score (1 - normalized_distance)
                    # ChromaDB returns squared Euclidean distance for normalized vectors
                    similarity_score = max(0, 1 - (distances[i] / 2))
                    
                    # Filter by similarity threshold
                    if similarity_score >= similarity_threshold:
                        results.append({
                            "id": ids[i],
                            "content": documents[i],
                            "similarity_score": similarity_score,
                            "metadata": metadatas[i] or {}
                        })
            
            return {
                "results": results,
                "total_found": len(results),
                "search_metadata": {
                    "similarity_threshold": similarity_threshold,
                    "data_scopes_filter": data_scopes,
                    "time_range_filter": time_range
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in similarity search: {e}")
            return {
                "results": [],
                "total_found": 0,
                "search_metadata": {
                    "error": str(e)
                }
            }
    
    async def get_memory(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific memory by ID.
        
        Args:
            memory_id: Unique identifier for the memory
            
        Returns:
            Memory data or None if not found
        """
        try:
            if not self.collection:
                raise RuntimeError("ChromaDB collection not initialized")
            
            results = self.collection.get(
                ids=[memory_id],
                include=["documents", "metadatas"]
            )
            
            if results["ids"] and results["ids"][0]:
                return {
                    "id": results["ids"][0],
                    "content": results["documents"][0],
                    "metadata": results["metadatas"][0] or {}
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error retrieving memory {memory_id}: {e}")
            return None
    
    async def delete_memory(self, memory_id: str) -> bool:
        """
        Delete a memory from storage.
        
        Args:
            memory_id: Unique identifier for the memory
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            if not self.collection:
                raise RuntimeError("ChromaDB collection not initialized")
            
            self.collection.delete(ids=[memory_id])
            self.logger.info(f"Deleted memory {memory_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting memory {memory_id}: {e}")
            return False
    
    async def cleanup_old_memories(self, retention_days: int = 365) -> Dict[str, Any]:
        """
        Clean up old memories based on retention policy.
        
        Args:
            retention_days: Number of days to retain memories
            
        Returns:
            Dict with cleanup results
        """
        try:
            if not self.collection:
                raise RuntimeError("ChromaDB collection not initialized")
            
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
            cutoff_iso = cutoff_date.isoformat()
            
            # Find old memories
            old_memories = self.collection.get(
                where={"created_at": {"$lt": cutoff_iso}},
                include=["metadatas"]
            )
            
            deleted_count = 0
            if old_memories["ids"]:
                # Delete old memories
                self.collection.delete(ids=old_memories["ids"])
                deleted_count = len(old_memories["ids"])
                
            self.logger.info(f"Cleaned up {deleted_count} old memories (older than {retention_days} days)")
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "cutoff_date": cutoff_iso
            }
            
        except Exception as e:
            self.logger.error(f"Error in cleanup: {e}")
            return {
                "success": False,
                "error": str(e),
                "deleted_count": 0
            }
    
    def execute(self, parameters: Dict[str, Any]) -> Any:
        """
        Execute tool operations (placeholder implementation).
        
        This method is required by BaseTool but most operations are 
        called directly by the capability handlers.
        
        Args:
            parameters: Tool execution parameters
            
        Returns:
            Tool execution results
        """
        operation = parameters.get("operation")
        
        if operation == "get_stats":
            return self.get_collection_stats()
        elif operation == "health_check":
            return {"status": "healthy" if self.collection else "not_initialized"}
        elif operation == "get_collection_name":
            return self.collection_name
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the memory collection."""
        try:
            if not self.collection:
                return {"error": "Collection not initialized"}
            
            count = self.collection.count()
            
            return {
                "total_memories": count,
                "collection_name": self.collection_name,
                "data_directory": str(self.data_dir)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}