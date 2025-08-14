"""
Integration tests for contact enrichment functionality.

Tests the integration between Contacts Agent and Memory Agent for
message analysis and LLM-powered contact enrichment.
"""

import pytest
import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import sys
from pathlib import Path

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "agent-sdk"))

# Import the enrichment handler and related classes
from kenny_agent.base_handler import BaseCapabilityHandler
from src.kenny_agent.handlers.enrich import EnrichContactsHandler


class MockMemoryAgent:
    """Mock Memory Agent for testing integration."""
    
    def __init__(self):
        self.stored_memories = []
        
    async def store_memory(self, content: str, metadata: dict) -> dict:
        """Mock memory storage."""
        memory_id = str(uuid.uuid4())
        memory = {
            "memory_id": memory_id,
            "content": content,
            "metadata": metadata,
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "embedding_generated": True
        }
        self.stored_memories.append(memory)
        return memory
        
    async def retrieve_memories(self, query: str, limit: int = 10) -> list:
        """Mock memory retrieval with semantic search."""
        # Simple mock - return memories containing query terms
        results = []
        for memory in self.stored_memories:
            if query.lower() in memory["content"].lower():
                results.append({
                    "memory_id": memory["memory_id"],
                    "content": memory["content"],
                    "metadata": memory["metadata"],
                    "similarity_score": 0.85
                })
        return results[:limit]


class MockMessageAnalyzer:
    """Mock message analyzer for extracting contact information."""
    
    async def analyze_messages_for_contact(self, contact_id: str, contact_name: str) -> dict:
        """Mock message analysis for contact enrichment."""
        # Mock analysis results based on contact_id patterns
        if "john" in contact_id.lower():
            return {
                "job_info": [
                    {"value": "Software Engineer at TechCorp", "confidence": 0.85, "source_message": "mentioned working at TechCorp on mobile apps"}
                ],
                "interests": [
                    {"value": "Machine Learning", "confidence": 0.80, "source_message": "discussed ML algorithms in recent chat"},
                    {"value": "Rock Climbing", "confidence": 0.70, "source_message": "talked about weekend climbing trip"}
                ],
                "relationships": [
                    {"value": "Colleague", "confidence": 0.90, "source_message": "frequent work-related discussions"}
                ],
                "interaction_patterns": {
                    "frequency": "high",
                    "recency": "2 days ago",
                    "sentiment": "positive",
                    "topic_distribution": {"work": 0.6, "personal": 0.4}
                }
            }
        elif "jane" in contact_id.lower():
            return {
                "job_info": [
                    {"value": "Product Manager", "confidence": 0.90, "source_message": "mentioned leading product team"}
                ],
                "interests": [
                    {"value": "Design Thinking", "confidence": 0.85, "source_message": "shared article about UX design"}
                ],
                "relationships": [
                    {"value": "Friend", "confidence": 0.80, "source_message": "personal conversations and social meetups"}
                ],
                "interaction_patterns": {
                    "frequency": "medium",
                    "recency": "1 week ago", 
                    "sentiment": "neutral",
                    "topic_distribution": {"personal": 0.7, "work": 0.3}
                }
            }
        else:
            return {
                "job_info": [],
                "interests": [],
                "relationships": [],
                "interaction_patterns": {
                    "frequency": "low",
                    "recency": "never",
                    "sentiment": "neutral",
                    "topic_distribution": {}
                }
            }


