"""
Contact enrichment capability handler.

This handler implements the contacts.enrich capability for adding
additional information to contacts from various sources.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler


class EnrichContactsHandler(BaseCapabilityHandler):
    """Handler for the contacts.enrich capability."""
    
    capability = "contacts.enrich"
    
    def __init__(self, agent=None):
        """Initialize the enrich contacts handler."""
        self.agent = agent  # Store reference to agent for tool access
        super().__init__(
            capability="contacts.enrich",
            description="Enrich contact information from various sources",
            input_schema={
                "type": "object",
                "properties": {
                    "contact_id": {"type": "string", "description": "Contact ID to enrich"},
                    "enrichment_type": {"type": "string", "enum": ["job_title", "interests", "relationships", "interaction_history"], "description": "Type of enrichment to perform"},
                    "source_platform": {"type": "string", "enum": ["mail", "whatsapp", "imessage", "calendar"], "description": "Platform providing enrichment data"}
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
        Execute the contacts.enrich capability.
        
        Args:
            parameters: Input parameters containing contact_id and enrichment options
            
        Returns:
            Dictionary with enrichments and count
        """
        contact_id = parameters.get("contact_id", "").strip()
        enrichment_type = parameters.get("enrichment_type")
        source_platform = parameters.get("source_platform")
        
        if not contact_id or not enrichment_type:
            return {
                "contact_id": contact_id or "",
                "enrichments": [],
                "enrichment_count": 0
            }
        
        # For now, return mock data - this will be replaced with actual enrichment
        # TODO: Integrate with contacts bridge tool for real enrichment
        mock_enrichments = self._generate_mock_enrichments(contact_id, enrichment_type, source_platform)
        
        return {
            "contact_id": contact_id,
            "enrichments": mock_enrichments,
            "enrichment_count": len(mock_enrichments)
        }
    
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
