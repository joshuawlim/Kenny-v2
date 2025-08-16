"""
Intelligent Contacts Agent for Kenny v2.1

Enhanced Contacts Agent with embedded LLM capabilities for natural language
contact resolution, cross-platform integration, and semantic enrichment.

Key Enhancements:
- Natural language contact queries: "Find Sarah from the design team"
- Cross-platform contact enrichment from mail, calendar, and messaging
- Semantic contact matching with confidence scoring
- Relationship caching for performance optimization
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.agent_service_base import AgentServiceBase, ConfidenceResult
from kenny_agent.registry import AgentRegistryClient

from .handlers.resolve import ResolveContactsHandler
from .handlers.enrich import EnrichContactsHandler
from .handlers.merge import MergeContactsHandler
from .tools.contacts_bridge import ContactsBridgeTool
from .tools.message_analyzer import MessageAnalyzer
from .tools.memory_client import MemoryClient


class IntelligentContactsAgent(AgentServiceBase):
    """
    Enhanced Contacts Agent with LLM-driven natural language processing.
    
    Transforms from basic API wrapper to intelligent service:
    - Natural language contact resolution
    - Cross-platform contact enrichment
    - Semantic matching with confidence scoring
    - Relationship caching for performance
    """
    
    def __init__(self, llm_model: str = "llama3.2:3b"):
        """Initialize the Intelligent Contacts Agent."""
        super().__init__(
            agent_id="intelligent-contacts-agent",
            name="Intelligent Contacts Agent",
            description="AI-powered contact management with natural language processing, cross-platform enrichment, and semantic matching",
            version="2.1.0",
            llm_model=llm_model,
            data_scopes=["contacts:all", "mail:inbox", "mail:sent", "whatsapp:chats", "imessage:chats", "calendar:events"],
            tool_access=["macos-bridge", "sqlite-db", "ollama"],
            egress_domains=[],
            health_check={
                "endpoint": "/health",
                "interval_seconds": 60,
                "timeout_seconds": 10
            }
        )
        
        # Set fallback capability for low-confidence queries
        self.fallback_capability = "contacts.resolve"
        
        print(f"Initializing Intelligent Contacts Agent with LLM: {llm_model}")
        
        # Initialize tools
        self.message_analyzer = MessageAnalyzer()
        self.memory_client = MemoryClient()
        self.contacts_bridge_tool = ContactsBridgeTool()
        
        # Register tools
        self.register_tool(self.contacts_bridge_tool)
        self.register_tool(self.message_analyzer)
        self.register_tool(self.memory_client)
        
        # Register enhanced capability handlers
        print("Registering intelligent contact capabilities...")
        self.register_capability(EnhancedResolveContactsHandler(agent=self))
        self.register_capability(EnhancedEnrichContactsHandler(
            agent=self,
            message_analyzer=self.message_analyzer,
            memory_client=self.memory_client
        ))
        self.register_capability(EnhancedMergeContactsHandler(agent=self))
        
        # Register cross-platform dependencies
        self._register_cross_platform_dependencies()
        
        # Initialize registry client
        self.registry_client = AgentRegistryClient(
            base_url=os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
        )
        
        print(f"Registered capabilities: {list(self.capabilities.keys())}")
        print("Intelligent Contacts Agent initialization complete!")
    
    def _register_cross_platform_dependencies(self):
        """Register dependencies on other agents for cross-platform enrichment."""
        # Mail Agent for email contact analysis
        self.register_agent_dependency(
            agent_id="mail-agent",
            capabilities=["messages.search", "messages.read"],
            required=False,
            timeout=3.0
        )
        
        # iMessage Agent for message contact analysis  
        self.register_agent_dependency(
            agent_id="imessage-agent",
            capabilities=["messages.search", "messages.read"],
            required=False,
            timeout=3.0
        )
        
        # Calendar Agent for meeting attendee analysis
        self.register_agent_dependency(
            agent_id="calendar-agent", 
            capabilities=["calendar.read"],
            required=False,
            timeout=3.0
        )
        
        print("Registered cross-platform dependencies: mail, imessage, calendar")
    
    def get_agent_context(self) -> str:
        """Return context description for LLM interpretation."""
        return """Intelligent contact management agent specializing in:
        
- Natural language contact resolution and disambiguation
- Cross-platform contact enrichment from mail, messaging, and calendar
- Semantic contact matching with fuzzy name resolution
- Contact relationship analysis and caching
- Multi-platform contact deduplication and merging

