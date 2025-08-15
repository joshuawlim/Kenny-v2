import asyncio
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx
from datetime import datetime

from .schemas import AgentInfo, CapabilityInfo, SystemHealth

logger = logging.getLogger(__name__)

class KennyGateway:
    """Main gateway class for Kenny v2 multi-agent system"""
    
    def __init__(self):
        self.agent_registry_url = "http://localhost:8001"
        self.coordinator_url = "http://localhost:8002"
        self.http_client: Optional[httpx.AsyncClient] = None
        
        # Cache for performance
        self._agents_cache: Dict[str, AgentInfo] = {}
        self._capabilities_cache: List[CapabilityInfo] = []
        self._cache_timestamp = 0
        self.cache_ttl = 30  # 30 seconds
    
    async def initialize(self):
        """Initialize gateway components"""
        self.http_client = httpx.AsyncClient(timeout=10.0)
        
        # Try to connect to agent registry
        registry_available = await self._check_registry_connection()
        
        if registry_available:
            await self._refresh_cache()
            logger.info("Gateway initialized successfully with full agent registry")
        else:
            logger.info("Agent registry not available, initializing in standalone mode")
            self._initialize_mock_data()
            logger.info("Gateway initialized successfully with mock data")
    
    async def _check_registry_connection(self) -> bool:
        """Check if agent registry is available"""
        try:
            response = await self.http_client.get(f"{self.agent_registry_url}/health", timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"Registry connection check failed: {e}")
            return False
    
    async def cleanup(self):
        """Cleanup gateway resources"""
        if self.http_client:
            await self.http_client.aclose()
        logger.info("Gateway cleanup completed")
    
    async def get_system_health(self) -> SystemHealth:
        """Get aggregated system health from Agent Registry"""
        try:
            if not self.http_client:
                raise RuntimeError("Gateway not initialized")
            
            response = await self.http_client.get(f"{self.agent_registry_url}/health")
            
            if response.status_code == 200:
                health_data = response.json()
                
                # Get enhanced health if available
                try:
                    enhanced_response = await self.http_client.get(f"{self.agent_registry_url}/health/dashboard")
                    if enhanced_response.status_code == 200:
                        enhanced_data = enhanced_response.json()
                        system_overview = enhanced_data.get("system_overview", health_data)
                        
                        return SystemHealth(
                            status=system_overview.get("status", "unknown"),
                            total_agents=system_overview.get("total_agents", 0),
                            healthy_agents=system_overview.get("healthy_agents", 0),
                            unhealthy_agents=system_overview.get("unhealthy_agents", 0),
                            total_capabilities=system_overview.get("total_capabilities", 0),
                            timestamp=system_overview.get("timestamp", datetime.now().isoformat())
                        )
                except Exception as e:
                    logger.debug(f"Enhanced health not available: {e}")
                
                # Fallback to basic health with local agent counts
                total_agents = len(self._agents_cache)
                healthy_agents = sum(1 for agent in self._agents_cache.values() if agent.is_healthy)
                unhealthy_agents = total_agents - healthy_agents
                total_capabilities = len(self._capabilities_cache)
                
                return SystemHealth(
                    status=health_data.get("status", "unknown"),
                    total_agents=total_agents,
                    healthy_agents=healthy_agents,
                    unhealthy_agents=unhealthy_agents,
                    total_capabilities=total_capabilities,
                    timestamp=health_data.get("timestamp", datetime.now().isoformat())
                )
            else:
                raise Exception(f"Registry health check failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            # Use local cache even in error case
            total_agents = len(self._agents_cache)
            healthy_agents = sum(1 for agent in self._agents_cache.values() if agent.is_healthy)
            unhealthy_agents = total_agents - healthy_agents
            total_capabilities = len(self._capabilities_cache)
            
            return SystemHealth(
                status="error",
                total_agents=total_agents,
                healthy_agents=healthy_agents,
                unhealthy_agents=unhealthy_agents,
                total_capabilities=total_capabilities,
                timestamp=datetime.now().isoformat()
            )
    
    async def get_agents(self) -> List[AgentInfo]:
        """Get all registered agents"""
        await self._refresh_cache_if_needed()
        return list(self._agents_cache.values())
    
    async def get_all_capabilities(self) -> List[CapabilityInfo]:
        """Get all available capabilities across agents"""
        await self._refresh_cache_if_needed()
        return self._capabilities_cache.copy()
    
    async def get_agent_capabilities(self, agent_id: str) -> List[str]:
        """Get capabilities for a specific agent"""
        await self._refresh_cache_if_needed()
        
        agent = self._agents_cache.get(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        return agent.capabilities
    
    async def call_agent_direct(self, agent_id: str, capability: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Call agent capability directly (bypass coordinator)"""
        try:
            if not self.http_client:
                raise RuntimeError("Gateway not initialized")
            
            # Get agent info from cache
            await self._refresh_cache_if_needed()
            agent = self._agents_cache.get(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
            
            if not agent.is_healthy:
                raise ValueError(f"Agent {agent_id} is not healthy")
            
            # In standalone mode, return mock responses
            if not await self._is_agent_registry_available():
                return self._mock_agent_response(agent_id, capability, parameters)
            
            # Determine agent URL based on known ports
            agent_ports = {
                "mail-agent": 8000,
                "contacts-agent": 8001, 
                "memory-agent": 8002,
                "whatsapp-agent": 8005,
                "imessage-agent": 8006,
                "calendar-agent": 8007
            }
            
            port = agent_ports.get(agent_id, 8000)
            agent_url = f"http://localhost:{port}"
            
            # Make capability call
            response = await self.http_client.post(
                f"{agent_url}/capabilities/{capability}",
                json=parameters,
                timeout=5.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"Agent call failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Direct agent call failed: {e}")
            raise
    
    async def _is_agent_registry_available(self) -> bool:
        """Check if agent registry is available"""
        try:
            response = await self.http_client.get(f"{self.agent_registry_url}/health", timeout=2.0)
            return response.status_code == 200
        except:
            return False
    
    def _mock_agent_response(self, agent_id: str, capability: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock response for testing"""
        mock_responses = {
            ("mail-agent", "messages.search"): {
                "status": "success",
                "results": [
                    {"id": "msg_1", "subject": "Meeting tomorrow", "from": "alice@example.com"},
                    {"id": "msg_2", "subject": "Project update", "from": "bob@example.com"}
                ],
                "total_count": 2
            },
            ("contacts-agent", "contacts.resolve"): {
                "status": "success", 
                "contact": {
                    "id": "contact_1",
                    "name": "John Smith",
                    "email": "john@example.com",
                    "phone": "+1234567890"
                }
            },
            ("calendar-agent", "calendar.read"): {
                "status": "success",
                "events": [
                    {"id": "event_1", "title": "Team Meeting", "start": "2025-01-15T10:00:00Z"},
                    {"id": "event_2", "title": "Lunch with Sarah", "start": "2025-01-15T12:00:00Z"}
                ]
            },
            ("memory-agent", "memory.retrieve"): {
                "status": "success",
                "results": [
                    {"content": "User likes coffee", "source": "notes", "confidence": 0.9},
                    {"content": "Prefers morning meetings", "source": "preferences", "confidence": 0.8}
                ]
            },
            ("imessage-agent", "messages.read"): {
                "status": "success",
                "messages": [
                    {"id": "imsg_1", "content": "Hey, how are you?", "from": "Alice", "timestamp": "2025-01-15T10:00:00Z"},
                    {"id": "imsg_2", "content": "Let's meet tomorrow", "from": "Bob", "timestamp": "2025-01-15T11:00:00Z"}
                ]
            },
            ("imessage-agent", "messages.search"): {
                "status": "success",
                "results": [
                    {"id": "imsg_3", "content": "Meeting at 2pm", "from": "Sarah", "relevance": 0.95},
                    {"id": "imsg_4", "content": "Don't forget the presentation", "from": "John", "relevance": 0.87}
                ]
            },
            ("whatsapp-agent", "chats.read"): {
                "status": "success", 
                "messages": [
                    {"id": "wa_1", "content": "Good morning!", "from": "+1234567890", "timestamp": "2025-01-15T08:00:00Z"},
                    {"id": "wa_2", "content": "See you later", "from": "Mom", "timestamp": "2025-01-15T09:00:00Z"}
                ]
            }
        }
        
        mock_key = (agent_id, capability)
        if mock_key in mock_responses:
            response = mock_responses[mock_key].copy()
            response["_mock"] = True
            response["_parameters"] = parameters
            return response
        
        # Default mock response
        return {
            "status": "success",
            "message": f"Mock response for {agent_id}.{capability}",
            "parameters": parameters,
            "_mock": True
        }
    
    async def orchestrate_request(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrate request through coordinator"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            if not self.http_client:
                raise RuntimeError("Gateway not initialized")
            
            # Check if coordinator is available
            if not await self._is_coordinator_available():
                logger.warning("Coordinator unavailable, using mock response")
                return self._mock_coordinator_response(query, context)
            
            request_data = {
                "user_input": query,
                "context": context
            }
            
            response = await self.http_client.post(
                f"{self.coordinator_url}/coordinator/process",
                json=request_data,
                timeout=30.0
            )
            
            if response.status_code == 200:
                result = response.json()
                duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
                
                # Extract coordinator response properly
                coordinator_result = result.get("result", {})
                
                # Extract the actual conversational message from coordinator results
                actual_message = self._extract_conversational_message(coordinator_result)
                
                return {
                    "request_id": f"coord_{int(start_time * 1000)}",
                    "result": {
                        "message": actual_message,
                        "intent": coordinator_result.get("intent", "unknown"),
                        "plan": coordinator_result.get("plan", []),
                        "execution_path": coordinator_result.get("execution_path", []),
                        "status": result.get("status", "unknown")
                    },
                    "execution_path": coordinator_result.get("execution_path", []),
                    "duration_ms": duration_ms
                }
            else:
                raise Exception(f"Coordinator call failed: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"Coordinator orchestration failed: {e}")
            # Return error response instead of raising
            duration_ms = int((asyncio.get_event_loop().time() - start_time) * 1000)
            return {
                "request_id": f"error_{int(start_time * 1000)}",
                "result": {
                    "intent": "error",
                    "plan": [],
                    "execution_path": [],
                    "results": {},
                    "errors": [str(e)],
                    "status": "error"
                },
                "execution_path": [],
                "duration_ms": duration_ms
            }
    
    async def _is_coordinator_available(self) -> bool:
        """Check if coordinator is available"""
        try:
            response = await self.http_client.get(f"{self.coordinator_url}/health", timeout=2.0)
            return response.status_code == 200
        except:
            return False
    
    def _mock_coordinator_response(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock coordinator response"""
        return {
            "request_id": f"mock_coord_{asyncio.get_event_loop().time()}",
            "result": {
                "intent": "multi_agent_workflow",
                "plan": ["analyze_query", "route_to_agents", "synthesize_response"],
                "execution_path": ["router", "planner", "executor", "reviewer"],
                "results": {
                    "calendar-agent": {
                        "calendar.propose_event": {
                            "status": "success",
                            "event_proposal": {
                                "title": "Meeting with Sarah",
                                "suggested_times": ["2025-01-16T14:00:00Z", "2025-01-16T15:00:00Z"],
                                "duration": "1 hour"
                            }
                        }
                    }
                },
                "errors": []
            },
            "execution_path": ["router", "planner", "executor", "reviewer"],
            "duration_ms": 150,
            "_mock": True
        }
    
    async def orchestrate_request_stream(self, query: str, context: Dict[str, Any]) -> AsyncGenerator[Dict[str, Any], None]:
        """Orchestrate request with streaming results"""
        try:
            if not self.http_client:
                raise RuntimeError("Gateway not initialized")
            
            # Check if coordinator is available
            if not await self._is_coordinator_available():
                logger.warning("Coordinator unavailable for streaming")
                yield {
                    "type": "error",
                    "message": "Coordinator service unavailable",
                    "timestamp": asyncio.get_event_loop().time()
                }
                return
            
            request_data = {
                "user_input": query,
                "context": context
            }
            
            async with self.http_client.stream(
                "POST",
                f"{self.coordinator_url}/coordinator/process-stream",
                json=request_data,
                timeout=30.0
            ) as response:
                
                if response.status_code != 200:
                    yield {
                        "type": "error",
                        "message": f"Coordinator stream failed: {response.status_code}",
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    return
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            import json
                            data = json.loads(line[6:])  # Remove "data: " prefix
                            yield data
                        except json.JSONDecodeError as e:
                            logger.debug(f"Failed to parse streaming data: {line}, error: {e}")
                            continue
                        
        except Exception as e:
            logger.error(f"Coordinator streaming failed: {e}")
            yield {
                "type": "error",
                "message": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def _refresh_cache_if_needed(self):
        """Refresh cache if TTL expired"""
        current_time = asyncio.get_event_loop().time()
        if current_time - self._cache_timestamp > self.cache_ttl:
            try:
                await self._refresh_cache()
            except Exception as e:
                logger.debug(f"Cache refresh failed, keeping existing cache: {e}")
                # Don't re-initialize if we already have mock data
                if not self._agents_cache:
                    self._initialize_mock_data()
    
    async def _refresh_cache(self):
        """Refresh agents and capabilities cache"""
        try:
            if not self.http_client:
                self.http_client = httpx.AsyncClient(timeout=10.0)
            
            # Fetch agents
            agents_response = await self.http_client.get(f"{self.agent_registry_url}/agents")
            
            if agents_response.status_code == 200:
                agents_data = agents_response.json()
                
                self._agents_cache = {}
                # Handle both list format (current) and dict format (for compatibility)
                agents_list = agents_data if isinstance(agents_data, list) else agents_data.get("agents", [])
                for agent_data in agents_list:
                    agent = AgentInfo(
                        agent_id=agent_data.get("agent_id", ""),
                        display_name=agent_data.get("display_name"),
                        status=agent_data.get("status", "unknown"),
                        is_healthy=agent_data.get("is_healthy", False),
                        capabilities=[cap.get("verb", "") for cap in agent_data.get("capabilities", [])],
                        last_seen=agent_data.get("last_seen", "")
                    )
                    self._agents_cache[agent.agent_id] = agent
            
            # Fetch capabilities
            capabilities_response = await self.http_client.get(f"{self.agent_registry_url}/capabilities")
            
            if capabilities_response.status_code == 200:
                capabilities_data = capabilities_response.json()
                
                self._capabilities_cache = []
                # Handle dict format (current) where capabilities are grouped by verb
                if isinstance(capabilities_data, dict):
                    for verb, capability_list in capabilities_data.items():
                        for cap_data in capability_list:
                            capability = CapabilityInfo(
                                verb=cap_data.get("verb", ""),
                                agent_id=cap_data.get("agent_id", ""),
                                agent_name=cap_data.get("agent_name", ""),
                                description=cap_data.get("description"),
                                safety_annotations=cap_data.get("safety_annotations", [])
                            )
                            self._capabilities_cache.append(capability)
                else:
                    # Handle list format (for compatibility)
                    for cap_data in capabilities_data.get("capabilities", []):
                        capability = CapabilityInfo(
                            verb=cap_data.get("verb", ""),
                            agent_id=cap_data.get("agent_id", ""),
                            agent_name=cap_data.get("agent_name", ""),
                            description=cap_data.get("description"),
                            safety_annotations=cap_data.get("safety_annotations", [])
                        )
                        self._capabilities_cache.append(capability)
            
            self._cache_timestamp = asyncio.get_event_loop().time()
            logger.debug("Gateway cache refreshed successfully")
            
        except Exception as e:
            logger.error(f"Failed to refresh cache: {e}")
            # Keep existing cache if refresh fails
    
    def _extract_conversational_message(self, coordinator_result: Dict[str, Any]) -> str:
        """Extract the actual conversational message from coordinator results"""
        try:
            # Try to get the message from execution results
            results = coordinator_result.get("results", {})
            execution_results = results.get("execution_results", [])
            
            raw_message = ""
            if execution_results and len(execution_results) > 0:
                first_result = execution_results[0]
                if isinstance(first_result, dict):
                    result_data = first_result.get("result", {})
                    if isinstance(result_data, dict) and "message" in result_data:
                        raw_message = result_data["message"]
            
            # Fallback: try to get from general_processing
            if not raw_message:
                general_processing = results.get("general_processing", {})
                if isinstance(general_processing, dict):
                    result_data = general_processing.get("result", {})
                    if isinstance(result_data, dict) and "message" in result_data:
                        raw_message = result_data["message"]
            
            # If we found a raw message, enhance it with Kenny's personality
            if raw_message:
                return self._add_kenny_personality(raw_message)
            
            # Last fallback: return a Kenny-style response
            return "Hey there! I got your message but I'm having a bit of trouble processing it right now. Could you try rephrasing that for me?"
            
        except Exception as e:
            logger.warning(f"Failed to extract conversational message: {e}")
            return "Oops! Something went sideways on my end. Mind giving that another shot?"
    
    def _add_kenny_personality(self, raw_message: str) -> str:
        """Add Kenny's personality and character to raw responses"""
        try:
            # Kenny's personality traits: helpful, casual, tech-savvy, efficient, friendly
            
            # Handle different types of generic responses
            if "Processed:" in raw_message:
                # Transform generic "Processed: X" responses
                user_input = raw_message.replace("Processed: ", "").strip()
                
                if any(greeting in user_input.lower() for greeting in ["hello", "hi", "hey"]):
                    return f"Hey there! 👋 Good to see you. I'm Kenny, your personal assistant. What can I help you with today?"
                
                elif "kenny" in user_input.lower():
                    return f"That's me! I'm Kenny, your multi-agent personal assistant. I can help you with emails, contacts, calendar, messages, and more. What would you like to do?"
                
                elif any(question in user_input.lower() for question in ["help", "what can you do", "capabilities"]):
                    return "I'm Kenny! I can help you with loads of things - searching emails, finding contacts, checking your calendar, reading messages, and even coordinating complex tasks across multiple services. Just tell me what you need!"
                
                else:
                    return f"Got it! I processed your request: '{user_input}'. Is there anything specific you'd like me to help you with?"
            
            # Handle other response types
            elif "success" in raw_message.lower():
                return f"✅ All done! {raw_message.replace('Success', 'Successfully handled that').replace('success', 'took care of that')}"
            
            elif "error" in raw_message.lower() or "failed" in raw_message.lower():
                return f"Hmm, ran into a snag there. {raw_message} Want me to try a different approach?"
            
            elif raw_message.strip() == "" or raw_message.lower() == "ok":
                return "All set! Anything else I can help you with?"
            
            # For other responses, just add a friendly Kenny touch
            return f"{raw_message} Let me know if you need anything else!"
            
        except Exception as e:
            logger.warning(f"Failed to add Kenny personality: {e}")
            # Fallback to original message if personality enhancement fails
            return raw_message
    
    def _initialize_mock_data(self):
        """Initialize mock data for standalone testing"""
        self._agents_cache = {
            "mail-agent": AgentInfo(
                agent_id="mail-agent",
                display_name="Mail Agent",
                status="healthy",
                is_healthy=True,
                capabilities=["messages.search", "messages.read", "messages.propose_reply"],
                last_seen="2025-01-01T00:00:00Z"
            ),
            "contacts-agent": AgentInfo(
                agent_id="contacts-agent", 
                display_name="Contacts Agent",
                status="healthy",
                is_healthy=True,
                capabilities=["contacts.resolve", "contacts.enrich", "contacts.merge"],
                last_seen="2025-01-01T00:00:00Z"
            ),
            "calendar-agent": AgentInfo(
                agent_id="calendar-agent",
                display_name="Calendar Agent", 
                status="healthy",
                is_healthy=True,
                capabilities=["calendar.read", "calendar.propose_event", "calendar.write_event"],
                last_seen="2025-01-01T00:00:00Z"
            ),
            "memory-agent": AgentInfo(
                agent_id="memory-agent",
                display_name="Memory Agent",
                status="healthy", 
                is_healthy=True,
                capabilities=["memory.store", "memory.retrieve", "memory.embed"],
                last_seen="2025-01-01T00:00:00Z"
            ),
            "imessage-agent": AgentInfo(
                agent_id="imessage-agent",
                display_name="iMessage Agent",
                status="healthy",
                is_healthy=True,
                capabilities=["messages.read", "messages.search", "messages.propose_reply"],
                last_seen="2025-01-01T00:00:00Z"
            ),
            "whatsapp-agent": AgentInfo(
                agent_id="whatsapp-agent",
                display_name="WhatsApp Agent", 
                status="healthy",
                is_healthy=True,
                capabilities=["chats.read", "chats.search", "chats.propose_reply"],
                last_seen="2025-01-01T00:00:00Z"
            )
        }
        
        self._capabilities_cache = [
            CapabilityInfo(verb="messages.search", agent_id="mail-agent", agent_name="Mail Agent", description="Search emails"),
            CapabilityInfo(verb="messages.read", agent_id="mail-agent", agent_name="Mail Agent", description="Read email content"),
            CapabilityInfo(verb="contacts.resolve", agent_id="contacts-agent", agent_name="Contacts Agent", description="Find contacts"),
            CapabilityInfo(verb="calendar.read", agent_id="calendar-agent", agent_name="Calendar Agent", description="Read calendar events"),
            CapabilityInfo(verb="memory.store", agent_id="memory-agent", agent_name="Memory Agent", description="Store information"),
            CapabilityInfo(verb="memory.retrieve", agent_id="memory-agent", agent_name="Memory Agent", description="Retrieve information"),
            CapabilityInfo(verb="messages.read", agent_id="imessage-agent", agent_name="iMessage Agent", description="Read iMessages"),
            CapabilityInfo(verb="messages.search", agent_id="imessage-agent", agent_name="iMessage Agent", description="Search iMessages"),
            CapabilityInfo(verb="chats.read", agent_id="whatsapp-agent", agent_name="WhatsApp Agent", description="Read WhatsApp chats"),
            CapabilityInfo(verb="chats.search", agent_id="whatsapp-agent", agent_name="WhatsApp Agent", description="Search WhatsApp chats")
        ]
        
        self._cache_timestamp = asyncio.get_event_loop().time()
        logger.info("Initialized mock agent data for standalone testing")