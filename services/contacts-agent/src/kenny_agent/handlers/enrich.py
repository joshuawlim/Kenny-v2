"""
Contact enrichment capability handler.

This handler implements the contacts.enrich capability for adding
additional information to contacts from various sources including
message analysis and cross-agent memory integration.
"""

import sys
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler


class EnrichContactsHandler(BaseCapabilityHandler):
    """Handler for the contacts.enrich capability."""
    
    capability = "contacts.enrich"
    
    def __init__(self, agent=None, message_analyzer=None, memory_client=None):
        """Initialize the enrich contacts handler."""
        self.agent = agent  # Store reference to agent for tool access
        self.message_analyzer = message_analyzer
        self.memory_client = memory_client
        self.logger = logging.getLogger(__name__)
        
        super().__init__(
            capability="contacts.enrich",
            description="Enrich contact information from message analysis and cross-agent memory integration",
            input_schema={
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "Contact ID to enrich"},
                    "contact_name": {"type": "string", "description": "Contact display name for analysis"},
                    "enrichment_type": {"type": "string", "enum": ["job_title", "interests", "relationships", "interaction_history"], "description": "Type of enrichment to perform"},
                    "source_platform": {"type": "string", "enum": ["mail", "whatsapp", "imessage", "calendar", "memory"], "description": "Platform providing enrichment data"},
                    "use_message_analysis": {"type": "boolean", "default": True, "description": "Whether to use message analysis for enrichment"},
                    "use_memory_integration": {"type": "boolean", "default": True, "description": "Whether to use memory integration for enrichment"}
                },
                "required": ["contact_id", "enrichment_type"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string"},
                    "enrichments": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "value": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "source": {"type": "string"},
                                "timestamp": {"type": "string", "format": "date-time"}
                            },
                            "required": ["type", "value", "confidence", "source"]
                        }
                    },
                    "enrichment_count": {"type": "integer"}
                },
                "required": ["contact_id", "enrichments", "enrichment_count"],
                "additionalProperties": False
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the contacts.enrich capability using message analysis and memory integration.
        
        Args:
            parameters: Input parameters containing contact_id and enrichment options
            
        Returns:
            Dictionary with enrichments and count
        """
        contact_id = parameters.get("contact_id", "").strip()
        contact_name = parameters.get("contact_name", "").strip()
        enrichment_type = parameters.get("enrichment_type")
        use_message_analysis = parameters.get("use_message_analysis", True)
        use_memory_integration = parameters.get("use_memory_integration", True)
        
        if not contact_id or not enrichment_type:
            return {
                "contact_id": contact_id or "",
                "enrichments": [],
                "enrichment_count": 0
            }
        
        all_enrichments = []
        
        try:
            # Get enrichments from memory first (fast)
            if use_memory_integration and self.memory_client:
                memory_enrichments = await self._get_memory_enrichments(
                    contact_id, contact_name, enrichment_type
                )
                all_enrichments.extend(memory_enrichments)
                self.logger.info(f"Found {len(memory_enrichments)} memory enrichments for {contact_name}")
            
            # Get enrichments from message analysis (slower)
            if use_message_analysis and self.message_analyzer:
                message_enrichments = await self._get_message_enrichments(
                    contact_id, contact_name, enrichment_type
                )
                all_enrichments.extend(message_enrichments)
                self.logger.info(f"Found {len(message_enrichments)} message enrichments for {contact_name}")
            
            # If no tools available, fallback to mock data
            if not all_enrichments and not self.message_analyzer and not self.memory_client:
                all_enrichments = self._generate_mock_enrichments(contact_id, enrichment_type, None)
                self.logger.info(f"Using mock enrichments for {contact_name}")
            
            # Remove duplicates and sort by confidence
            unique_enrichments = self._deduplicate_enrichments(all_enrichments)
            
            return {
                "contact_id": contact_id,
                "enrichments": unique_enrichments,
                "enrichment_count": len(unique_enrichments)
            }
            
        except Exception as e:
            self.logger.error(f"Error enriching contact {contact_name}: {e}")
            return {
                "contact_id": contact_id,
                "enrichments": [],
                "enrichment_count": 0
            }
    
    async def _get_memory_enrichments(self, contact_id: str, contact_name: str, enrichment_type: str) -> List[Dict[str, Any]]:
        """Get enrichments from memory agent."""
        try:
            enrichments = await self.memory_client.enrich_from_memories(
                contact_id, contact_name, enrichment_type
            )
            return enrichments
        except Exception as e:
            self.logger.error(f"Error getting memory enrichments: {e}")
            return []
    
    async def _get_message_enrichments(self, contact_id: str, contact_name: str, enrichment_type: str) -> List[Dict[str, Any]]:
        """Get enrichments from message analysis."""
        try:
            # Analyze messages for the contact
            analysis_result = await self.message_analyzer.analyze_messages_for_contact(
                contact_id, contact_name
            )
            
            # Store the analysis in memory for future use
            if self.memory_client:
                await self.memory_client.store_contact_enrichment(
                    contact_id, contact_name, analysis_result
                )
            
            # Convert analysis to enrichments
            enrichments = self._convert_analysis_to_enrichments(analysis_result, enrichment_type)
            return enrichments
            
        except Exception as e:
            self.logger.error(f"Error getting message enrichments: {e}")
            return []
    
    def _convert_analysis_to_enrichments(self, analysis_result: Dict[str, Any], enrichment_type: str) -> List[Dict[str, Any]]:
        """Convert message analysis results to enrichment format."""
        enrichments = []
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if enrichment_type == "job_title" and analysis_result.get("job_info"):
            for job_info in analysis_result["job_info"]:
                enrichments.append({
                    "type": "job_title",
                    "value": job_info["value"],
                    "confidence": job_info["confidence"],
                    "source": "message_analysis",
                    "timestamp": timestamp,
                    "source_evidence": job_info.get("source_evidence", "")
                })
                
        elif enrichment_type == "interests" and analysis_result.get("interests"):
            for interest in analysis_result["interests"]:
                enrichments.append({
                    "type": "interests",
                    "value": interest["value"],
                    "confidence": interest["confidence"],
                    "source": "message_analysis",
                    "timestamp": timestamp,
                    "source_evidence": interest.get("source_evidence", "")
                })
                
        elif enrichment_type == "relationships" and analysis_result.get("relationships"):
            for relationship in analysis_result["relationships"]:
                enrichments.append({
                    "type": "relationships",
                    "value": relationship["value"],
                    "confidence": relationship["confidence"],
                    "source": "message_analysis",
                    "timestamp": timestamp,
                    "source_evidence": relationship.get("source_evidence", "")
                })
                
        elif enrichment_type == "interaction_history" and analysis_result.get("interaction_patterns"):
            patterns = analysis_result["interaction_patterns"]
            enrichments.append({
                "type": "interaction_history",
                "value": f"Frequency: {patterns.get('frequency', 'unknown')}, Last: {patterns.get('recency', 'unknown')}",
                "confidence": 0.95,
                "source": "message_analysis",
                "timestamp": timestamp,
                "source_evidence": "Derived from message interaction patterns"
            })
        
        return enrichments
    
    def _deduplicate_enrichments(self, enrichments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate enrichments and sort by confidence."""
        seen = set()
        unique_enrichments = []
        
        # Sort by confidence descending
        sorted_enrichments = sorted(enrichments, key=lambda x: x.get("confidence", 0), reverse=True)
        
        for enrichment in sorted_enrichments:
            # Create a key based on type and value (case-insensitive)
            key = (enrichment.get("type", ""), enrichment.get("value", "").lower())
            
            if key not in seen:
                seen.add(key)
                unique_enrichments.append(enrichment)
        
        return unique_enrichments
    
    def _generate_mock_enrichments(self, contact_id: str, enrichment_type: str, source_platform: str = None) -> List[Dict[str, Any]]:
        """
        Generate mock enrichment data for testing.
        
        Args:
            contact_id: The contact ID to enrich
            enrichment_type: Type of enrichment to perform
            source_platform: Optional source platform
            
        Returns:
            List of mock enrichment objects
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        
        if enrichment_type == "job_title":
            return [{
                "type": "job_title",
                "value": "Software Engineer",
                "confidence": 0.85,
                "source": source_platform or "mail",
                "timestamp": timestamp
            }]
        elif enrichment_type == "interests":
            return [
                {
                    "type": "interests",
                    "value": "Machine Learning",
                    "confidence": 0.80,
                    "source": source_platform or "mail",
                    "timestamp": timestamp
                },
                {
                    "type": "interests", 
                    "value": "Data Science",
                    "confidence": 0.75,
                    "source": source_platform or "whatsapp",
                    "timestamp": timestamp
                }
            ]
        elif enrichment_type == "relationships":
            return [{
                "type": "relationships",
                "value": "Colleague",
                "confidence": 0.90,
                "source": source_platform or "calendar",
                "timestamp": timestamp
            }]
        elif enrichment_type == "interaction_history":
            return [
                {
                    "type": "interaction_history",
                    "value": "Last email: 2 days ago",
                    "confidence": 0.95,
                    "source": source_platform or "mail",
                    "timestamp": timestamp
                },
                {
                    "type": "interaction_history",
                    "value": "Last message: 1 week ago", 
                    "confidence": 0.85,
                    "source": source_platform or "whatsapp",
                    "timestamp": timestamp
                }
            ]
        else:
            return []
