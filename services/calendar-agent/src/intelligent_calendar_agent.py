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
        
        # Enhanced capabilities for natural language processing
        enhanced_capabilities = [
            "calendar.smart_schedule",
            "calendar.conflict_resolve", 
            "calendar.meeting_prep",
            "calendar.availability_optimize",
            "calendar.context_analyze"
        ]
        
        for capability in enhanced_capabilities:
            self.capabilities[capability] = {
                "handler": self._handle_enhanced_capability,
                "description": f"Enhanced {capability} with LLM processing",
                "confidence_scoring": True
            }
        
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
        """Handle enhanced LLM-powered capabilities."""
        try:
            if capability == "calendar.smart_schedule":
                return await self._smart_schedule_with_llm(params)
            elif capability == "calendar.conflict_resolve":
                return await self._resolve_conflicts_with_llm(params)
            elif capability == "calendar.meeting_prep":
                return await self._prepare_meeting_with_llm(params)
            elif capability == "calendar.availability_optimize":
                return await self._optimize_availability_with_llm(params)
            elif capability == "calendar.context_analyze":
                return await self._analyze_context_with_llm(params)
            else:
                return ConfidenceResult(
                    result={"error": f"Unknown enhanced capability: {capability}"},
                    confidence=0.0,
                    reasoning="Capability not implemented"
                )
        except Exception as e:
            return ConfidenceResult(
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Error processing {capability}: {str(e)}"
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
        event = params.get("event", {})
        related_communications = params.get("communications", [])
        
        prompt = f"""
        Analyze this meeting context:
        
        Event: {event}
        Related Communications: {related_communications}
        
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
                "communications": related_communications
            },
            confidence=0.80,
            reasoning="LLM context analysis of meeting and communications"
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