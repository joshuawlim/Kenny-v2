import logging
import asyncio
from typing import Dict, Any, List, Optional
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class IntentClassifier:
    """LLM-based intent classification for user requests"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        try:
            self.llm = ChatOllama(
                model=model_name,
                temperature=0.1,
                base_url="http://localhost:11434"
            )
            self.llm_available = True
        except Exception as e:
            logger.warning(f"Ollama not available, using fallback classification: {e}")
            self.llm = None
            self.llm_available = False
        self.agent_capabilities = {}
        
    async def load_agent_capabilities(self, agent_client):
        """Load available agent capabilities for routing"""
        try:
            agents = await agent_client.get_available_agents()
            for agent in agents:
                agent_id = agent.get("agent_id")
                if agent_id:
                    capabilities = await agent_client.get_agent_capabilities(agent_id)
                    self.agent_capabilities[agent_id] = capabilities
        except Exception as e:
            logger.warning(f"Failed to load agent capabilities: {e}")
            # Fallback to known capabilities with correct agent IDs
            self.agent_capabilities = {
                "mail-agent": [
                    {"verb": "messages.search", "description": "Search mail messages"},
                    {"verb": "messages.read", "description": "Read mail messages"},
                    {"verb": "messages.propose_reply", "description": "Generate reply proposals"}
                ],
                "contacts-agent": [
                    {"verb": "contacts.resolve", "description": "Find and disambiguate contacts"},
                    {"verb": "contacts.enrich", "description": "Add contact information"},
                    {"verb": "contacts.merge", "description": "Merge duplicate contacts"}
                ],
                "memory-agent": [
                    {"verb": "memory.retrieve", "description": "Search stored memories"},
                    {"verb": "memory.store", "description": "Store new memories"},
                    {"verb": "memory.embed", "description": "Generate embeddings"}
                ]
            }
    
    async def classify_intent(self, user_input: str) -> Dict[str, Any]:
        """Classify user intent and determine routing strategy"""
        # Use fallback if LLM is not available
        if not self.llm_available or self.llm is None:
            logger.info("Using fallback classification (LLM not available)")
            return self._fallback_classification(user_input)
        
        try:
            # Create capability description for the LLM
            capabilities_text = self._format_capabilities_for_llm()
            
            system_prompt = f"""You are an intelligent request router for a multi-agent personal assistant system.

Available agents and their capabilities:
{capabilities_text}

Your task is to analyze user requests and determine:
1. Primary intent category
2. Required agent(s) and capabilities
3. Execution strategy (single-agent, multi-agent, or sequential)
4. Priority and urgency

Respond in JSON format:
{{
    "primary_intent": "mail_operation|contacts_operation|memory_operation|calendar_operation|general_query",
    "confidence": 0.0-1.0,
    "required_agents": [
        {{
            "agent_id": "agent_name",
            "capabilities": ["capability1", "capability2"],
            "priority": 1
        }}
    ],
    "execution_strategy": "single_agent|multi_agent|sequential",
    "reasoning": "Brief explanation of the routing decision"
}}"""

            human_prompt = f"User request: {user_input}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse the JSON response
            import json
            try:
                intent_data = json.loads(response.content)
                return intent_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON: {response.content}")
                return self._fallback_classification(user_input)
                
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return self._fallback_classification(user_input)
    
    def _format_capabilities_for_llm(self) -> str:
        """Format agent capabilities for LLM prompt"""
        text = ""
        for agent_id, capabilities in self.agent_capabilities.items():
            text += f"\n{agent_id}:\n"
            for cap in capabilities:
                verb = cap.get("verb", "unknown")
                desc = cap.get("description", "No description")
                text += f"  - {verb}: {desc}\n"
        return text
    
    def _fallback_classification(self, user_input: str) -> Dict[str, Any]:
        """Fallback classification using keyword matching"""
        user_input_lower = user_input.lower()
        
        if any(word in user_input_lower for word in ["mail", "email", "message", "inbox", "send"]):
            return {
                "primary_intent": "mail_operation",
                "confidence": 0.7,
                "required_agents": [
                    {
                        "agent_id": "mail-agent",
                        "capabilities": ["messages.search"],
                        "priority": 1
                    }
                ],
                "execution_strategy": "single_agent",
                "reasoning": "Keyword-based fallback classification for mail operations"
            }
        elif any(word in user_input_lower for word in ["contact", "person", "phone", "address"]):
            return {
                "primary_intent": "contacts_operation", 
                "confidence": 0.7,
                "required_agents": [
                    {
                        "agent_id": "contacts-agent",
                        "capabilities": ["contacts.resolve"],
                        "priority": 1
                    }
                ],
                "execution_strategy": "single_agent",
                "reasoning": "Keyword-based fallback classification for contact operations"
            }
        elif any(word in user_input_lower for word in ["remember", "recall", "memory", "store", "find"]):
            return {
                "primary_intent": "memory_operation",
                "confidence": 0.7,
                "required_agents": [
                    {
                        "agent_id": "memory-agent", 
                        "capabilities": ["memory.retrieve"],
                        "priority": 1
                    }
                ],
                "execution_strategy": "single_agent",
                "reasoning": "Keyword-based fallback classification for memory operations"
            }
        elif any(word in user_input_lower for word in ["calendar", "schedule", "meeting", "event", "appointment"]):
            return {
                "primary_intent": "calendar_operation",
                "confidence": 0.7,
                "required_agents": [],
                "execution_strategy": "single_agent", 
                "reasoning": "Keyword-based fallback classification for calendar operations (no agent available)"
            }
        else:
            return {
                "primary_intent": "general_query",
                "confidence": 0.5,
                "required_agents": [],
                "execution_strategy": "single_agent",
                "reasoning": "Fallback classification for general queries"
            }

class RouterNode:
    """Enhanced router node with intelligent intent classification"""
    
    def __init__(self):
        self.classifier = IntentClassifier()
        self._capabilities_loaded = False
    
    async def route_request(self, state: Dict[str, Any], agent_client) -> Dict[str, Any]:
        """Route user input with intelligent intent classification"""
        logger.info(f"Routing request: {state['user_input']}")
        state['current_node'] = "router"
        state['execution_path'].append("router")
        
        try:
            # Load agent capabilities if not already loaded
            if not self._capabilities_loaded:
                await self.classifier.load_agent_capabilities(agent_client)
                self._capabilities_loaded = True
            
            # Classify intent using LLM
            intent_result = await self.classifier.classify_intent(state['user_input'])
            
            # Store routing information in context
            state['context']['intent'] = intent_result['primary_intent']
            state['context']['confidence'] = intent_result['confidence'] 
            state['context']['required_agents'] = intent_result['required_agents']
            state['context']['execution_strategy'] = intent_result['execution_strategy']
            state['context']['routing_reasoning'] = intent_result['reasoning']
            
            logger.info(f"Intent classified as: {intent_result['primary_intent']} "
                       f"(confidence: {intent_result['confidence']:.2f})")
            
        except Exception as e:
            logger.error(f"Error in routing: {e}")
            state['errors'].append(f"Routing error: {str(e)}")
            # Use fallback routing
            state['context']['intent'] = "general_query"
            state['context']['confidence'] = 0.3
            state['context']['required_agents'] = []
            state['context']['execution_strategy'] = "single_agent"
        
        return state