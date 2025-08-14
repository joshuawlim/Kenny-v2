"""
Memory Agent client tool for cross-agent integration.

This tool provides an interface for the Contacts Agent to interact with
the Memory Agent for storing and retrieving enrichment data.
"""

import sys
import logging
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_tool import BaseTool


class MemoryClient(BaseTool):
    """Tool for interacting with the Memory Agent."""
    
    def __init__(self, memory_agent_url: str = "http://localhost:8003"):
        """Initialize the memory client tool."""
        super().__init__(
            name="memory_client",
            description="Client for interacting with the Memory Agent for storage and retrieval"
        )
        self.memory_agent_url = memory_agent_url
        self.logger = logging.getLogger(__name__)
        
    async def store_contact_enrichment(
        self, 
        contact_id: str, 
        contact_name: str, 
        enrichment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store contact enrichment data in the Memory Agent.
        
        Args:
            contact_id: Unique identifier for the contact
            contact_name: Display name of the contact
            enrichment_data: Enrichment data to store
            
        Returns:
            Dict containing storage result
        """
        try:
            content = f"Contact enrichment for {contact_name}: {self._summarize_enrichment(enrichment_data)}"
            
            payload = {
                "input": {
                    "content": content,
                    "metadata": {
                        "source": "contacts_agent",
                        "data_scope": "contact_enrichment",
                        "contact_id": contact_id,
                        "contact_name": contact_name,
                        "enrichment_timestamp": datetime.now(timezone.utc).isoformat(),
                        "tags": ["contact_enrichment", "message_analysis"],
                        "importance": self._calculate_importance(enrichment_data),
                        "context": {
                            "enrichment_data": enrichment_data
                        }
                    },
                    "auto_embed": True,
                    "embedding_model": "nomic-embed-text"
                }
            }
            
            response = requests.post(
                f"{self.memory_agent_url}/capabilities/memory.store",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Successfully stored enrichment data for {contact_name}")
                return {
                    "success": True,
                    "memory_id": result.get("result", {}).get("memory_id"),
                    "stored_at": result.get("result", {}).get("stored_at")
                }
            else:
                self.logger.error(f"Failed to store enrichment data: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            self.logger.error(f"Error storing contact enrichment: {e}")
            return {"success": False, "error": str(e)}
    
    async def retrieve_contact_memories(
        self, 
        contact_name: str, 
        query: str = "", 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories related to a specific contact.
        
        Args:
            contact_name: Name of the contact to search for
            query: Additional search query
            limit: Maximum number of memories to retrieve
            
        Returns:
            List of relevant memories
        """
        try:
            # Combine contact name with query for more targeted search
            search_query = f"{contact_name} {query}".strip()
            
            payload = {
                "input": {
                    "query": search_query,
                    "limit": limit,
                    "similarity_threshold": 0.6,
                    "include_metadata": True
                }
            }
            
            response = requests.post(
                f"{self.memory_agent_url}/capabilities/memory.retrieve",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                memories = result.get("result", {}).get("memories", [])
                
                # Filter for contact-related memories
                contact_memories = []
                for memory in memories:
                    metadata = memory.get("metadata", {})
                    if (metadata.get("contact_name", "").lower() == contact_name.lower() or
                        contact_name.lower() in memory.get("content", "").lower()):
                        contact_memories.append(memory)
                
                self.logger.info(f"Retrieved {len(contact_memories)} memories for {contact_name}")
                return contact_memories
            else:
                self.logger.error(f"Failed to retrieve memories: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving contact memories: {e}")
            return []
    
    async def enrich_from_memories(
        self, 
        contact_id: str, 
        contact_name: str,
        enrichment_type: str
    ) -> List[Dict[str, Any]]:
        """
        Enrich contact data using existing memories.
        
        Args:
            contact_id: Contact identifier
            contact_name: Contact display name
            enrichment_type: Type of enrichment to perform
            
        Returns:
            List of enrichments from memory data
        """
        try:
            # Search for memories related to the enrichment type
            query_map = {
                "job_title": f"{contact_name} work job company occupation",
                "interests": f"{contact_name} interests hobbies likes enjoys",
                "relationships": f"{contact_name} relationship friend colleague family",
                "interaction_history": f"{contact_name} messages conversations contact"
            }
            
            query = query_map.get(enrichment_type, contact_name)
            memories = await self.retrieve_contact_memories(contact_name, query, 5)
            
            if not memories:
                return []
            
            # Extract enrichments from memory data
            enrichments = []
            for memory in memories:
                enrichment = self._extract_enrichment_from_memory(
                    memory, enrichment_type, contact_name
                )
                if enrichment:
                    enrichments.append(enrichment)
            
            return enrichments
            
        except Exception as e:
            self.logger.error(f"Error enriching from memories: {e}")
            return []
    
    def _summarize_enrichment(self, enrichment_data: Dict[str, Any]) -> str:
        """Create a summary of enrichment data for storage."""
        summary_parts = []
        
        if enrichment_data.get("job_info"):
            job_values = [job["value"] for job in enrichment_data["job_info"]]
            summary_parts.append(f"Job: {', '.join(job_values)}")
        
        if enrichment_data.get("interests"):
            interest_values = [interest["value"] for interest in enrichment_data["interests"]]
            summary_parts.append(f"Interests: {', '.join(interest_values)}")
        
        if enrichment_data.get("relationships"):
            rel_values = [rel["value"] for rel in enrichment_data["relationships"]]
            summary_parts.append(f"Relationship: {', '.join(rel_values)}")
        
        if enrichment_data.get("interaction_patterns"):
            patterns = enrichment_data["interaction_patterns"]
            summary_parts.append(f"Interaction: {patterns.get('frequency', 'unknown')} frequency")
        
        return "; ".join(summary_parts) if summary_parts else "Contact enrichment data"
    
    def _calculate_importance(self, enrichment_data: Dict[str, Any]) -> float:
        """Calculate importance score for enrichment data."""
        score = 0.5  # Base score
        
        # Higher score for more enrichment types
        if enrichment_data.get("job_info"):
            score += 0.1
        if enrichment_data.get("interests"):
            score += 0.1
        if enrichment_data.get("relationships"):
            score += 0.1
        
        # Higher score for high-confidence data
        for enrichment_type in ["job_info", "interests", "relationships"]:
            items = enrichment_data.get(enrichment_type, [])
            if items:
                avg_confidence = sum(item.get("confidence", 0) for item in items) / len(items)
                score += avg_confidence * 0.1
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _extract_enrichment_from_memory(
        self, 
        memory: Dict[str, Any], 
        enrichment_type: str, 
        contact_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract enrichment data from a memory entry."""
        try:
            content = memory.get("content", "")
            metadata = memory.get("metadata", {})
            
            # Check if memory contains enrichment data in context
            enrichment_data = metadata.get("context", {}).get("enrichment_data")
            if enrichment_data and enrichment_type in ["job_info", "interests", "relationships"]:
                items = enrichment_data.get(enrichment_type.replace("_title", "_info"), [])
                if items:
                    # Return the first enrichment with memory source
                    item = items[0]
                    return {
                        "type": enrichment_type,
                        "value": item["value"],
                        "confidence": item["confidence"] * 0.9,  # Slightly lower for memory source
                        "source": "memory_analysis",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "source_evidence": f"From stored memory: {content[:100]}..."
                    }
            
            # For interaction history, extract from metadata
            if enrichment_type == "interaction_history" and enrichment_data:
                patterns = enrichment_data.get("interaction_patterns", {})
                return {
                    "type": "interaction_history",
                    "value": f"Previous analysis: {patterns.get('frequency', 'unknown')} frequency",
                    "confidence": 0.8,
                    "source": "memory_analysis",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "source_evidence": "From stored interaction analysis"
                }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error extracting enrichment from memory: {e}")
            return None
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the memory client tool.
        
        Args:
            parameters: Contains action and relevant data for memory operations
            
        Returns:
            Dict containing operation results
        """
        action = parameters.get("action", "")
        
        try:
            if action == "store_enrichment":
                contact_id = parameters.get("contact_id", "")
                contact_name = parameters.get("contact_name", "")
                enrichment_data = parameters.get("enrichment_data", {})
                
                result = await self.store_contact_enrichment(contact_id, contact_name, enrichment_data)
                return result
                
            elif action == "retrieve_memories":
                contact_name = parameters.get("contact_name", "")
                query = parameters.get("query", "")
                limit = parameters.get("limit", 10)
                
                memories = await self.retrieve_contact_memories(contact_name, query, limit)
                return {"success": True, "memories": memories}
                
            elif action == "enrich_from_memories":
                contact_id = parameters.get("contact_id", "")
                contact_name = parameters.get("contact_name", "")
                enrichment_type = parameters.get("enrichment_type", "")
                
                enrichments = await self.enrich_from_memories(contact_id, contact_name, enrichment_type)
                return {"success": True, "enrichments": enrichments}
                
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Return tool usage summary."""
        return {
            "tool_name": self.name,
            "description": self.description,
            "usage_count": self.usage_count,
            "average_execution_time": self.average_execution_time
        }