"""
Memory embedding capability handler.

Provides text embedding generation capabilities using local Ollama models
with caching and batch processing support.
"""

import sys
import time
import logging
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler
from typing import Dict, Any, List


class MemoryEmbedHandler(BaseCapabilityHandler):
    """Handler for memory.embed capability - generate embeddings for text."""
    
    def __init__(self, ollama_client=None):
        """Initialize the memory embed handler."""
        self.ollama_client = ollama_client
        self.logger = logging.getLogger(__name__)
        
        super().__init__(
            capability="memory.embed",
            description="Generate text embeddings using local Ollama models with caching support",
            input_schema={
                "type": "object",
                "properties": {
                    "texts": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Text(s) to generate embeddings for",
                        "minItems": 1,
                        "maxItems": 100
                    },
                    "model": {
                        "type": "string",
                        "description": "Embedding model to use",
                        "default": "nomic-embed-text",
                        "enum": ["nomic-embed-text", "all-minilm", "mxbai-embed-large"]
                    },
                    "normalize": {
                        "type": "boolean",
                        "description": "Whether to normalize embeddings to unit length",
                        "default": True
                    },
                    "cache_key": {
                        "type": "string",
                        "description": "Optional cache key for storing/retrieving embeddings"
                    }
                },
                "required": ["texts"]
            },
            output_schema={
                "type": "object",
                "properties": {
                    "embeddings": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "number"}
                        },
                        "description": "Generated embeddings (one per input text)"
                    },
                    "metadata": {
                        "type": "object",
                        "properties": {
                            "model": {"type": "string"},
                            "embedding_dimensions": {"type": "integer"},
                            "processing_time": {"type": "number"},
                            "cached_results": {"type": "integer"},
                            "generated_results": {"type": "integer"}
                        }
                    }
                }
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute embedding generation for texts.
        
        Args:
            parameters: Contains texts and embedding parameters
            
        Returns:
            Dict containing embeddings and processing metadata
        """
        try:
            texts = parameters.get("texts", [])
            model = parameters.get("model", "nomic-embed-text")
            normalize = parameters.get("normalize", True)
            cache_key = parameters.get("cache_key")
            
            if not texts:
                raise ValueError("No texts provided for embedding")
            
            # Check if tool is available
            if not self.ollama_client:
                raise ValueError("Ollama client tool not available")
            
            # Set model if different from current
            await self.ollama_client.set_model(model)
            
            # Process embeddings
            start_time = time.time()
            embeddings_result = await self.ollama_client.generate_embeddings_batch(
                texts=texts,
                normalize=normalize,
                cache_key=cache_key
            )
            processing_time = time.time() - start_time
            
            # Get embedding dimensions (from first embedding)
            embedding_dimensions = len(embeddings_result["embeddings"][0]) if embeddings_result["embeddings"] else 0
            
            return {
                "embeddings": embeddings_result["embeddings"],
                "metadata": {
                    "model": model,
                    "embedding_dimensions": embedding_dimensions,
                    "processing_time": processing_time,
                    "cached_results": embeddings_result.get("cached_count", 0),
                    "generated_results": embeddings_result.get("generated_count", 0)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error in memory embed: {e}")
            return {
                "embeddings": [],
                "metadata": {
                    "error": str(e),
                    "processing_time": 0,
                    "cached_results": 0,
                    "generated_results": 0
                }
            }