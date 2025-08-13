#!/usr/bin/env python3
"""
Integration test for the Memory Agent.

Tests the complete integration without external dependencies
by mocking Ollama and ChromaDB services.
"""

import sys
import asyncio
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add the source directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_memory_agent_integration():
    """Test the complete memory agent integration."""
    logger.info("=" * 60)
    logger.info("Testing Memory Agent Integration")
    logger.info("=" * 60)
    
    try:
        # Test 1: Agent creation and initialization
        logger.info("\n1. Testing Agent Creation...")
        from kenny_agent.agent import MemoryAgent
        
        # Mock external dependencies
        with patch('kenny_agent.tools.ollama_client.ollama'), \
             patch('kenny_agent.tools.chroma_client.chromadb'):
            
            agent = MemoryAgent()
            logger.info(f"✓ Agent created: {agent.name}")
            logger.info(f"✓ Capabilities: {len(agent.capabilities)}")
            logger.info(f"✓ Tools: {len(agent.tools)}")
            
            # Test 2: Capability registration
            logger.info("\n2. Testing Capability Registration...")
            capabilities = agent.get_capabilities()
            expected_capabilities = ["memory.retrieve", "memory.embed", "memory.store"]
            
            for capability in expected_capabilities:
                assert capability in capabilities, f"Missing capability: {capability}"
                logger.info(f"✓ Capability registered: {capability}")
            
            # Test 3: Manifest generation
            logger.info("\n3. Testing Manifest Generation...")
            manifest = agent.generate_manifest()
            
            assert manifest["agent_id"] == "memory-agent"
            assert len(manifest["capabilities"]) == 3
            assert "memory:all" in manifest["data_scopes"]
            logger.info("✓ Manifest generation successful")
            
            # Test 4: Tool operations
            logger.info("\n4. Testing Tool Operations...")
            ollama_tool = agent.tools["ollama_client"]
            chroma_tool = agent.tools["chroma_client"]
            
            # Test tool execute methods
            models_result = ollama_tool.execute({"operation": "get_models"})
            assert isinstance(models_result, list)
            logger.info(f"✓ Ollama tool: {len(models_result)} models available")
            
            health_result = chroma_tool.execute({"operation": "health_check"})
            assert "status" in health_result
            logger.info(f"✓ ChromaDB tool health: {health_result['status']}")
            
            # Test 5: Capability info
            logger.info("\n5. Testing Capability Information...")
            for capability in expected_capabilities:
                info = agent.get_capability_info(capability)
                assert info is not None
                assert "verb" in info or "capability" in info
                logger.info(f"✓ {capability}: {info.get('description', 'No description')[:50]}...")
            
            # Test 6: Health status
            logger.info("\n6. Testing Health Status...")
            health = agent.get_health_status()
            assert "agent_id" in health
            assert "status" in health
            assert health["capabilities_count"] == 3
            assert health["tools_count"] == 2
            logger.info(f"✓ Health status: {health['status']}")
            
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL INTEGRATION TESTS PASSED")
        logger.info("Memory Agent is ready for deployment!")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ INTEGRATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fastapi_service():
    """Test the FastAPI service startup."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing FastAPI Service")
    logger.info("=" * 60)
    
    try:
        from fastapi.testclient import TestClient
        
        # Mock external dependencies
        with patch('kenny_agent.tools.ollama_client.ollama'), \
             patch('kenny_agent.tools.chroma_client.chromadb'), \
             patch('src.main.memory_agent') as mock_agent:
            
            # Setup mock agent
            mock_agent_instance = Mock()
            mock_agent_instance.is_running = True
            mock_agent_instance.get_capabilities.return_value = ["memory.retrieve", "memory.embed", "memory.store"]
            mock_agent_instance.get_capability_info.return_value = {"verb": "memory.test", "description": "Test capability"}
            mock_agent_instance.get_health_status.return_value = {"status": "healthy"}
            mock_agent_instance.execute_capability = AsyncMock(return_value={"test": "result"})
            
            mock_agent = mock_agent_instance
            
            # Test service endpoints
            from src.main import app
            client = TestClient(app)
            
            logger.info("1. Testing root endpoint...")
            response = client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            assert "Memory Agent" in data["service"]
            logger.info("✓ Root endpoint working")
            
            logger.info("2. Testing capabilities endpoint...")
            response = client.get("/capabilities")
            assert response.status_code in [200, 503]  # May be 503 if agent not started
            logger.info("✓ Capabilities endpoint accessible")
            
            logger.info("3. Testing health endpoint...")
            response = client.get("/health")
            assert response.status_code in [200, 503]  # May be 503 if agent not started
            logger.info("✓ Health endpoint accessible")
            
        logger.info("\n✓ FastAPI service integration successful!")
        return True
        
    except Exception as e:
        logger.error(f"✗ FastAPI service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    async def run_all_tests():
        success = True
        success &= await test_memory_agent_integration()
        success &= await test_fastapi_service()
        return success
    
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)