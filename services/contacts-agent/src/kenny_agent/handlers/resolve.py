"""
Contact resolution capability handler.

This handler implements the contacts.resolve capability for finding
and disambiguating contacts by various identifiers.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import re

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_handler import BaseCapabilityHandler


class ResolveContactsHandler(BaseCapabilityHandler):
    """Handler for the contacts.resolve capability."""
    
    capability = "contacts.resolve"
    
    def __init__(self):
        """Initialize the resolve contacts handler."""
        super().__init__(
            capability="contacts.resolve",
            description="Resolve contacts by identifier with fuzzy matching",
            input_schema={
                "type": "object",
                "properties": {
                    "identifier": {"type": "string", "description": "Email, phone, or name to resolve"},
                    "platform": {"type": "string", "enum": ["mail", "whatsapp", "imessage", "calendar"], "description": "Platform context for resolution"},
                    "fuzzy_match": {"type": "boolean", "default": True, "description": "Enable fuzzy name matching"}
                },
                "required": ["identifier"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "contacts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "emails": {"type": "array", "items": {"type": "string"}},
                                "phones": {"type": "array", "items": {"type": "string"}},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "platforms": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["id", "name", "confidence"]
                        }
                    },
                    "resolved_count": {"type": "integer"}
                },
                "required": ["contacts", "resolved_count"],
                "additionalProperties": False
            }
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the contacts.resolve capability.
        
        Args:
            parameters: Input parameters containing identifier and options
            
        Returns:
            Dictionary with resolved contacts and count
        """
        identifier = parameters.get("identifier", "").strip()
        platform = parameters.get("platform")
        fuzzy_match = parameters.get("fuzzy_match", True)
        
        if not identifier:
            return {
                "contacts": [],
                "resolved_count": 0
            }
        
        # For now, return mock data - this will be replaced with actual contact resolution
        # TODO: Integrate with contacts bridge tool for real contact lookup
        mock_contacts = self._generate_mock_contacts(identifier, platform, fuzzy_match)
        
        return {
            "contacts": mock_contacts,
            "resolved_count": len(mock_contacts)
        }
    
    def _generate_mock_contacts(self, identifier: str, platform: str = None, fuzzy_match: bool = True) -> List[Dict[str, Any]]:
        """
        Generate mock contact data for testing.
        
        Args:
            identifier: The identifier to resolve
            platform: Optional platform context
            
        Returns:
            List of mock contact objects
        """
        # Simple mock data for testing
        if "@" in identifier:  # Email
            return [{
                "id": "mock-email-001",
                "name": "John Doe",
                "emails": [identifier],
                "phones": ["+1-555-0123"],
                "confidence": 0.95,
                "platforms": ["mail"]
            }]
        elif re.match(r'^\+?[\d\s\-\(\)]+$', identifier):  # Phone
            return [{
                "id": "mock-phone-001", 
                "name": "Jane Smith",
                "emails": ["jane.smith@example.com"],
                "phones": [identifier],
                "confidence": 0.90,
                "platforms": ["whatsapp", "imessage"]
            }]
        else:  # Name
            return [{
                "id": "mock-name-001",
                "name": identifier,
                "emails": ["contact@example.com"],
                "phones": ["+1-555-9999"],
                "confidence": 0.85 if fuzzy_match else 0.60,
                "platforms": ["mail", "calendar"]
            }]
