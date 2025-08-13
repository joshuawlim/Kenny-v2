"""
Ollama client tool for the memory agent.

Provides text embedding generation using local Ollama models
with caching and batch processing capabilities.
"""

import sys
import time
import hashlib
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_tool import BaseTool

try:
    import ollama
except ImportError:
    ollama = None

import httpx


class OllamaClientTool(BaseTool):
    """Tool for interacting with local Ollama models for embedding generation."""
    
    def __init__(self):
        """Initialize the Ollama client tool."""
        super().__init__(
            name="ollama_client",
            description="Generate text embeddings using local Ollama models",
            version="1.0.0"
        )
        
        self.client = None
        self.current_model = "nomic-embed-text"
        self.embedding_cache = {}  # Simple in-memory cache
        self.base_url = "http://localhost:11434"
        self.logger = logging.getLogger(__name__)
        
        # Model configurations
        self.models_config = {
            "nomic-embed-text": {
                "dimensions": 768,
                "max_tokens": 8192,
                "description": "High-quality embedding model for general text"
            },
            "all-minilm": {
                "dimensions": 384,
                "max_tokens": 512,
                "description": "Lightweight embedding model for fast processing"
            },
            "mxbai-embed-large": {
                "dimensions": 1024,
                "max_tokens": 512,
                "description": "Large embedding model for high accuracy"
            }
        }
    
    async def initialize(self):
        """Initialize the Ollama client connection."""
        try:
            if ollama is None:
                self.logger.error("Ollama library not available")
                return False
            
            # Test connection to Ollama
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code != 200:
                    self.logger.error(f"Ollama not available at {self.base_url}")
                    return False
            
            self.client = ollama.AsyncClient(host=self.base_url)
            
            # Check if default model is available
            await self._ensure_model_available(self.current_model)
            
            self.logger.info(f"Ollama client initialized with model: {self.current_model}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama client: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup resources."""
        self.client = None
        self.embedding_cache.clear()
        self.logger.info("Ollama client cleaned up")
    
    async def set_model(self, model_name: str) -> bool:
        """
        Set the embedding model to use.
        
        Args:
            model_name: Name of the model to use
            
        Returns:
            True if model was set successfully, False otherwise
        """
        try:
            if model_name not in self.models_config:
                available_models = list(self.models_config.keys())
                self.logger.warning(f"Unknown model {model_name}, available: {available_models}")
                return False
            
            await self._ensure_model_available(model_name)
            self.current_model = model_name
            self.logger.info(f"Set Ollama model to: {model_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting model {model_name}: {e}")
            return False
    
    def get_current_model(self) -> str:
        """Get the currently active model name."""
        return self.current_model
    
    def get_model_info(self, model_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a model."""
        model = model_name or self.current_model
        return self.models_config.get(model, {})
    
    async def generate_embedding(self, text: str, use_cache: bool = True) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to generate embedding for
            use_cache: Whether to use cached embeddings
            
        Returns:
            List of embedding values
        """
        if not self.client:
            raise RuntimeError("Ollama client not initialized")
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(text, self.current_model)
            if cache_key in self.embedding_cache:
                return self.embedding_cache[cache_key]
        
        try:
            response = await self.client.embeddings(
                model=self.current_model,
                prompt=text
            )
            
            embedding = response.get("embedding", [])
            
            # Cache the result
            if use_cache and embedding:
                cache_key = self._get_cache_key(text, self.current_model)
                self.embedding_cache[cache_key] = embedding
            
            return embedding
            
        except Exception as e:
            self.logger.error(f"Error generating embedding: {e}")
            raise
    
    async def generate_embeddings_batch(
        self, 
        texts: List[str], 
        normalize: bool = True,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate embeddings for multiple texts with batch processing.
        
        Args:
            texts: List of texts to generate embeddings for
            normalize: Whether to normalize embeddings to unit length
            cache_key: Optional cache key for the batch
            
        Returns:
            Dict with embeddings and metadata
        """
        if not texts:
            return {"embeddings": [], "cached_count": 0, "generated_count": 0}
        
        embeddings = []
        cached_count = 0
        generated_count = 0
        
        for text in texts:
            try:
                embedding = await self.generate_embedding(text, use_cache=True)
                
                # Normalize if requested
                if normalize and embedding:
                    embedding = self._normalize_embedding(embedding)
                
                embeddings.append(embedding)
                
                # Count cache hits vs generations (simplified)
                cache_key_text = self._get_cache_key(text, self.current_model)
                if cache_key_text in self.embedding_cache:
                    cached_count += 1
                else:
                    generated_count += 1
                    
            except Exception as e:
                self.logger.error(f"Error generating embedding for text: {e}")
                embeddings.append([])  # Empty embedding on error
        
        return {
            "embeddings": embeddings,
            "cached_count": cached_count,
            "generated_count": generated_count
        }
    
    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model combination."""
        content = f"{model}:{text}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """Normalize embedding to unit length."""
        import math
        
        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            return [x / magnitude for x in embedding]
        return embedding
    
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
        
        if operation == "get_models":
            return list(self.models_config.keys())
        elif operation == "get_current_model":
            return self.current_model
        elif operation == "health_check":
            return {"status": "healthy" if self.client else "not_initialized"}
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    async def _ensure_model_available(self, model_name: str):
        """Ensure the specified model is available in Ollama."""
        try:
            # Check if model is already available
            models_response = await self.client.list()
            available_models = [model["name"] for model in models_response.get("models", [])]
            
            if model_name not in available_models:
                self.logger.info(f"Pulling model {model_name}...")
                await self.client.pull(model_name)
                self.logger.info(f"Model {model_name} pulled successfully")
            
        except Exception as e:
            self.logger.error(f"Error ensuring model {model_name} is available: {e}")
            raise