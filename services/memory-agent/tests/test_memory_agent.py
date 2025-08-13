"""
Comprehensive tests for the Memory Agent.

Tests all components including agent initialization, capability handlers,
tools, and integration between components.
"""

import sys
import asyncio
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import shutil

# Add the source directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from kenny_agent.agent import MemoryAgent
from kenny_agent.handlers.retrieve import MemoryRetrieveHandler
from kenny_agent.handlers.embed import MemoryEmbedHandler
from kenny_agent.handlers.store import MemoryStoreHandler
from kenny_agent.tools.ollama_client import OllamaClientTool
from kenny_agent.tools.chroma_client import ChromaClientTool


class TestMemoryAgent:
    """Test suite for MemoryAgent class."""
    
    def test_agent_initialization(self):
        """Test that the memory agent initializes correctly."""
        agent = MemoryAgent()
        
        # Check basic properties
        assert agent.agent_id == "memory-agent"
        assert agent.name == "Memory Agent"
        assert "memory storage" in agent.description.lower()
        assert agent.version == "1.0.0"
        
        # Check data scopes
        expected_scopes = ["memory:all", "mail:content", "contacts:interactions", "calendar:events", "messages:content"]
        for scope in expected_scopes:
            assert scope in agent.data_scopes
        
        # Check tool access
        expected_tools = ["ollama", "chromadb", "sqlite-db"]
        for tool in expected_tools:
            assert tool in agent.tool_access
    
    def test_capability_registration(self):
        """Test that all capabilities are registered correctly."""
        agent = MemoryAgent()
        
        # Check that all three capabilities are registered
        assert "memory.retrieve" in agent.capabilities
        assert "memory.embed" in agent.capabilities
        assert "memory.store" in agent.capabilities
        
        # Check capability types
        assert isinstance(agent.capabilities["memory.retrieve"], MemoryRetrieveHandler)
        assert isinstance(agent.capabilities["memory.embed"], MemoryEmbedHandler)
        assert isinstance(agent.capabilities["memory.store"], MemoryStoreHandler)
    
    def test_tool_registration(self):
        """Test that all tools are registered correctly."""
        agent = MemoryAgent()
        
        # Check that both tools are registered
        assert "ollama_client" in agent.tools
        assert "chroma_client" in agent.tools
        
        # Check tool types
        assert isinstance(agent.tools["ollama_client"], OllamaClientTool)
        assert isinstance(agent.tools["chroma_client"], ChromaClientTool)
    
    @pytest.mark.asyncio
    @patch('kenny_agent.agent.HealthMonitor')
    @patch('kenny_agent.agent.AgentRegistryClient')
    async def test_agent_start_success(self, mock_registry_client, mock_health_monitor):
        """Test successful agent startup."""
        # Mock the registry client
        mock_registry_instance = AsyncMock()
        mock_registry_client.return_value = mock_registry_instance
        mock_registry_instance.register_agent.return_value = True
        
        # Mock the health monitor
        mock_health_instance = Mock()
        mock_health_monitor.return_value = mock_health_instance
        
        # Mock tool initialization
        agent = MemoryAgent()
        for tool in agent.tools.values():
            tool.initialize = AsyncMock(return_value=True)
        
        # Test startup
        result = await agent.start()
        assert result is True
        assert agent.is_running is True
        
        # Verify registry registration was called
        mock_registry_instance.register_agent.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('kenny_agent.agent.HealthMonitor')
    @patch('kenny_agent.agent.AgentRegistryClient')
    async def test_agent_start_failure(self, mock_registry_client, mock_health_monitor):
        """Test agent startup with tool initialization failure."""
        # Mock tool initialization failure
        agent = MemoryAgent()
        agent.tools["ollama_client"].initialize = AsyncMock(side_effect=Exception("Ollama not available"))
        
        # Test startup
        result = await agent.start()
        assert result is False
        assert agent.is_running is False
    
    @pytest.mark.asyncio
    async def test_agent_stop(self):
        """Test agent shutdown."""
        agent = MemoryAgent()
        
        # Mock tool cleanup
        for tool in agent.tools.values():
            tool.cleanup = AsyncMock(return_value=True)
        
        agent.is_running = True
        
        # Test shutdown
        result = await agent.stop()
        assert result is True
        assert agent.is_running is False
        
        # Verify tool cleanup was called
        for tool in agent.tools.values():
            tool.cleanup.assert_called_once()
    
    def test_manifest_generation(self):
        """Test agent manifest generation."""
        agent = MemoryAgent()
        manifest = agent.generate_manifest()
        
        # Check manifest structure
        assert "agent_id" in manifest
        assert "display_name" in manifest
        assert "capabilities" in manifest
        assert "data_scopes" in manifest
        assert "tool_access" in manifest
        
        # Check capabilities in manifest
        assert len(manifest["capabilities"]) == 3
        capability_verbs = [cap["verb"] for cap in manifest["capabilities"]]
        assert "memory.retrieve" in capability_verbs
        assert "memory.embed" in capability_verbs
        assert "memory.store" in capability_verbs


