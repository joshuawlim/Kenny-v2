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
from kenny_agent.cache_warming_service import CacheWarmingService
from kenny_agent.intelligent_cache_orchestrator import IntelligentCacheOrchestrator

from handlers.read import ReadCapabilityHandler
from handlers.propose_event import ProposeEventCapabilityHandler
from handlers.write_event import WriteEventCapabilityHandler
from tools.calendar_bridge import CalendarBridgeTool
from performance_monitor import get_performance_monitor, log_calendar_operation


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
        
        # Initialize performance monitoring for Phase 3.2.1
        self.performance_monitor = get_performance_monitor()
        self.logger.info("Performance monitoring enabled for parallel processing optimizations")
        
        # Initialize Phase 3.2.2 Multi-Tier Caching
        self.cache_warming_service = CacheWarmingService(self, warming_interval=3600)  # 1 hour
        self.logger.info("Phase 3.2.2 Multi-Tier Caching initialized with Redis L2 layer")
        
        # Initialize Phase 3.2.3 Predictive Cache Warming
        self.cache_orchestrator = IntelligentCacheOrchestrator(self)
        self.logger.info("Phase 3.2.3 Predictive Cache Warming initialized with ML intelligence")
        
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
            "calendar.read_with_contacts",
            "calendar.cache_stats",
            "calendar.cache_warm",
            "calendar.predictive_insights",
            "calendar.orchestration_status"
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
        """Handle enhanced LLM-powered capabilities with comprehensive error handling and performance monitoring."""
        async with self.performance_monitor.monitor_operation(
            operation_name=f"enhanced_capability_{capability}",
            capability=capability,
            param_count=len(params)
        ) as metrics:
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
            elif capability == "calendar.cache_stats":
                result = await self._get_cache_performance_stats(params)
            elif capability == "calendar.cache_warm":
                result = await self._warm_cache_patterns(params)
            elif capability == "calendar.predictive_insights":
                result = await self._get_predictive_insights(params)
            elif capability == "calendar.orchestration_status":
                result = await self._get_orchestration_status(params)
            else:
                self.logger.error(f"Unknown enhanced capability requested: {capability}")
                return ConfidenceResult(
                    result={"error": f"Unknown enhanced capability: {capability}"},
                    confidence=0.0,
                    reasoning="Capability not implemented"
                )
            
                execution_time = time.time() - start_time
                metrics.success_count += 1
                metrics.metadata.update({
                    "confidence": result.confidence,
                    "result_type": type(result.result).__name__
                })
                self.logger.info(f"Successfully executed {capability} in {execution_time:.3f}s with confidence {result.confidence}")
                
                return result
            
            except ValueError as e:
                execution_time = time.time() - start_time
                metrics.error_count += 1
                metrics.metadata["error_type"] = "validation_error"
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
                metrics.error_count += 1
                metrics.metadata["error_type"] = "timeout_error"
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
                metrics.error_count += 1
                metrics.metadata["error_type"] = "connection_error"
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
                metrics.error_count += 1
                metrics.metadata["error_type"] = "unexpected_error"
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
        async with self.performance_monitor.monitor_operation(
            operation_name="resolve_contacts_and_filter_events",
            query_length=len(query),
            has_date_range=bool(date_range)
        ) as metrics:
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
            
            # Query contacts agent to resolve contact information (parallel for performance)
            contact_results = []
            contact_errors = []
            
            if hasattr(self, 'registry_client') and self.registry_client:
                # Parallelize contact resolution for better performance
                contact_tasks = []
                metrics.concurrent_tasks = len(contact_names)
                metrics.parallel_operations = len(contact_names) if len(contact_names) > 1 else 1
                
                for name in contact_names:
                    task = asyncio.create_task(
                        self._resolve_single_contact(name),
                        name=f"resolve_contact_{name}"
                    )
                    contact_tasks.append(task)
                
                # Execute all contact resolutions in parallel
                if contact_tasks:
                    contact_task_results = await asyncio.gather(*contact_tasks, return_exceptions=True)
                    
                    for i, result in enumerate(contact_task_results):
                        if isinstance(result, Exception):
                            error_msg = f"Failed to resolve contact '{contact_names[i]}': {result}"
                            self.logger.error(error_msg)
                            contact_errors.append(error_msg)
                            metrics.error_count += 1
                        elif result and result.get("contacts"):
                            contact_results.extend(result["contacts"])
                            self.logger.info(f"Successfully resolved contact '{contact_names[i]}': {len(result['contacts'])} matches")
                            metrics.success_count += 1
                        else:
                            self.logger.warning(f"No contacts found for '{contact_names[i]}'")
            else:
                error_msg = "No registry client available for contact resolution"
                self.logger.error(error_msg)
                contact_errors.append(error_msg)
                metrics.error_count += 1
            
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
            
            # Update performance metrics
            metrics.metadata.update({
                "contacts_resolved": len(contact_results),
                "contact_errors": len(contact_errors),
                "entities_found": len(entities.get("people", [])),
                "confidence": result_confidence
            })
            
            self.logger.info(f"Contact resolution and calendar filtering completed in {execution_time:.3f}s")
            
            return ConfidenceResult(
                result={
                    "calendar_events": calendar_result,
                    "resolved_contacts": contact_results,
                    "query_entities": entities,
                    "contact_integration": "enabled" if contact_results else "no_contacts_found",
                    "contact_errors": contact_errors,
                    "execution_time": execution_time,
                    "performance_optimized": True
                },
                confidence=result_confidence,
                reasoning=f"Calendar events filtered by {len(contact_results)} resolved contacts with parallel processing" if contact_results else "Calendar events without contact filtering"
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
    
    async def _resolve_single_contact(self, name: str) -> Optional[Dict[str, Any]]:
        """Resolve a single contact asynchronously."""
        try:
            self.logger.info(f"Resolving contact: '{name}'")
            contact_result = await self.query_agent(
                "contacts-agent", 
                "contacts.resolve", 
                {"query": name},
                timeout=5.0
            )
            return contact_result
        except Exception as e:
            self.logger.error(f"Failed to resolve contact '{name}': {e}")
            return None
    
    def get_multi_platform_context(self) -> str:
        """Get multi-platform integration context."""
        return f"""
        Cross-platform integrations available (with parallel processing):
        
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
        """Start the Intelligent Calendar Agent with parallel processing optimizations and register with the registry."""
        print(f"Starting {self.name} with Phase 3.2.1 parallel processing optimizations...")
        print(f"Agent ID: {self.agent_id}")
        print(f"LLM Model: {self.llm_processor.model_name}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        print(f"Parallel Processing: Enabled for contact resolution and calendar operations")
        
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
        
        print(f"{self.name} started successfully with performance optimizations!")
        
        # Start cache warming service for Phase 3.2.2
        try:
            await self.cache_warming_service.start()
            self.logger.info("Cache warming service started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start cache warming service: {e}")
        
        # Start intelligent cache orchestrator for Phase 3.2.3
        try:
            await self.cache_orchestrator.start()
            self.logger.info("Intelligent cache orchestrator started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start cache orchestrator: {e}")
        
        # Log Phase 3.2.1 & 3.2.2 & 3.2.3 optimizations
        self.logger.info("Phase 3.2.1 Parallel Processing Optimizations Active:")
        self.logger.info("- Async calendar bridge with connection pooling")
        self.logger.info("- Parallel contact resolution")
        self.logger.info("- Enhanced event fetching with auto-parallelization")
        self.logger.info("- Comprehensive performance monitoring")
        
        self.logger.info("Phase 3.2.2 Multi-Tier Caching Optimizations Active:")
        self.logger.info("- L1 In-Memory cache (30s TTL, 1000 entries)")
        self.logger.info("- L2 Redis cache (5min TTL, connection pooling)")
        self.logger.info("- L3 SQLite cache (1hr TTL, persistent)")
        self.logger.info("- Background cache warming service")
        self.logger.info("- Intelligent cache promotion and invalidation")
        
        self.logger.info("Phase 3.2.3 Predictive Cache Warming Active:")
        self.logger.info("- ML-based query pattern prediction")
        self.logger.info("- Real-time EventKit calendar change monitoring")
        self.logger.info("- Intelligent cache orchestration and optimization")
        self.logger.info("- Adaptive learning and prediction accuracy tracking")
        self.logger.info("- Event-driven cache invalidation and refresh")
    
    async def stop(self):
        """Stop the Intelligent Calendar Agent and cleanup resources."""
        print(f"Stopping {self.name}...")
        
        # Cleanup calendar bridge async client
        calendar_bridge_tool = self.tools.get("calendar_bridge")
        if calendar_bridge_tool and hasattr(calendar_bridge_tool, 'cleanup'):
            try:
                await calendar_bridge_tool.cleanup()
                print("Calendar bridge async client cleaned up successfully")
            except Exception as e:
                print(f"Warning: Error cleaning up calendar bridge: {e}")
        
        # Stop cache warming service
        try:
            await self.cache_warming_service.stop()
            self.logger.info("Cache warming service stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping cache warming service: {e}")
        
        # Stop intelligent cache orchestrator
        try:
            await self.cache_orchestrator.stop()
            self.logger.info("Intelligent cache orchestrator stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping cache orchestrator: {e}")
        
        # Log final performance summary
        self.performance_monitor.log_performance_summary()
        
        # Log final cache statistics
        if hasattr(self, 'semantic_cache'):
            cache_stats = self.semantic_cache.get_cache_stats()
            self.logger.info("Final cache performance statistics:")
            self.logger.info(f"- L1 hit rate: {cache_stats['l1_cache']['hit_rate_percent']}%")
            self.logger.info(f"- L2 hit rate: {cache_stats['l2_cache']['hit_rate_percent']}%") 
            self.logger.info(f"- L3 hit rate: {cache_stats['l3_cache']['hit_rate_percent']}%")
            self.logger.info(f"- Overall hit rate: {cache_stats['overall_performance']['total_hit_rate_percent']}%")
        
        # Log Phase 3.2.3 final performance
        try:
            orchestration_insights = await self.cache_orchestrator.get_orchestration_insights()
            performance_improvement = orchestration_insights.get("performance_improvement", {})
            self.logger.info("Phase 3.2.3 Predictive Cache Warming Final Results:")
            self.logger.info(f"- Overall performance gain: {performance_improvement.get('overall_performance_gain', 0):.1f}%")
            self.logger.info(f"- Prediction accuracy: {performance_improvement.get('prediction_accuracy', 0):.1%}")
            self.logger.info(f"- Cache hit rate improvement: {performance_improvement.get('cache_hit_rate_improvement', 0):.1f}%")
            self.logger.info(f"- Response time improvement: {performance_improvement.get('response_time_improvement', 0):.1f}%")
        except Exception as e:
            self.logger.error(f"Error logging Phase 3.2.3 final performance: {e}")
        
        print(f"{self.name} stopped successfully!")
    
    async def process_natural_language_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Override base method to use orchestrated query processing with Phase 3.2.3 intelligence.
        """
        try:
            # Use orchestrated processing for enhanced performance
            if hasattr(self, 'cache_orchestrator') and self.cache_orchestrator.is_running:
                return await self.cache_orchestrator.process_query_with_orchestration(query)
            else:
                # Fallback to base method if orchestrator not available
                return await super().process_natural_language_query(query, context)
        
        except Exception as e:
            self.logger.error(f"Error in orchestrated query processing, falling back to base method: {e}")
            return await super().process_natural_language_query(query, context)
    
    async def _get_cache_performance_stats(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Get comprehensive cache performance statistics for Phase 3.2.2."""
        try:
            # Get cache statistics from semantic cache
            cache_stats = self.semantic_cache.get_cache_stats()
            
            # Get cache warming service statistics
            warming_stats = self.cache_warming_service.get_warming_stats()
            
            # Calculate performance improvements
            performance_metrics = self.get_performance_metrics()
            
            result = {
                "cache_performance": {
                    "multi_tier_stats": cache_stats,
                    "cache_warming_stats": warming_stats,
                    "agent_performance": performance_metrics,
                    "phase_3_2_2_status": "Active - Multi-Tier Aggressive Caching"
                },
                "performance_summary": {
                    "l1_hit_rate": cache_stats["l1_cache"]["hit_rate_percent"],
                    "l2_hit_rate": cache_stats["l2_cache"]["hit_rate_percent"],
                    "l3_hit_rate": cache_stats["l3_cache"]["hit_rate_percent"],
                    "overall_hit_rate": cache_stats["overall_performance"]["total_hit_rate_percent"],
                    "cache_effectiveness": "excellent" if cache_stats["overall_performance"]["total_hit_rate_percent"] > 80 else
                                        "good" if cache_stats["overall_performance"]["total_hit_rate_percent"] > 60 else
                                        "needs_improvement"
                },
                "optimization_targets": {
                    "l1_target": ">70%",
                    "l2_target": ">85%",
                    "l3_target": ">95%",
                    "response_time_target": "<2s for cached queries"
                }
            }
            
            return ConfidenceResult(
                result=result,
                confidence=1.0,
                reasoning="Cache performance statistics retrieved successfully"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={
                    "error": f"Error retrieving cache stats: {str(e)}",
                    "fallback_info": "Cache performance monitoring temporarily unavailable"
                },
                confidence=0.0,
                reasoning=f"Cache stats retrieval failed: {str(e)}"
            )
    
    async def _warm_cache_patterns(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Manually trigger cache warming for specific patterns."""
        try:
            patterns = params.get("patterns", [])
            force_warm = params.get("force", False)
            
            if not patterns:
                # Use default warming patterns
                patterns = [
                    "events today",
                    "meetings today",
                    "schedule this week",
                    "upcoming meetings"
                ]
            
            warmed_count = 0
            errors = []
            
            for pattern in patterns:
                try:
                    if force_warm:
                        await self.cache_warming_service.force_warm_pattern(pattern)
                    else:
                        # Use regular warming
                        await self.process_natural_language_query(pattern)
                    
                    warmed_count += 1
                    self.logger.info(f"Warmed cache for pattern: {pattern}")
                    
                except Exception as e:
                    error_msg = f"Failed to warm pattern '{pattern}': {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
            
            result = {
                "cache_warming_result": {
                    "patterns_requested": len(patterns),
                    "patterns_warmed": warmed_count,
                    "success_rate": (warmed_count / len(patterns)) * 100,
                    "errors": errors,
                    "warming_service_stats": self.cache_warming_service.get_warming_stats()
                }
            }
            
            confidence = 0.9 if warmed_count == len(patterns) else 0.7 if warmed_count > 0 else 0.3
            
            return ConfidenceResult(
                result=result,
                confidence=confidence,
                reasoning=f"Cache warming completed: {warmed_count}/{len(patterns)} patterns warmed"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={
                    "error": f"Cache warming failed: {str(e)}",
                    "fallback_suggestion": "Try warming individual patterns manually"
                },
                confidence=0.0,
                reasoning=f"Cache warming error: {str(e)}"
            )
    
    async def _get_predictive_insights(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Get predictive cache warming insights and recommendations."""
        try:
            # Get comprehensive orchestration insights
            insights = await self.cache_orchestrator.get_orchestration_insights()
            
            # Get pattern analysis statistics
            pattern_stats = self.cache_orchestrator.pattern_analyzer.get_analysis_stats()
            
            # Generate current predictions
            current_time = datetime.now()
            predictions = await self.cache_orchestrator.pattern_analyzer.predict_likely_queries(current_time)
            
            result = {
                "predictive_insights": {
                    "phase_3_2_3_status": "Active - ML-Based Predictive Cache Warming",
                    "orchestration_insights": insights,
                    "pattern_analysis": pattern_stats,
                    "current_predictions": [
                        {
                            "query": pred.query,
                            "probability": pred.probability,
                            "confidence": pred.confidence,
                            "reasoning": pred.reasoning,
                            "query_type": pred.query_type
                        } for pred in predictions[:10]  # Top 10 predictions
                    ],
                    "performance_targets": {
                        "target_improvement": "70-80% total improvement (41s → 8-12s)",
                        "prediction_accuracy_target": ">80%",
                        "cache_efficiency_target": ">90% hit rate",
                        "real_time_response_target": "<1s invalidation"
                    }
                }
            }
            
            return ConfidenceResult(
                result=result,
                confidence=1.0,
                reasoning="Phase 3.2.3 predictive insights retrieved successfully"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={
                    "error": f"Error retrieving predictive insights: {str(e)}",
                    "fallback_info": "Predictive analytics temporarily unavailable"
                },
                confidence=0.0,
                reasoning=f"Predictive insights retrieval failed: {str(e)}"
            )
    
    async def _get_orchestration_status(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Get comprehensive cache orchestration status."""
        try:
            # Get orchestration status
            orchestration_insights = await self.cache_orchestrator.get_orchestration_insights()
            
            # Get component statuses
            pattern_analyzer_running = hasattr(self.cache_orchestrator, 'pattern_analyzer')
            event_monitor_running = self.cache_orchestrator.event_monitor.monitoring_enabled
            predictive_warmer_running = self.cache_orchestrator.predictive_warmer.is_running
            
            # Calculate overall system health
            components_healthy = sum([
                pattern_analyzer_running,
                event_monitor_running, 
                predictive_warmer_running,
                self.cache_orchestrator.is_running
            ])
            
            system_health = "excellent" if components_healthy == 4 else \
                           "good" if components_healthy >= 3 else \
                           "degraded" if components_healthy >= 2 else "critical"
            
            result = {
                "orchestration_status": {
                    "system_health": system_health,
                    "components_status": {
                        "cache_orchestrator": self.cache_orchestrator.is_running,
                        "pattern_analyzer": pattern_analyzer_running,
                        "event_monitor": event_monitor_running,
                        "predictive_warmer": predictive_warmer_running
                    },
                    "performance_summary": orchestration_insights.get("performance_improvement", {}),
                    "optimization_strategy": self.cache_orchestrator.current_strategy.value,
                    "prediction_accuracy": orchestration_insights.get("performance_improvement", {}).get("prediction_accuracy", 0.0),
                    "cache_hit_improvement": orchestration_insights.get("performance_improvement", {}).get("cache_hit_rate_improvement", 0.0),
                    "response_time_improvement": orchestration_insights.get("performance_improvement", {}).get("response_time_improvement", 0.0)
                }
            }
            
            return ConfidenceResult(
                result=result,
                confidence=1.0,
                reasoning="Cache orchestration status retrieved successfully"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={
                    "error": f"Error retrieving orchestration status: {str(e)}",
                    "fallback_info": "Orchestration status temporarily unavailable"
                },
                confidence=0.0,
                reasoning=f"Orchestration status retrieval failed: {str(e)}"
            )