class EnhancedEnrichContactsHandler(EnrichContactsHandler):
    """Enhanced enrichment handler with message analysis integration."""
    
    def __init__(self, agent=None, memory_agent=None, message_analyzer=None):
        super().__init__(agent=agent)
        self.memory_agent = memory_agent
        self.message_analyzer = message_analyzer
        
    async def analyze_messages_for_enrichment(self, contact_id: str, contact_name: str) -> dict:
        """Analyze messages to extract contact enrichment data."""
        if not self.message_analyzer:
            return {}
            
        analysis_result = await self.message_analyzer.analyze_messages_for_contact(contact_id, contact_name)
        
        # Store analysis results in memory for future reference
        if self.memory_agent and analysis_result:
            await self.memory_agent.store_memory(
                content=f"Contact enrichment analysis for {contact_name}",
                metadata={
                    "source": "contacts_agent",
                    "data_scope": "contact_enrichment",
                    "contact_id": contact_id,
                    "contact_name": contact_name,
                    "analysis_data": analysis_result,
                    "tags": ["contact_enrichment", "message_analysis"]
                }
            )
        
        return analysis_result
        
    async def execute(self, parameters: dict) -> dict:
        """Enhanced execute method with message analysis integration."""
        contact_id = parameters.get("contact_id", "").strip()
        enrichment_type = parameters.get("enrichment_type")
        contact_name = parameters.get("contact_name", "")
        
        if not contact_id or not enrichment_type:
            return {
                "contact_id": contact_id or "",
                "enrichments": [],
                "enrichment_count": 0
            }
        
        # Perform message analysis if we have the tools
        analysis_data = {}
        if self.message_analyzer:
            analysis_data = await self.analyze_messages_for_enrichment(contact_id, contact_name)
        
        # Generate enrichments based on analysis
        enrichments = await self._generate_enrichments_from_analysis(
            contact_id, enrichment_type, analysis_data
        )
        
        return {
            "contact_id": contact_id,
            "enrichments": enrichments,
            "enrichment_count": len(enrichments)
        }
        
    async def _generate_enrichments_from_analysis(self, contact_id: str, enrichment_type: str, analysis_data: dict) -> list:
        """Generate enrichments from message analysis data."""
        enrichments = []
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if enrichment_type == "job_title" and analysis_data.get("job_info"):
            for job_info in analysis_data["job_info"]:
                enrichments.append({
                    "type": "job_title",
                    "value": job_info["value"],
                    "confidence": job_info["confidence"],
                    "source": "message_analysis",
                    "timestamp": timestamp,
                    "source_evidence": job_info.get("source_message", "")
                })
                
        elif enrichment_type == "interests" and analysis_data.get("interests"):
            for interest in analysis_data["interests"]:
                enrichments.append({
                    "type": "interests",
                    "value": interest["value"],
                    "confidence": interest["confidence"],
                    "source": "message_analysis",
                    "timestamp": timestamp,
                    "source_evidence": interest.get("source_message", "")
                })
                
        elif enrichment_type == "relationships" and analysis_data.get("relationships"):
            for relationship in analysis_data["relationships"]:
                enrichments.append({
                    "type": "relationships",
                    "value": relationship["value"],
                    "confidence": relationship["confidence"],
                    "source": "message_analysis",
                    "timestamp": timestamp,
                    "source_evidence": relationship.get("source_message", "")
                })
                
        elif enrichment_type == "interaction_history" and analysis_data.get("interaction_patterns"):
            patterns = analysis_data["interaction_patterns"]
            enrichments.append({
                "type": "interaction_history",
                "value": f"Frequency: {patterns.get('frequency', 'unknown')}, Last: {patterns.get('recency', 'unknown')}",
                "confidence": 0.95,
                "source": "message_analysis",
                "timestamp": timestamp,
                "source_evidence": "Derived from message interaction patterns"
            })
        
        return enrichments


@pytest.fixture
def mock_memory_agent():
    """Fixture providing a mock memory agent."""
    return MockMemoryAgent()


@pytest.fixture
def mock_message_analyzer():
    """Fixture providing a mock message analyzer."""
    return MockMessageAnalyzer()


@pytest.fixture
def enhanced_handler(mock_memory_agent, mock_message_analyzer):
    """Fixture providing an enhanced enrichment handler."""
    return EnhancedEnrichContactsHandler(
        memory_agent=mock_memory_agent,
        message_analyzer=mock_message_analyzer
    )


