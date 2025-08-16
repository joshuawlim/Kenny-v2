"""
Intelligent Calendar Agent for Kenny v2.1

Enhanced Calendar Agent with embedded LLM capabilities for natural language
event management, schedule optimization, and intelligent meeting coordination.

Key Enhancements:
- Natural language event creation: "Schedule a meeting with Sarah next Tuesday at 2pm"
- Smart conflict detection and resolution suggestions
- Meeting context analysis and preparation recommendations
- Cross-platform participant coordination
"""

import sys
import os
import logging
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.agent_service_base import AgentServiceBase, ConfidenceResult
from kenny_agent.registry import AgentRegistryClient

from handlers.read import ReadCapabilityHandler
from handlers.propose_event import ProposeEventCapabilityHandler
from handlers.write_event import WriteEventCapabilityHandler
from tools.calendar_bridge import CalendarBridgeTool


class IntelligentCalendarAgent(AgentServiceBase):
    """
    Enhanced Calendar Agent with LLM-driven natural language processing.
    
    Transforms from basic API wrapper to intelligent service:
    - Natural language event creation and management
    - Smart scheduling with conflict resolution
    - Meeting context analysis and preparation
    - Cross-platform participant coordination
    """
    
    def __init__(self, llm_model: str = "llama3.2:3b"):
        """Initialize the Intelligent Calendar Agent."""
        super().__init__(
            agent_id="intelligent-calendar-agent",
            name="Intelligent Calendar Agent",
            description="AI-powered calendar management with natural language processing, smart scheduling, and intelligent meeting coordination",
            version="2.1.0",
            llm_model=llm_model,
            data_scopes=["calendar:events", "calendar:calendars", "calendar:participants"],
            tool_access=["macos-bridge", "approval-workflow", "ollama", llm_model],
            egress_domains=[]
        )
        
        # Setup logging
        self.logger = logging.getLogger("intelligent-calendar-agent")
        self.logger.setLevel(logging.INFO)
        
        self.logger.info(f"Initialized Intelligent Calendar Agent with LLM model: {llm_model}")
        print(f"Initialized Intelligent Calendar Agent with LLM model: {llm_model}")
        print("Initializing Intelligent Calendar Agent with LLM:", llm_model)
        
        # Initialize tools
        self._initialize_tools()
        
        # Initialize capability handlers  
        self._initialize_handlers()
        
        # Register enhanced capabilities
        print("Registering intelligent calendar capabilities...")
        self._register_enhanced_capabilities()
        
        # Register cross-platform dependencies
        print("Registering cross-platform dependencies...")
        self._register_dependencies()
        
        print("Intelligent Calendar Agent initialization complete!")
    
    def _initialize_tools(self):
        """Initialize calendar-specific tools."""
        bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        print(f"Registering Calendar bridge tool with URL: {bridge_url}")
        self.register_tool(CalendarBridgeTool(bridge_url))
    
    def _initialize_handlers(self):
        """Initialize capability handlers."""
        # Initialize read handler
        self.read_handler = ReadCapabilityHandler()
        self.read_handler._agent = self
        
        # Initialize propose event handler
        self.propose_event_handler = ProposeEventCapabilityHandler()
        self.propose_event_handler._agent = self
        
        # Initialize write event handler
        self.write_event_handler = WriteEventCapabilityHandler()
        self.write_event_handler._agent = self
    
    def _register_enhanced_capabilities(self):
        """Register enhanced intelligent capabilities."""
        # Register traditional capabilities with enhanced intelligence
        self.register_capability(self.read_handler)
        self.register_capability(self.propose_event_handler)
        self.register_capability(self.write_event_handler)
        
        # Create wrapper handler for enhanced capabilities
        class EnhancedCapabilityHandler:
            def __init__(self, agent, capability_name):
                self.agent = agent
                self.capability_name = capability_name
            
            async def execute(self, parameters):
                return await self.agent._handle_enhanced_capability(self.capability_name, parameters)
        
        # Enhanced capabilities for natural language processing
        enhanced_capabilities = [
            "calendar.smart_schedule",
            "calendar.conflict_resolve", 
            "calendar.meeting_prep",
            "calendar.availability_optimize",
            "calendar.context_analyze",
            "calendar.read_with_contacts"
        ]
        
        for capability in enhanced_capabilities:
            handler = EnhancedCapabilityHandler(self, capability)
            self.capabilities[capability] = handler
        
        print(f"Registered capabilities: {list(self.capabilities.keys())}")
    
    def _register_dependencies(self):
        """Register dependencies on other agents for cross-platform intelligence."""
        # Register dependency on contacts agent
        self.register_agent_dependency(
            "contacts-agent",
            ["contacts.resolve", "contacts.enrich"],
            "Contact resolution and enrichment for meeting participants"
        )
        
        # Register dependency on mail agent  
        self.register_agent_dependency(
            "mail-agent",
            ["messages.search", "messages.read"],
            "Email context for meeting preparation and follow-up"
        )
        
        # Register dependency on imessage agent
        self.register_agent_dependency(
            "imessage-agent", 
            ["messages.search", "messages.read"],
            "Message context for informal meeting arrangements"
        )
        
        print(f"Registered cross-platform dependencies: {list(self.agent_dependencies.keys())}")
    
    async def _handle_enhanced_capability(self, capability: str, params: Dict[str, Any]) -> ConfidenceResult:
        """Handle enhanced LLM-powered capabilities with comprehensive error handling."""
        start_time = time.time()
        
        try:
            self.logger.info(f"Executing enhanced capability: {capability} with params: {list(params.keys())}")
            
            if capability == "calendar.smart_schedule":
                result = await self._smart_schedule_with_llm(params)
            elif capability == "calendar.conflict_resolve":
                result = await self._resolve_conflicts_with_llm(params)
            elif capability == "calendar.meeting_prep":
                result = await self._prepare_meeting_with_llm(params)
            elif capability == "calendar.availability_optimize":
                result = await self._optimize_availability_with_llm(params)
            elif capability == "calendar.context_analyze":
                result = await self._analyze_context_with_llm(params)
            elif capability == "calendar.read_with_contacts":
                query = params.get("query", "")
                date_range = params.get("date_range")
                result = await self._resolve_contacts_and_filter_events(query, date_range)
            else:
                self.logger.error(f"Unknown enhanced capability requested: {capability}")
                return ConfidenceResult(
                    result={"error": f"Unknown enhanced capability: {capability}"},
                    confidence=0.0,
                    reasoning="Capability not implemented"
                )
            
            execution_time = time.time() - start_time
            self.logger.info(f"Successfully executed {capability} in {execution_time:.3f}s with confidence {result.confidence}")
            
            return result
            
        except ValueError as e:
            execution_time = time.time() - start_time
            self.logger.error(f"ValueError in {capability} after {execution_time:.3f}s: {str(e)}")
            return ConfidenceResult(
                result={
                    "error": f"Invalid parameters for {capability}: {str(e)}",
                    "error_type": "validation_error"
                },
                confidence=0.0,
                reasoning=f"Parameter validation failed for {capability}: {str(e)}"
            )
        except TimeoutError as e:
            execution_time = time.time() - start_time
            self.logger.error(f"TimeoutError in {capability} after {execution_time:.3f}s: {str(e)}")
            return ConfidenceResult(
                result={
                    "error": f"Timeout executing {capability}: {str(e)}",
                    "error_type": "timeout_error",
                    "execution_time": execution_time
                },
                confidence=0.0,
                reasoning=f"Capability {capability} timed out after {execution_time:.3f}s"
            )
        except ConnectionError as e:
            execution_time = time.time() - start_time
            self.logger.error(f"ConnectionError in {capability} after {execution_time:.3f}s: {str(e)}")
            return ConfidenceResult(
                result={
                    "error": f"Connection error in {capability}: {str(e)}",
                    "error_type": "connection_error",
                    "fallback_suggestion": "Check calendar bridge connectivity"
                },
                confidence=0.0,
                reasoning=f"Connection failed for {capability}: {str(e)}"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Unexpected error in {capability} after {execution_time:.3f}s: {str(e)}", exc_info=True)
            return ConfidenceResult(
                result={
                    "error": f"Unexpected error in {capability}: {str(e)}",
                    "error_type": "unexpected_error",
                    "execution_time": execution_time
                },
                confidence=0.0,
                reasoning=f"Unexpected error processing {capability}: {str(e)}"
            )
    
    async def _smart_schedule_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Intelligently schedule events using LLM understanding."""
        request = params.get("request", "")
        constraints = params.get("constraints", {})
        participants = params.get("participants", [])
        
        prompt = f"""
        Help schedule this meeting intelligently:
        
        Request: "{request}"
        Constraints: {constraints}
        Participants: {participants}
        
        Consider:
        1. Optimal time slots based on typical schedules
        2. Meeting duration appropriate for the topic
        3. Participant preferences and timezones
        4. Buffer time before/after other meetings
        5. Meeting room or location requirements
        
        Suggest the best scheduling options with reasoning.
        """
        
        scheduling_analysis = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "scheduling_suggestions": scheduling_analysis,
                "original_request": request,
                "constraints": constraints,
                "participants": participants
            },
            confidence=0.85,
            reasoning="LLM-powered intelligent scheduling analysis"
        )
    
    async def _resolve_conflicts_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Resolve scheduling conflicts using LLM intelligence."""
        conflicts = params.get("conflicts", [])
        priority_context = params.get("priority_context", {})
        
        prompt = f"""
        Resolve these calendar conflicts intelligently:
        
        Conflicts: {conflicts}
        Priority Context: {priority_context}
        
        For each conflict, suggest:
        1. Which meeting is more important and why
        2. Alternative time slots for lower priority meetings
        3. Possible meeting adjustments (duration, format)
        4. Participant notification strategies
        5. Rescheduling options that minimize impact
        
        Provide actionable conflict resolution recommendations.
        """
        
        resolution_analysis = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "conflict_resolutions": resolution_analysis,
                "conflicts": conflicts,
                "priority_context": priority_context
            },
            confidence=0.80,
            reasoning="LLM-based conflict resolution analysis"
        )
    
    async def _prepare_meeting_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Prepare meeting context and recommendations using LLM."""
        event_details = params.get("event_details", {})
        participant_history = params.get("participant_history", {})
        
        prompt = f"""
        Prepare comprehensive meeting context:
        
        Event: {event_details}
        Participant History: {participant_history}
        
        Provide:
        1. Meeting agenda suggestions based on title/description
        2. Participant background and relevant context
        3. Preparation materials and resources needed
        4. Key discussion points and objectives
        5. Follow-up action items template
        6. Meeting format recommendations (video, in-person, etc.)
        
        Generate actionable meeting preparation guidance.
        """
        
        preparation_guide = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "preparation_guide": preparation_guide,
                "event_details": event_details,
                "participant_history": participant_history
            },
            confidence=0.75,
            reasoning="LLM-generated meeting preparation guidance"
        )
    
    async def _optimize_availability_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Optimize calendar availability using LLM intelligence."""
        calendar_data = params.get("calendar_data", {})
        optimization_goals = params.get("goals", {})
        
        prompt = f"""
        Optimize calendar availability:
        
        Current Calendar: {calendar_data}
        Optimization Goals: {optimization_goals}
        
        Analyze:
        1. Current meeting distribution and patterns
        2. Focus time blocks and productivity windows
        3. Meeting-free periods for deep work
        4. Travel time and buffer requirements
        5. Work-life balance considerations
        
        Suggest calendar optimization strategies.
        """
        
        optimization_analysis = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "optimization_suggestions": optimization_analysis,
                "calendar_data": calendar_data,
                "goals": optimization_goals
            },
            confidence=0.70,
            reasoning="LLM-powered calendar optimization analysis"
        )
    
    async def _analyze_context_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Analyze meeting context using LLM understanding."""
        try:
            query = params.get("query", "")
            event = params.get("event", {})
            related_communications = params.get("communications", [])
            
            # If we have a query but no specific event, try to extract context from the query
            if query and not event:
                # Parse query for context clues
                context_info = {
                    "query": query,
                    "parsed_entities": self._extract_entities_from_query(query),
                    "inferred_context": "User is asking about calendar events"
                }
                
                prompt = f"""
                Analyze this calendar query context:
                
                Query: "{query}"
                
                Extract and analyze:
                1. Intent and purpose of the query
                2. Key entities mentioned (people, dates, events)
                3. Context clues about what information is needed
                4. Potential follow-up questions or related information
                5. Suggested calendar data to retrieve
                
                Provide structured context analysis.
                """
                
                context_analysis = await self.process_with_llm(prompt)
                
                return ConfidenceResult(
                    result={
                        "context_analysis": context_analysis,
                        "query_context": context_info,
                        "analysis_type": "query_context"
                    },
                    confidence=0.75,
                    reasoning="LLM analysis of calendar query context"
                )
            
            # Original meeting context analysis
            prompt = f"""
            Analyze this meeting context:
            
            Event: {event}
            Related Communications: {related_communications}
            Query: {query}
            
            Extract:
            1. Meeting purpose and objectives
            2. Key stakeholders and their roles
            3. Decision points and deliverables
            4. Background context from communications
            5. Success criteria and outcomes
            6. Potential risks or challenges
            
            Provide comprehensive context analysis.
            """
            
            context_analysis = await self.process_with_llm(prompt)
            
            return ConfidenceResult(
                result={
                    "context_analysis": context_analysis,
                    "event": event,
                    "communications": related_communications,
                    "analysis_type": "meeting_context"
                },
                confidence=0.80,
                reasoning="LLM context analysis of meeting and communications"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={
                    "error": f"Context analysis failed: {str(e)}",
                    "fallback_analysis": "Unable to analyze context due to processing error"
                },
                confidence=0.0,
                reasoning=f"Error in context analysis: {str(e)}"
            )
    
    def _extract_entities_from_query(self, query: str) -> Dict[str, Any]:
        """Extract entities from query text (simple implementation)."""
        entities = {
            "people": [],
            "dates": [],
            "events": [],
            "actions": []
        }
        
        # Simple keyword matching for people names (this could be enhanced)
        import re
        
        # Look for potential names (capitalized words)
        potential_names = re.findall(r'\b[A-Z][a-z]+\b', query)
        entities["people"] = potential_names
        
        # Look for date-related terms
        date_terms = ["upcoming", "today", "tomorrow", "next week", "this week", "next month"]
        for term in date_terms:
            if term.lower() in query.lower():
                entities["dates"].append(term)
        
        # Look for event-related terms
        event_terms = ["meeting", "event", "appointment", "call", "conference"]
        for term in event_terms:
            if term.lower() in query.lower():
                entities["events"].append(term)
                
        return entities
    
    async def _resolve_contacts_and_filter_events(self, query: str, date_range: Optional[Dict[str, str]] = None) -> ConfidenceResult:
        """
        Resolve contacts from query and filter calendar events by those contacts.
        
        Args:
            query: Natural language query containing contact names
            date_range: Optional date range for filtering events
            
        Returns:
            ConfidenceResult with filtered calendar events
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Resolving contacts and filtering events for query: '{query}'")
            
            # Extract potential contact names from query
            entities = self._extract_entities_from_query(query)
            contact_names = entities.get("people", [])
            
            if not contact_names:
                self.logger.info("No contact names found in query, proceeding with regular calendar read")
                # No contacts found, just return regular calendar read
                read_params = {"query": query}
                if date_range:
                    read_params["date_range"] = date_range
                
                calendar_result = await self.read_handler.execute(read_params)
                execution_time = time.time() - start_time
                
                return ConfidenceResult(
                    result={
                        "calendar_events": calendar_result,
                        "resolved_contacts": [],
                        "query_entities": entities,
                        "contact_integration": "no_contacts_in_query",
                        "execution_time": execution_time
                    },
                    confidence=0.70,
                    reasoning="Calendar events retrieved without contact filtering (no contact names found)"
                )
            
            self.logger.info(f"Found potential contact names: {contact_names}")
            
            # Query contacts agent to resolve contact information
            contact_results = []
            contact_errors = []
            
            if hasattr(self, 'registry_client') and self.registry_client:
                for name in contact_names:
                    try:
                        self.logger.info(f"Resolving contact: '{name}'")
                        contact_result = await self.query_agent(
                            "contacts-agent", 
                            "contacts.resolve", 
                            {"query": name},
                            timeout=5.0
                        )
                        if contact_result and contact_result.get("contacts"):
                            contact_results.extend(contact_result["contacts"])
                            self.logger.info(f"Successfully resolved contact '{name}': {len(contact_result['contacts'])} matches")
                        else:
                            self.logger.warning(f"No contacts found for '{name}'")
                    except Exception as e:
                        error_msg = f"Failed to resolve contact '{name}': {e}"
                        self.logger.error(error_msg)
                        contact_errors.append(error_msg)
            else:
                error_msg = "No registry client available for contact resolution"
                self.logger.error(error_msg)
                contact_errors.append(error_msg)
            
            # Get calendar events for the date range
            read_params = {"query": query}
            if date_range:
                read_params["date_range"] = date_range
                
            # If we found contacts, add them as a filter
            if contact_results:
                read_params["contact_filter"] = {
                    "contacts": contact_results,
                    "query_names": contact_names
                }
                self.logger.info(f"Applying contact filter with {len(contact_results)} resolved contacts")
            
            calendar_result = await self.read_handler.execute(read_params)
            execution_time = time.time() - start_time
            
            result_confidence = 0.85 if contact_results else 0.60
            if contact_errors:
                result_confidence *= 0.8  # Reduce confidence if there were contact resolution errors
            
            self.logger.info(f"Contact resolution and calendar filtering completed in {execution_time:.3f}s")
            
            return ConfidenceResult(
                result={
                    "calendar_events": calendar_result,
                    "resolved_contacts": contact_results,
                    "query_entities": entities,
                    "contact_integration": "enabled" if contact_results else "no_contacts_found",
                    "contact_errors": contact_errors,
                    "execution_time": execution_time
                },
                confidence=result_confidence,
                reasoning=f"Calendar events filtered by {len(contact_results)} resolved contacts" if contact_results else "Calendar events without contact filtering"
            )
            
        except ValueError as e:
            execution_time = time.time() - start_time
            error_msg = f"Invalid parameters for contact resolution: {str(e)}"
            self.logger.error(error_msg)
            return ConfidenceResult(
                result={
                    "error": error_msg,
                    "error_type": "validation_error",
                    "execution_time": execution_time
                },
                confidence=0.0,
                reasoning=f"Parameter validation failed: {str(e)}"
            )
        except TimeoutError as e:
            execution_time = time.time() - start_time
            error_msg = f"Timeout during contact resolution: {str(e)}"
            self.logger.error(error_msg)
            return ConfidenceResult(
                result={
                    "error": error_msg,
                    "error_type": "timeout_error",
                    "execution_time": execution_time,
                    "fallback_suggestion": "Try calendar query without contact filtering"
                },
                confidence=0.0,
                reasoning=f"Contact resolution timed out: {str(e)}"
            )
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Contact resolution and event filtering failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return ConfidenceResult(
                result={
                    "error": error_msg,
                    "error_type": "unexpected_error",
                    "execution_time": execution_time,
                    "fallback_suggestion": "Consider querying calendar without contact filtering"
                },
                confidence=0.0,
                reasoning=f"Error in contact integration: {str(e)}"
            )
    
    def get_agent_context(self) -> str:
        """Get agent context for LLM processing."""
        return f"""
        You are the Intelligent Calendar Agent for Kenny v2.1.
        
        You help users with natural language calendar queries including:
        - Smart event scheduling with conflict resolution
        - Meeting preparation and context analysis
        - Calendar optimization for productivity
        - Cross-platform participant coordination
        - Intelligent availability management
        
        You have access to:
        - Apple Calendar via macOS Bridge
        - Contact information through contacts agent
        - Email context through mail agent
        - Message context through imessage agent
        
        Always prioritize user productivity and provide actionable scheduling guidance.
        """
    
    def get_multi_platform_context(self) -> str:
        """Get multi-platform integration context."""
        return f"""
        Cross-platform integrations available:
        
        Contacts Agent: Resolve meeting participants and enrich contact information
        Mail Agent: Analyze email context for meeting preparation and follow-up
        iMessage Agent: Understand informal meeting arrangements via messages
        
        Dependencies: {list(self.agent_dependencies.keys())}
        """
    
    async def schedule_with_natural_language(self, request: str, context: Dict[str, Any] = None) -> ConfidenceResult:
        """Schedule events using natural language interpretation."""
        try:
            # Use LLM to interpret the natural language scheduling request
            interpretation_prompt = f"""
            Interpret this natural language calendar request:
            "{request}"
            
            Extract:
            - Event title and description
            - Date and time preferences
            - Duration estimates
            - Participants and their roles
            - Location or meeting format preferences
            - Priority level and urgency
            - Any special requirements
            
            Return structured event parameters.
            """
            
            event_params = await self.process_with_llm(interpretation_prompt)
            
            # Create event proposal using interpreted parameters
            proposal_result = await self.propose_event_handler.execute({
                "natural_request": request,
                "interpreted_params": event_params,
                "context": context or {}
            })
            
            return ConfidenceResult(
                result={
                    "event_proposal": proposal_result,
                    "interpretation": event_params,
                    "original_request": request
                },
                confidence=0.85,
                reasoning="Natural language event scheduling with LLM interpretation"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Error in natural language scheduling: {str(e)}"
            )
    
    async def analyze_schedule_patterns(self, timeframe: str = "week") -> ConfidenceResult:
        """Analyze calendar patterns and provide insights."""
        try:
            # Get calendar data for analysis
            calendar_data = await self.read_handler.execute({"timeframe": timeframe})
            
            # Analyze patterns with LLM
            analysis_prompt = f"""
            Analyze these calendar patterns:
            
            Timeframe: {timeframe}
            Calendar Data: {calendar_data}
            
            Identify:
            1. Meeting frequency and distribution patterns
            2. Most productive time blocks
            3. Overcommitted periods and potential burnout risks
            4. Recurring meeting efficiency
            5. Focus time availability
            6. Work-life balance indicators
            
            Provide actionable insights for schedule optimization.
            """
            
            pattern_analysis = await self.process_with_llm(analysis_prompt)
            
            return ConfidenceResult(
                result={
                    "pattern_analysis": pattern_analysis,
                    "timeframe": timeframe,
                    "calendar_summary": calendar_data
                },
                confidence=0.80,
                reasoning="LLM-powered schedule pattern analysis"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Error in schedule pattern analysis: {str(e)}"
            )
    
    async def start(self):
        """Start the Intelligent Calendar Agent and register with the registry."""
        print(f"Starting {self.name}...")
        print(f"Agent ID: {self.agent_id}")
        print(f"LLM Model: {self.llm_processor.model_name}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        
        # Try to register with agent registry
        try:
            await self.registry_client.register_agent(
                agent_id=self.agent_id,
                manifest=self.generate_manifest(),
                health_endpoint=f"http://localhost:8007/health"
            )
            print(f"Successfully registered {self.name} with agent registry")
        except Exception as e:
            print(f"Warning: Could not register with agent registry: {e}")
        
        print(f"{self.name} started successfully!")
    
    async def stop(self):
        """Stop the Intelligent Calendar Agent."""
        print(f"Stopping {self.name}...")
        # Cleanup any resources if needed
        print(f"{self.name} stopped successfully!")