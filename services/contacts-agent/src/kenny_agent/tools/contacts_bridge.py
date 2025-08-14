"""
Contacts Bridge Tool for integrating with the macOS bridge and local database.

This tool provides access to contact data through both the bridge service
and the local contacts database.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
import asyncio

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_tool import BaseTool
from ..database import ContactsDatabase


class ContactsBridgeTool(BaseTool):
    """Tool for accessing contact data through the macOS bridge and local database."""
    
    name = "contacts_bridge"
    description = "Access contact data through the macOS bridge service and local database"
    
    def __init__(self):
        """Initialize the contacts bridge tool."""
        super().__init__(
            name="contacts_bridge",
            description="Access contact data through the macOS bridge service and local database",
            version="1.0.0",
            category="bridge"
        )
        
        # Bridge URL configuration
        import os
        self.bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        self.timeout = 65.0  # 65 second timeout for bridge requests (JXA is slow)
        
        # Initialize local database
        self.db = ContactsDatabase()
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the contacts bridge tool.
        
        Args:
            parameters: Tool parameters
            
        Returns:
            Tool execution result
        """
        # This is a placeholder implementation
        # In a real implementation, this would route to specific methods
        return {
            "status": "success",
            "message": "Contacts bridge tool executed",
            "parameters": parameters
        }
    
    async def get_contacts(self, query: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get contacts from the local database.
        
        Args:
            query: Optional search query
            limit: Maximum number of contacts to return
            
        Returns:
            List of contact objects
        """
        try:
            if query:
                # Use database search for queried contacts
                contacts = self.db.search_contacts(query, fuzzy_match=True)
                return contacts[:limit]
            else:
                # For now, return a few sample contacts if no query
                # TODO: Add a get_all_contacts method to database
                sample_contacts = self.db.search_contacts("", fuzzy_match=True)
                return sample_contacts[:limit]
            
        except Exception as e:
            print(f"[contacts-bridge] Error getting contacts: {e}")
            return []
    
    async def search_contacts(self, identifier: str, platform: str = None) -> List[Dict[str, Any]]:
        """
        Search for contacts by identifier.
        
        Args:
            identifier: Email, phone, or name to search for
            platform: Optional platform context
            
        Returns:
            List of matching contacts
        """
        try:
            # First try bridge for live macOS Contacts data
            bridge_contacts = await self._fetch_from_bridge(query=identifier)
            if bridge_contacts:
                print(f"[contacts-bridge] Got {len(bridge_contacts)} contacts from bridge")
                return bridge_contacts
            
            # Fallback to local database
            print(f"[contacts-bridge] Falling back to local database search")
            contacts = self.db.search_contacts(identifier, platform=platform, fuzzy_match=True)
            
            # Add platform information to results
            for contact in contacts:
                if 'platforms' not in contact:
                    contact['platforms'] = ['local']  # Default platform
            
            return contacts
            
        except Exception as e:
            print(f"[contacts-bridge] Error searching contacts: {e}")
            return []
    
    async def enrich_contact(self, contact_id: str, enrichment_type: str) -> List[Dict[str, Any]]:
        """
        Enrich contact information.
        
        Args:
            contact_id: Contact ID to enrich
            enrichment_type: Type of enrichment to perform
            
        Returns:
            List of enrichment objects
        """
        try:
            # Get existing enrichments from database
            enrichments = self.db.get_contact_enrichments(contact_id, enrichment_type)
            
            # Convert database format to expected format
            result = []
            for enrichment in enrichments:
                result.append({
                    "type": enrichment["enrichment_type"],
                    "value": enrichment["enrichment_value"],
                    "confidence": enrichment["confidence"],
                    "source": enrichment["source_platform"],
                    "timestamp": enrichment["created_at"]
                })
            
            return result
            
        except Exception as e:
            print(f"[contacts-bridge] Error enriching contact: {e}")
            return []
    
    async def _fetch_from_bridge(self, query: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch contacts from the macOS bridge service.
        
        Args:
            query: Search query for contacts
            limit: Maximum number of contacts to return
            
        Returns:
            List of contact objects from bridge
        """
        try:
            import httpx
            
            # Prepare request parameters
            params = {"limit": limit}
            if query and query.strip():
                params["query"] = query.strip()
            
            # Make request to bridge
            print(f"[contacts-bridge] Fetching from bridge: {self.bridge_url}/v1/contacts")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.bridge_url}/v1/contacts",
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                contacts = response.json()
                print(f"[contacts-bridge] Bridge returned {len(contacts)} contacts")
                
                # Filter out contacts without sufficient information
                valid_contacts = []
                for contact in contacts:
                    if (contact.get("name") or 
                        contact.get("emails") or 
                        contact.get("phones")):
                        valid_contacts.append(contact)
                
                return valid_contacts
                
        except httpx.HTTPError as e:
            print(f"[contacts-bridge] HTTP error fetching from bridge: {e}")
            return []
        except httpx.TimeoutException:
            print(f"[contacts-bridge] Timeout fetching from bridge after {self.timeout}s")
            return []
        except Exception as e:
            print(f"[contacts-bridge] Error fetching from bridge: {e}")
            return []
    
    def close(self):
        """Close database connections and cleanup resources."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def __del__(self):
        """Cleanup on destruction."""
        self.close()