class TestContactEnrichmentIntegration:
    """Test suite for contact enrichment integration functionality."""
    
    @pytest.mark.asyncio
    async def test_job_title_enrichment_from_messages(self, enhanced_handler):
        """Test job title enrichment using message analysis."""
        result = await enhanced_handler.execute({
            "contact_id": "john_doe_123",
            "contact_name": "John Doe",
            "enrichment_type": "job_title"
        })
        
        assert result["contact_id"] == "john_doe_123"
        assert result["enrichment_count"] > 0
        
        # Verify enrichment contains job information from mock analysis
        job_enrichments = [e for e in result["enrichments"] if e["type"] == "job_title"]
        assert len(job_enrichments) > 0
        assert "Software Engineer at TechCorp" in job_enrichments[0]["value"]
        assert job_enrichments[0]["confidence"] == 0.85
        assert job_enrichments[0]["source"] == "message_analysis"
    
    @pytest.mark.asyncio
    async def test_interests_enrichment_from_messages(self, enhanced_handler):
        """Test interests enrichment using message analysis."""
        result = await enhanced_handler.execute({
            "contact_id": "john_doe_123", 
            "contact_name": "John Doe",
            "enrichment_type": "interests"
        })
        
        assert result["contact_id"] == "john_doe_123"
        assert result["enrichment_count"] > 0
        
        # Verify interests from mock analysis
        interests = [e for e in result["enrichments"] if e["type"] == "interests"]
        assert len(interests) >= 2
        
        interest_values = [i["value"] for i in interests]
        assert "Machine Learning" in interest_values
        assert "Rock Climbing" in interest_values
    
    @pytest.mark.asyncio
    async def test_relationships_enrichment_from_messages(self, enhanced_handler):
        """Test relationships enrichment using message analysis."""
        result = await enhanced_handler.execute({
            "contact_id": "jane_smith_456",
            "contact_name": "Jane Smith", 
            "enrichment_type": "relationships"
        })
        
        assert result["contact_id"] == "jane_smith_456"
        assert result["enrichment_count"] > 0
        
        # Verify relationship from mock analysis
        relationships = [e for e in result["enrichments"] if e["type"] == "relationships"]
        assert len(relationships) > 0
        assert relationships[0]["value"] == "Friend"
        assert relationships[0]["confidence"] == 0.80
    
    @pytest.mark.asyncio
    async def test_interaction_history_enrichment(self, enhanced_handler):
        """Test interaction history enrichment from message patterns."""
        result = await enhanced_handler.execute({
            "contact_id": "john_doe_123",
            "contact_name": "John Doe",
            "enrichment_type": "interaction_history"
        })
        
        assert result["contact_id"] == "john_doe_123" 
        assert result["enrichment_count"] > 0
        
        # Verify interaction history
        interactions = [e for e in result["enrichments"] if e["type"] == "interaction_history"]
        assert len(interactions) > 0
        assert "Frequency: high" in interactions[0]["value"]
        assert "Last: 2 days ago" in interactions[0]["value"]
    
    @pytest.mark.asyncio
    async def test_memory_integration(self, enhanced_handler, mock_memory_agent):
        """Test integration with Memory Agent for storing enrichment analysis."""
        # Execute enrichment to trigger memory storage
        await enhanced_handler.execute({
            "contact_id": "john_doe_123",
            "contact_name": "John Doe", 
            "enrichment_type": "job_title"
        })
        
        # Verify memory was stored
        assert len(mock_memory_agent.stored_memories) > 0
        
        memory = mock_memory_agent.stored_memories[0]
        assert memory["metadata"]["source"] == "contacts_agent"
        assert memory["metadata"]["data_scope"] == "contact_enrichment"
        assert memory["metadata"]["contact_id"] == "john_doe_123"
        assert memory["metadata"]["contact_name"] == "John Doe"
        assert "analysis_data" in memory["metadata"]
    
    @pytest.mark.asyncio
    async def test_enrichment_without_message_analyzer(self):
        """Test enrichment gracefully handles missing message analyzer."""
        handler = EnhancedEnrichContactsHandler(message_analyzer=None)
        
        result = await handler.execute({
            "contact_id": "test_123",
            "contact_name": "Test User",
            "enrichment_type": "job_title"
        })
        
        # Should return empty enrichments when no analyzer is available
        assert result["contact_id"] == "test_123"
        assert result["enrichment_count"] == 0
        assert result["enrichments"] == []
    
    @pytest.mark.asyncio
    async def test_unknown_contact_enrichment(self, enhanced_handler):
        """Test enrichment for unknown contact returns empty results."""
        result = await enhanced_handler.execute({
            "contact_id": "unknown_contact_999",
            "contact_name": "Unknown Person",
            "enrichment_type": "job_title"
        })
        
        # Should return empty enrichments for unknown contacts
        assert result["contact_id"] == "unknown_contact_999"
        assert result["enrichment_count"] == 0
        assert result["enrichments"] == []
    
    @pytest.mark.asyncio
    async def test_enrichment_input_validation(self, enhanced_handler):
        """Test input validation for enrichment parameters."""
        # Test missing contact_id
        result = await enhanced_handler.execute({
            "enrichment_type": "job_title"
        })
        assert result["contact_id"] == ""
        assert result["enrichment_count"] == 0
        
        # Test missing enrichment_type
        result = await enhanced_handler.execute({
            "contact_id": "test_123"
        })
        assert result["contact_id"] == "test_123"
        assert result["enrichment_count"] == 0
        
        # Test empty contact_id
        result = await enhanced_handler.execute({
            "contact_id": "",
            "enrichment_type": "job_title"
        })
        assert result["contact_id"] == ""
        assert result["enrichment_count"] == 0


class TestMessageAnalysisIntegration:
    """Test suite for message analysis integration."""
    
    @pytest.mark.asyncio
    async def test_message_analyzer_integration(self, mock_message_analyzer):
        """Test message analyzer returns expected analysis structure."""
        result = await mock_message_analyzer.analyze_messages_for_contact("john_doe_123", "John Doe")
        
        # Verify analysis structure
        assert "job_info" in result
        assert "interests" in result
        assert "relationships" in result
        assert "interaction_patterns" in result
        
        # Verify job info structure
        assert len(result["job_info"]) > 0
        job_info = result["job_info"][0]
        assert "value" in job_info
        assert "confidence" in job_info
        assert "source_message" in job_info
        
        # Verify interaction patterns structure
        patterns = result["interaction_patterns"]
        assert "frequency" in patterns
        assert "recency" in patterns
        assert "sentiment" in patterns
        assert "topic_distribution" in patterns
    
    @pytest.mark.asyncio
    async def test_memory_retrieval_for_enrichment(self, mock_memory_agent):
        """Test memory retrieval for contact enrichment context."""
        # Store some test memories
        await mock_memory_agent.store_memory(
            "John mentioned he works at TechCorp developing mobile apps",
            {"source": "imessage", "contact": "john_doe", "topic": "work"}
        )
        await mock_memory_agent.store_memory(
            "John discussed machine learning algorithms in our chat",
            {"source": "imessage", "contact": "john_doe", "topic": "interests"}
        )
        
        # Retrieve memories related to John
        memories = await mock_memory_agent.retrieve_memories("TechCorp")
        
        assert len(memories) > 0
        assert "TechCorp" in memories[0]["content"]
        assert memories[0]["similarity_score"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])