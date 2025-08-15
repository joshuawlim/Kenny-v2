import re
import asyncio
import logging
from typing import Dict, List, Pattern
import httpx

from .schemas import RoutingDecision, RoutingType

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Intent classification for routing decisions"""
    
    def __init__(self):
        # Direct agent patterns (fast path)
        self.direct_patterns: Dict[Pattern, Dict[str, str]] = {
            re.compile(r"search (mail|email)", re.IGNORECASE): {
                "agent_id": "mail-agent",
                "capability": "messages.search",
                "intent": "mail_search"
            },
            re.compile(r"find contact", re.IGNORECASE): {
                "agent_id": "contacts-agent", 
                "capability": "contacts.resolve",
                "intent": "contact_lookup"
            },
            re.compile(r"when is.*(meeting|event)", re.IGNORECASE): {
                "agent_id": "calendar-agent",
                "capability": "calendar.read",
                "intent": "calendar_query"
            },
            re.compile(r"show (my|recent) messages", re.IGNORECASE): {
                "agent_id": "imessage-agent",
                "capability": "messages.read", 
                "intent": "message_read"
            },
            re.compile(r"remember|save|store", re.IGNORECASE): {
                "agent_id": "memory-agent",
                "capability": "memory.store",
                "intent": "memory_store"
            },
            re.compile(r"what do you know about", re.IGNORECASE): {
                "agent_id": "memory-agent",
                "capability": "memory.retrieve",
                "intent": "memory_query"
            }
        }
        
        # Multi-agent triggers
        self.coordinator_triggers = [
            "and then", "also", "combine", "both", 
            "follow up", "create event", "send message",
            "schedule", "propose", "draft", "compose",
            "find and", "search and", "check and",
            "multiple", "several", "various", "across",
            "workflow", "sequence", "steps", "chain",
            "coordinate", "orchestrate", "integrate"
        ]
        
        # Ollama client for complex classification
        self.ollama_url = "http://localhost:11434"
    
    async def classify_intent(self, query: str) -> RoutingDecision:
        """Classify user intent and determine routing"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Tier 1: Fast pattern matching
            for pattern, config in self.direct_patterns.items():
                if pattern.search(query):
                    duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                    
                    return RoutingDecision(
                        route=RoutingType.DIRECT,
                        intent=config["intent"],
                        confidence=0.9,
                        agent_id=config["agent_id"],
                        capability=config["capability"],
                        parameters=self._extract_parameters(query, config["intent"]),
                        duration_ms=duration_ms
                    )
            
            # Tier 2: Multi-agent triggers
            coordinator_trigger_count = sum(1 for trigger in self.coordinator_triggers if trigger in query.lower())
            if coordinator_trigger_count > 0:
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                # Higher confidence for multiple triggers
                confidence = min(0.95, 0.7 + (coordinator_trigger_count * 0.1))
                
                return RoutingDecision(
                    route=RoutingType.COORDINATOR,
                    intent="multi_agent_workflow",
                    confidence=confidence,
                    duration_ms=duration_ms
                )
            
            # Tier 3: LLM classification for ambiguous cases
            llm_result = await self._classify_with_ollama(query)
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            if llm_result:
                return RoutingDecision(
                    route=llm_result.get("route", RoutingType.COORDINATOR),
                    intent=llm_result.get("intent", "general_query"),
                    confidence=llm_result.get("confidence", 0.5),
                    agent_id=llm_result.get("agent_id"),
                    capability=llm_result.get("capability"),
                    parameters=llm_result.get("parameters", {}),
                    duration_ms=duration_ms
                )
            
            # Default: route to coordinator
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            return RoutingDecision(
                route=RoutingType.COORDINATOR,
                intent="general_query", 
                confidence=0.3,
                duration_ms=duration_ms
            )
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            
            # Fallback to coordinator
            return RoutingDecision(
                route=RoutingType.COORDINATOR,
                intent="error_fallback",
                confidence=0.1,
                duration_ms=duration_ms
            )
    
    def _extract_parameters(self, query: str, intent: str) -> Dict[str, str]:
        """Extract parameters from query based on intent"""
        params = {}
        
        if intent == "mail_search":
            # Extract search terms
            search_pattern = re.compile(r"search (?:mail|email) (?:for |about )?(.+)", re.IGNORECASE)
            match = search_pattern.search(query)
            if match:
                params["query"] = match.group(1).strip()
        
        elif intent == "contact_lookup":
            # Extract contact name
            contact_pattern = re.compile(r"find contact (?:for |named )?(.+)", re.IGNORECASE)
            match = contact_pattern.search(query)
            if match:
                params["name"] = match.group(1).strip()
        
        elif intent == "memory_store":
            # Extract content to store
            store_pattern = re.compile(r"(?:remember|save|store) (.+)", re.IGNORECASE)
            match = store_pattern.search(query)
            if match:
                params["content"] = match.group(1).strip()
        
        elif intent == "memory_query":
            # Extract search topic
            query_pattern = re.compile(r"what do you know about (.+)", re.IGNORECASE)
            match = query_pattern.search(query)
            if match:
                params["topic"] = match.group(1).strip()
        
        return params
    
    async def _classify_with_ollama(self, query: str) -> Dict[str, str]:
        """Use Ollama for complex intent classification"""
        try:
            # Simplified classification prompt
            prompt = f"""Classify this user query for routing to the best agent:

Query: "{query}"

Available agents:
- mail-agent: Search and read emails (capabilities: messages.search, messages.read)  
- contacts-agent: Find and manage contacts (capabilities: contacts.resolve, contacts.enrich)
- calendar-agent: Calendar events and scheduling (capabilities: calendar.read, calendar.propose_event)
- imessage-agent: iMessage conversations (capabilities: messages.read, messages.search)
- memory-agent: Store and retrieve information (capabilities: memory.store, memory.retrieve) 
- whatsapp-agent: WhatsApp conversations (capabilities: chats.search, chats.read)

Return JSON with:
{{"route": "direct|coordinator", "intent": "description", "agent_id": "agent-name", "capability": "verb", "confidence": 0.0-1.0}}

If the query requires multiple agents or is complex, use route: "coordinator".
If it's a simple single-agent task, use route: "direct" with the specific agent and capability."""

            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": "llama3.2:3b",  # Use a small, fast model
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9
                        }
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    response_text = result.get("response", "")
                    
                    # Try to parse JSON from response
                    import json
                    try:
                        # Extract JSON from response
                        json_start = response_text.find("{")
                        json_end = response_text.rfind("}") + 1
                        if json_start >= 0 and json_end > json_start:
                            json_str = response_text[json_start:json_end]
                            return json.loads(json_str)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Ollama JSON response: {response_text}")
                
        except Exception as e:
            logger.warning(f"Ollama classification failed: {e}")
        
        return None