I can understand queries like:
- "Find Sarah from the design team" 
- "Get contact info for john@company.com"
- "Find all contacts related to the marketing project"
- "Merge duplicate contacts for John Smith"
"""
    
    async def resolve_contact_with_context(self, query: str, platforms: List[str] = None) -> ConfidenceResult:
        """Enhanced contact resolution with cross-platform context."""
        platforms = platforms or ["contacts", "mail", "imessage", "calendar"]
        
        # Enrich query with cross-platform context
        enriched_context = await self.enrich_query_context(query, platforms)
        
        # Use enhanced execution with confidence scoring
        result = await self.execute_with_confidence(
            capability="contacts.resolve",
            parameters={
                "query": query,
                "enriched_context": enriched_context,
                "platforms": platforms
            },
            min_confidence=0.6
        )
        
        # Cache successful contact relationships
        if not result.fallback_used and result.confidence > 0.7:
            await self._cache_contact_relationships(result.result, platforms)
        
        return result
    
    async def _cache_contact_relationships(self, contact_result: Dict, platforms: List[str]):
        """Cache contact relationships for performance optimization."""
        if not isinstance(contact_result, dict) or "contacts" not in contact_result:
            return
        
        for contact in contact_result.get("contacts", []):
            contact_id = contact.get("id")
            if not contact_id:
                continue
            
            # Cache email relationships
            for email in contact.get("emails", []):
                await self.cache_entity_relationship(
                    entity_type="contact",
                    entity_id=contact_id,
                    related_entity_type="email",
                    related_entity_id=email,
                    relationship_data={
                        "type": "email",
                        "contact_name": contact.get("name"),
                        "confidence": contact.get("confidence", 1.0),
                        "platforms": contact.get("platforms", [])
                    }
                )
            
            # Cache phone relationships
            for phone in contact.get("phones", []):
                await self.cache_entity_relationship(
                    entity_type="contact",
                    entity_id=contact_id,
                    related_entity_type="phone",
                    related_entity_id=phone,
                    relationship_data={
                        "type": "phone", 
                        "contact_name": contact.get("name"),
                        "confidence": contact.get("confidence", 1.0),
                        "platforms": contact.get("platforms", [])
                    }
                )
    
    async def find_similar_contacts(self, query: str, threshold: float = 0.8) -> List[Dict]:
        """Find semantically similar contacts using cached data."""
        return await self.find_semantic_matches(
            query=query,
            entity_type="contact",
            threshold=threshold
        )
    
    async def enrich_contact_cross_platform(self, contact_id: str) -> Dict[str, Any]:
        """Enrich contact with data from all available platforms."""
        enrichment_results = {"contact_id": contact_id, "enrichments": []}
        
        # Get cached relationships first
        email_relationships = await self.get_entity_relationships(
            entity_type="contact",
            entity_id=contact_id,
            related_entity_type="email"
        )
        
        # Query mail agent for email interactions
        if "mail-agent" in self.agent_dependencies and email_relationships:
            for rel in email_relationships:
                email = rel["related_entity_id"]
                try:
                    mail_data = await self.query_agent(
                        agent_id="mail-agent",
                        capability="messages.search",
                        parameters={"from": email, "limit": 5},
                        timeout=2.0
                    )
                    if mail_data:
                        enrichment_results["enrichments"].append({
                            "source": "mail",
                            "type": "email_interaction",
                            "data": mail_data,
                            "confidence": 0.9
                        })
                except Exception as e:
                    print(f"Mail enrichment error: {e}")
        
        # Query calendar agent for meeting interactions
        try:
            calendar_data = await self.query_agent(
                agent_id="calendar-agent",
                capability="calendar.read",
                parameters={"attendee_search": contact_id, "limit": 5},
                timeout=2.0
            )
            if calendar_data:
                enrichment_results["enrichments"].append({
                    "source": "calendar",
                    "type": "meeting_attendance",
                    "data": calendar_data,
                    "confidence": 0.8
                })
        except Exception as e:
            print(f"Calendar enrichment error: {e}")
        
        return enrichment_results
    
    async def start(self):
        """Start the intelligent contacts agent."""
        await super().start()
        
        # Set registry client for cross-agent communication
        self.set_registry_client(self.registry_client)
        
        try:
            # Register with agent registry
            manifest = self.generate_manifest()
            manifest["type"] = "intelligent_service"  # Mark as intelligent
            registration_data = {
                "manifest": manifest,
                "health_endpoint": "http://localhost:8003"
            }
            await self.registry_client.register_agent(registration_data)
            print("[intelligent-contacts-agent] Successfully registered with registry")
        except Exception as e:
            print(f"[intelligent-contacts-agent] Warning: Could not register with registry: {e}")
        
        print("[intelligent-contacts-agent] Started successfully with enhanced capabilities")
        return True
    
    async def stop(self):
        """Stop the intelligent contacts agent."""
        await super().stop()
        print("[intelligent-contacts-agent] Stopped successfully")
        return True


class EnhancedResolveContactsHandler(ResolveContactsHandler):
    """Enhanced contact resolution with natural language processing."""
    
    def __init__(self, agent: IntelligentContactsAgent):
        super().__init__(agent)
        self.intelligent_agent = agent
    
    async def handle(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact resolution with intelligence enhancement."""
        # Check if this is a natural language query
        if "query" in parameters and isinstance(parameters["query"], str):
            # Use LLM interpretation for natural language
            return await self._handle_natural_language_resolution(parameters)
        else:
            # Use standard resolution for structured queries
            return await super().handle(parameters)
    
    async def _handle_natural_language_resolution(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle natural language contact resolution."""
        query = parameters["query"]
        
        # First check semantic cache for similar queries
        similar_matches = await self.intelligent_agent.find_similar_contacts(query, threshold=0.85)
        if similar_matches:
            print(f"Found {len(similar_matches)} similar cached contact queries")
            # Return best match if confidence is high
            best_match = max(similar_matches, key=lambda x: x["similarity_score"])
            if best_match["similarity_score"] > 0.9:
                return best_match["result_data"]
        
        # Get enriched context from cross-platform data
        platforms = parameters.get("platforms", ["contacts", "mail", "imessage", "calendar"])
        enriched_context = parameters.get("enriched_context", {})
        
        # Use original handler but with enhanced context
        enhanced_params = {
            "identifier": query,
            "fuzzy_match": True,
            "context": enriched_context
        }
        
        result = await super().handle(enhanced_params)
        
        # Add confidence scoring based on match quality
        if result.get("contacts"):
            for contact in result["contacts"]:
                # Calculate confidence based on match strength
                confidence = self._calculate_contact_confidence(query, contact)
                contact["confidence"] = confidence
        
        return result
    
    def _calculate_contact_confidence(self, query: str, contact: Dict) -> float:
        """Calculate confidence score for contact match."""
        confidence = 0.5  # Base confidence
        
        name = contact.get("name", "").lower()
        query_lower = query.lower()
        
        # Exact name match
        if name == query_lower:
            confidence = 1.0
        # Partial name match
        elif query_lower in name or name in query_lower:
            confidence = 0.8
        # Email domain match
        elif any(query_lower in email.lower() for email in contact.get("emails", [])):
            confidence = 0.9
        # Phone number match
        elif any(query_lower in phone for phone in contact.get("phones", [])):
            confidence = 0.95
        
        # Boost confidence if multiple platforms have this contact
        platform_count = len(contact.get("platforms", []))
        if platform_count > 1:
            confidence = min(1.0, confidence + (platform_count - 1) * 0.1)
        
        return round(confidence, 2)


class EnhancedEnrichContactsHandler(EnrichContactsHandler):
    """Enhanced contact enrichment with cross-platform data."""
    
    def __init__(self, agent: IntelligentContactsAgent, message_analyzer, memory_client):
        super().__init__(agent, message_analyzer, memory_client)
        self.intelligent_agent = agent
    
    async def handle(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact enrichment with cross-platform intelligence."""
        # Get base enrichment
        result = await super().handle(parameters)
        
        # Add cross-platform enrichment
        contact_id = parameters.get("contact_id")
        if contact_id:
            cross_platform_data = await self.intelligent_agent.enrich_contact_cross_platform(contact_id)
            
            # Merge cross-platform enrichments
            if "enrichments" in result:
                result["enrichments"].extend(cross_platform_data.get("enrichments", []))
            else:
                result["enrichments"] = cross_platform_data.get("enrichments", [])
            
            # Update enrichment count
            result["enrichment_count"] = len(result.get("enrichments", []))
        
        return result


class EnhancedMergeContactsHandler(MergeContactsHandler):
    """Enhanced contact merging with relationship preservation."""
    
    def __init__(self, agent: IntelligentContactsAgent):
        super().__init__(agent)
        self.intelligent_agent = agent
    
    async def handle(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle contact merging with relationship cache updates."""
        # Perform standard merge
        result = await super().handle(parameters)
        
        # Update relationship cache for merged contact
        if result.get("merged_contact_id"):
            merged_id = result["merged_contact_id"]
            duplicate_ids = parameters.get("duplicate_contact_ids", [])
            
            # Transfer relationships from duplicates to merged contact
            for duplicate_id in duplicate_ids:
                await self._transfer_contact_relationships(duplicate_id, merged_id)
        
        return result
    
    async def _transfer_contact_relationships(self, from_contact_id: str, to_contact_id: str):
        """Transfer cached relationships from duplicate to merged contact."""
        # Get all relationships for the duplicate contact
        email_rels = await self.intelligent_agent.get_entity_relationships(
            entity_type="contact",
            entity_id=from_contact_id,
            related_entity_type="email"
        )
        
        phone_rels = await self.intelligent_agent.get_entity_relationships(
            entity_type="contact", 
            entity_id=from_contact_id,
            related_entity_type="phone"
        )
        
        # Transfer email relationships
        for rel in email_rels:
            await self.intelligent_agent.cache_entity_relationship(
                entity_type="contact",
                entity_id=to_contact_id,
                related_entity_type="email",
                related_entity_id=rel["related_entity_id"],
                relationship_data=rel["relationship_data"]
            )
        
        # Transfer phone relationships
        for rel in phone_rels:
            await self.intelligent_agent.cache_entity_relationship(
                entity_type="contact",
                entity_id=to_contact_id,
                related_entity_type="phone", 
                related_entity_id=rel["related_entity_id"],
                relationship_data=rel["relationship_data"]
            )