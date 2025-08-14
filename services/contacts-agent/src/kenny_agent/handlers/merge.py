"""
Contact merging capability handler.

This handler implements the contacts.merge capability for merging
duplicate contacts with conflict resolution.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import uuid

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler


class MergeContactsHandler(BaseCapabilityHandler):
    """Handler for the contacts.merge capability."""
    
    capability = "contacts.merge"
    
    def __init__(self, agent=None):
        """Initialize the merge contacts handler."""
        self.agent = agent  # Store reference to agent for tool access
        super().__init__(
            capability="contacts.merge",
            description="Merge duplicate contacts with conflict resolution",
            input_schema={
                "type": "object",
                "properties": {
                    "primary_contact_id": {"type": "string", "description": "Primary contact to keep"},
                    "duplicate_contact_ids": {"type": "array", "items": {"type": "string"}, "description": "Duplicate contacts to merge"},
                    "merge_strategy": {"type": "string", "enum": ["merge_all", "selective", "manual"], "default": "merge_all", "description": "How to handle conflicts"}
                },
                "required": ["primary_contact_id", "duplicate_contact_ids"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "merged_contact_id": {"type": "string"},
                    "merged_attributes": {
                        "type": "object",
                        "additionalProperties": True
                    },
                    "merged_count": {"type": "integer"},
                    "conflicts_resolved": {"type": "integer"}
                },
                "required": ["merged_contact_id", "merged_count"],
                "additionalProperties": False
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the contacts.merge capability.
        
        Args:
            parameters: Input parameters containing contact IDs and merge strategy
            
        Returns:
            Dictionary with merge results
        """
        primary_contact_id = parameters.get("primary_contact_id", "").strip()
        duplicate_contact_ids = parameters.get("duplicate_contact_ids", [])
        merge_strategy = parameters.get("merge_strategy", "merge_all")
        
        if not primary_contact_id:
            return {
                "merged_contact_id": "",
                "merged_count": 0,
                "conflicts_resolved": 0
            }
        
        # For now, return mock data - this will be replaced with actual merging
        # TODO: Integrate with contacts bridge tool for real contact merging
        mock_result = self._generate_mock_merge_result(primary_contact_id, duplicate_contact_ids, merge_strategy)
        
        return mock_result
    
    def _generate_mock_merge_result(self, primary_contact_id: str, duplicate_contact_ids: List[str], merge_strategy: str) -> Dict[str, Any]:
        """
        Generate mock merge result data for testing.
        
        Args:
            primary_contact_id: The primary contact ID to keep
            duplicate_contact_ids: List of duplicate contact IDs to merge
            merge_strategy: Strategy for handling conflicts
            
        Returns:
            Mock merge result object
        """
        # Generate a new merged contact ID
        merged_contact_id = str(uuid.uuid4())
        
        # Mock merged attributes
        merged_attributes = {
            "name": "John Doe (Merged)",
            "emails": ["john.doe@example.com", "j.doe@company.com"],
            "phones": ["+1-555-0123", "+1-555-4567"],
            "platforms": ["mail", "whatsapp", "imessage"],
            "merge_strategy": merge_strategy,
            "merged_at": "2025-01-13T12:00:00Z"
        }
        
        return {
            "merged_contact_id": merged_contact_id,
            "merged_attributes": merged_attributes,
            "merged_count": len(duplicate_contact_ids) + 1,  # +1 for primary
            "conflicts_resolved": len(duplicate_contact_ids) * 2  # Mock conflict count
        }