class TestMemoryRetrieveHandler:
    """Test suite for MemoryRetrieveHandler."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        handler = MemoryRetrieveHandler()
        
        assert handler.capability == "memory.retrieve"
        assert "semantic search" in handler.description.lower()
        assert handler.input_schema is not None
        assert handler.output_schema is not None
    
    @pytest.mark.asyncio
    async def test_execute_with_query(self):
        """Test successful memory retrieval."""
        # Mock tools
        mock_ollama = AsyncMock()
        mock_chroma = AsyncMock()
        
        # Mock embedding generation
        mock_ollama.generate_embedding.return_value = [0.1, 0.2, 0.3]
        mock_ollama.get_current_model.return_value = "nomic-embed-text"
        
        # Mock search results
        mock_chroma.similarity_search.return_value = {
            "results": [
                {
                    "id": "mem1",
                    "content": "Test memory content",
                    "similarity_score": 0.85,
                    "metadata": {"source": "test", "created_at": "2025-08-13T10:00:00Z"}
                }
            ]
        }
        
        # Initialize handler with mock tools
        handler = MemoryRetrieveHandler(mock_ollama, mock_chroma)
        
        parameters = {
            "query": "test query",
            "limit": 10,
            "similarity_threshold": 0.7
        }
        
        # Execute
        result = await handler.execute(parameters)
        
        # Verify results
        assert "memories" in result
        assert "total_found" in result
        assert "search_metadata" in result
        assert len(result["memories"]) == 1
        assert result["memories"][0]["id"] == "mem1"
        assert result["total_found"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_missing_tools(self):
        """Test execution with missing tools."""
        # Initialize handler without tools
        handler = MemoryRetrieveHandler()
        
        parameters = {"query": "test query"}
        
        # Execute - should handle gracefully
        result = await handler.execute(parameters)
        
        # Should return empty results with error
        assert result["memories"] == []
        assert result["total_found"] == 0
        assert "error" in result["search_metadata"]


class TestMemoryEmbedHandler:
    """Test suite for MemoryEmbedHandler."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        handler = MemoryEmbedHandler()
        
        assert handler.capability == "memory.embed"
        assert "embedding" in handler.description.lower()
        assert handler.input_schema is not None
        assert handler.output_schema is not None
    
    @pytest.mark.asyncio
    async def test_execute_single_text(self):
        """Test embedding generation for single text."""
        # Mock Ollama client
        mock_ollama = AsyncMock()
        mock_ollama.set_model.return_value = True
        mock_ollama.generate_embeddings_batch.return_value = {
            "embeddings": [[0.1, 0.2, 0.3]],
            "cached_count": 0,
            "generated_count": 1
        }
        
        # Initialize handler with mock tool
        handler = MemoryEmbedHandler(mock_ollama)
        
        parameters = {
            "texts": ["Hello world"],
            "model": "nomic-embed-text"
        }
        
        # Execute
        result = await handler.execute(parameters)
        
        # Verify results
        assert "embeddings" in result
        assert "metadata" in result
        assert len(result["embeddings"]) == 1
        assert len(result["embeddings"][0]) == 3
        assert result["metadata"]["generated_results"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_batch_texts(self):
        """Test embedding generation for multiple texts."""
        # Mock Ollama client
        mock_ollama = AsyncMock()
        mock_ollama.set_model.return_value = True
        mock_ollama.generate_embeddings_batch.return_value = {
            "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            "cached_count": 1,
            "generated_count": 1
        }
        
        # Initialize handler with mock tool
        handler = MemoryEmbedHandler(mock_ollama)
        
        parameters = {
            "texts": ["Hello world", "Machine learning"],
            "normalize": True
        }
        
        # Execute
        result = await handler.execute(parameters)
        
        # Verify results
        assert len(result["embeddings"]) == 2
        assert result["metadata"]["cached_results"] == 1
        assert result["metadata"]["generated_results"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_no_texts(self):
        """Test execution with no texts provided."""
        # Initialize handler with mock tool
        handler = MemoryEmbedHandler(AsyncMock())
        
        parameters = {"texts": []}
        
        # Execute - should handle gracefully
        result = await handler.execute(parameters)
        
        # Should return empty results with error
        assert result["embeddings"] == []
        assert "error" in result["metadata"]


class TestMemoryStoreHandler:
    """Test suite for MemoryStoreHandler."""
    
    def test_handler_initialization(self):
        """Test handler initialization."""
        handler = MemoryStoreHandler()
        
        assert handler.capability == "memory.store"
        assert "store" in handler.description.lower()
        assert handler.input_schema is not None
        assert handler.output_schema is not None
    
    @pytest.mark.asyncio
    async def test_execute_store_with_embedding(self):
        """Test memory storage with automatic embedding generation."""
        # Mock tools
        mock_ollama = AsyncMock()
        mock_chroma = AsyncMock()
        
        # Mock embedding generation
        mock_ollama.set_model.return_value = True
        mock_ollama.generate_embedding.return_value = [0.1, 0.2, 0.3]
        
        # Mock storage
        mock_chroma.store_memory.return_value = {"success": True}
        
        # Initialize handler with mock tools
        handler = MemoryStoreHandler(mock_ollama, mock_chroma)
        
        parameters = {
            "content": "Test memory content",
            "metadata": {
                "source": "test",
                "data_scope": "test:data"
            },
            "auto_embed": True
        }
        
        # Execute
        result = await handler.execute(parameters)
        
        # Verify results
        assert result["memory_id"] is not None
        assert result["stored_at"] is not None
        assert result["embedding_generated"] is True
        assert result["metadata"]["content_length"] > 0
        assert result["metadata"]["embedding_dimensions"] == 3
    
    @pytest.mark.asyncio
    async def test_execute_store_without_embedding(self):
        """Test memory storage without embedding generation."""
        # Mock tools
        mock_chroma = AsyncMock()
        mock_chroma.store_memory.return_value = {"success": True}
        
        # Initialize handler with mock tools (no ollama for this test)
        handler = MemoryStoreHandler(None, mock_chroma)
        
        parameters = {
            "content": "Test memory content",
            "metadata": {
                "source": "test",
                "data_scope": "test:data"
            },
            "auto_embed": False
        }
        
        # Execute
        result = await handler.execute(parameters)
        
        # Verify results
        assert result["memory_id"] is not None
        assert result["embedding_generated"] is False
        assert result["metadata"]["embedding_dimensions"] == 0
    
    @pytest.mark.asyncio
    async def test_execute_missing_metadata(self):
        """Test execution with missing required metadata."""
        # Initialize handler with mock tools
        handler = MemoryStoreHandler(None, AsyncMock())
        
        parameters = {
            "content": "Test content",
            "metadata": {
                "source": "test"
                # Missing data_scope
            }
        }
        
        # Execute - should handle gracefully
        result = await handler.execute(parameters)
        
        # Should return error
        assert result["memory_id"] is None
        assert "error" in result["metadata"]


class TestOllamaClientTool:
    """Test suite for OllamaClientTool."""
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        tool = OllamaClientTool()
        
        assert tool.name == "ollama_client"
        assert "ollama" in tool.description.lower()
        assert tool.current_model == "nomic-embed-text"
    
    def test_model_configuration(self):
        """Test model configuration data."""
        tool = OllamaClientTool()
        
        # Check that model configs exist
        assert "nomic-embed-text" in tool.models_config
        assert "all-minilm" in tool.models_config
        assert "mxbai-embed-large" in tool.models_config
        
        # Check config structure
        for model_config in tool.models_config.values():
            assert "dimensions" in model_config
            assert "max_tokens" in model_config
            assert "description" in model_config
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        tool = OllamaClientTool()
        
        key1 = tool._get_cache_key("test text", "model1")
        key2 = tool._get_cache_key("test text", "model2")
        key3 = tool._get_cache_key("different text", "model1")
        
        # Different models should give different keys
        assert key1 != key2
        # Different texts should give different keys
        assert key1 != key3
        # Same text and model should give same key
        assert key1 == tool._get_cache_key("test text", "model1")
    
    def test_embedding_normalization(self):
        """Test embedding normalization."""
        tool = OllamaClientTool()
        
        # Test normalization
        embedding = [3.0, 4.0]  # Magnitude = 5
        normalized = tool._normalize_embedding(embedding)
        
        # Should be normalized to unit length
        assert abs(normalized[0] - 0.6) < 1e-6
        assert abs(normalized[1] - 0.8) < 1e-6
        
        # Test zero vector
        zero_embedding = [0.0, 0.0]
        normalized_zero = tool._normalize_embedding(zero_embedding)
        assert normalized_zero == [0.0, 0.0]


class TestChromaClientTool:
    """Test suite for ChromaClientTool."""
    
    def test_tool_initialization(self):
        """Test tool initialization."""
        tool = ChromaClientTool()
        
        assert tool.name == "chroma_client"
        assert "chromadb" in tool.description.lower()
        assert tool.collection_name == "kenny_memories"
        assert "Kenny" in str(tool.data_dir)
    
    def test_get_collection_stats_no_collection(self):
        """Test getting stats when collection is not initialized."""
        tool = ChromaClientTool()
        
        stats = tool.get_collection_stats()
        assert "error" in stats
        assert "not initialized" in stats["error"].lower()


# Integration tests would go here, but they require actual Ollama and ChromaDB instances
# For now, we test the interfaces and error handling with mocks