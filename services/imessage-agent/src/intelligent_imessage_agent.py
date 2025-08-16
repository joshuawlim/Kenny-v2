"""
Intelligent iMessage Agent for Kenny v2.1

Enhanced iMessage Agent with embedded LLM capabilities for natural language
message analysis, conversation intelligence, and context-aware messaging.

Key Enhancements:
- Natural language message search: "Find recent messages from Sarah about project deadlines"
- Conversation context analysis and relationship mapping
- Intelligent message categorization and sentiment analysis
- Cross-platform thread correlation
"""

import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.agent_service_base import AgentServiceBase, ConfidenceResult
from kenny_agent.registry import AgentRegistryClient

from .handlers.search import SearchCapabilityHandler
from .handlers.read import ReadCapabilityHandler
from .handlers.propose_reply import ProposeReplyCapabilityHandler
from .tools.imessage_bridge import iMessageBridgeTool


class IntelligentiMessageAgent(AgentServiceBase):
    """
    Enhanced iMessage Agent with LLM-driven natural language processing.
    
    Transforms from basic API wrapper to intelligent service:
    - Natural language message search and analysis
    - Conversation context understanding
    - Cross-platform thread correlation
    - Intelligent reply suggestions
    """
    
    def __init__(self, llm_model: str = "llama3.2:3b"):
        """Initialize the Intelligent iMessage Agent."""
        super().__init__(
            agent_id="intelligent-imessage-agent",
            name="Intelligent iMessage Agent",
            description="AI-powered iMessage management with natural language processing, conversation intelligence, and context-aware messaging",
            version="2.1.0",
            llm_model=llm_model,
            data_scopes=["imessage:messages", "imessage:threads", "imessage:contacts"],
            tool_access=["macos-bridge", "sqlite-db", "ollama", llm_model],
            egress_domains=[]
        )
        
        print(f"Initialized Intelligent iMessage Agent with LLM model: {llm_model}")
        print("Initializing Intelligent iMessage Agent with LLM:", llm_model)
        
        # Initialize tools
        self._initialize_tools()
        
        # Initialize capability handlers  
        self._initialize_handlers()
        
        # Register enhanced capabilities
        print("Registering intelligent message capabilities...")
        self._register_enhanced_capabilities()
        
        # Register cross-platform dependencies
        print("Registering cross-platform dependencies...")
        self._register_dependencies()
        
        print("Intelligent iMessage Agent initialization complete!")
    
    def _initialize_tools(self):
        """Initialize iMessage-specific tools."""
        bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        print(f"Registering iMessage bridge tool with URL: {bridge_url}")
        self.register_tool(iMessageBridgeTool(bridge_url))
    
    def _initialize_handlers(self):
        """Initialize capability handlers."""
        # Initialize search handler
        self.search_handler = SearchCapabilityHandler()
        self.search_handler._agent = self
        
        # Initialize read handler
        self.read_handler = ReadCapabilityHandler()
        self.read_handler._agent = self
        
        # Initialize propose reply handler
        self.propose_reply_handler = ProposeReplyCapabilityHandler()
        self.propose_reply_handler._agent = self
    
    def _register_enhanced_capabilities(self):
        """Register enhanced intelligent capabilities."""
        # Register traditional capabilities with enhanced intelligence
        self.register_capability(self.search_handler)
        self.register_capability(self.read_handler)
        self.register_capability(self.propose_reply_handler)
        
        # Enhanced capabilities for natural language processing
        enhanced_capabilities = [
            "messages.analyze",
            "messages.categorize", 
            "messages.sentiment",
            "conversations.summarize"
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
            "Contact resolution and enrichment for message participants"
        )
        
        # Register dependency on mail agent  
        self.register_agent_dependency(
            "mail-agent",
            ["messages.search", "messages.read"],
            "Cross-platform message correlation with email"
        )
        
        # Register dependency on calendar agent
        self.register_agent_dependency(
            "calendar-agent", 
            ["calendar.read"],
            "Meeting context for message understanding"
        )
        
        print(f"Registered cross-platform dependencies: {list(self.agent_dependencies.keys())}")
    
    async def _handle_enhanced_capability(self, capability: str, params: Dict[str, Any]) -> ConfidenceResult:
        """Handle enhanced LLM-powered capabilities."""
        try:
            if capability == "messages.analyze":
                return await self._analyze_message_with_llm(params)
            elif capability == "messages.categorize":
                return await self._categorize_message_with_llm(params)
            elif capability == "messages.sentiment":
                return await self._analyze_sentiment_with_llm(params)
            elif capability == "conversations.summarize":
                return await self._summarize_conversation_with_llm(params)
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
    
    async def _analyze_message_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Analyze message content using LLM for context and intent."""
        message_text = params.get("message_text", "")
        context = params.get("context", {})
        
        prompt = f"""
        Analyze this iMessage for context, intent, and important information:
        
        Message: "{message_text}"
        Context: {context}
        
        Extract:
        1. Primary intent (question, request, information, social, etc.)
        2. Key topics mentioned
        3. Urgency level (low, medium, high)
        4. Action items or requests
        5. Sentiment (positive, neutral, negative)
        
        Respond with structured analysis.
        """
        
        analysis = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "analysis": analysis,
                "message_text": message_text,
                "enhanced_context": context
            },
            confidence=0.85,
            reasoning="LLM analysis of message content and context"
        )
    
    async def _categorize_message_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Categorize message using LLM understanding."""
        message_text = params.get("message_text", "")
        
        prompt = f"""
        Categorize this iMessage into appropriate categories:
        
        Message: "{message_text}"
        
        Categories: work, personal, family, social, urgent, informational, question, request, spam
        
        Return the most appropriate categories (can be multiple).
        """
        
        categories = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "categories": categories,
                "message_text": message_text
            },
            confidence=0.80,
            reasoning="LLM-based message categorization"
        )
    
    async def _analyze_sentiment_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Analyze message sentiment using LLM."""
        message_text = params.get("message_text", "")
        
        prompt = f"""
        Analyze the sentiment of this iMessage:
        
        Message: "{message_text}"
        
        Provide:
        1. Overall sentiment (positive, negative, neutral)
        2. Confidence score (0-1)
        3. Emotional indicators
        4. Tone (formal, casual, friendly, etc.)
        """
        
        sentiment = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "sentiment": sentiment,
                "message_text": message_text
            },
            confidence=0.75,
            reasoning="LLM sentiment analysis"
        )
    
    async def _summarize_conversation_with_llm(self, params: Dict[str, Any]) -> ConfidenceResult:
        """Summarize conversation thread using LLM."""
        messages = params.get("messages", [])
        
        conversation_text = "\n".join([f"{msg.get('sender', 'Unknown')}: {msg.get('text', '')}" for msg in messages])
        
        prompt = f"""
        Summarize this iMessage conversation:
        
        {conversation_text}
        
        Provide:
        1. Key discussion points
        2. Decisions made
        3. Action items
        4. Overall outcome
        5. Participant roles
        """
        
        summary = await self.process_with_llm(prompt)
        
        return ConfidenceResult(
            result={
                "summary": summary,
                "message_count": len(messages),
                "conversation_length": len(conversation_text)
            },
            confidence=0.80,
            reasoning="LLM conversation summarization"
        )
    
    def get_agent_context(self) -> str:
        """Get agent context for LLM processing."""
        return f"""
        You are the Intelligent iMessage Agent for Kenny v2.1.
        
        You help users with natural language iMessage queries including:
        - Searching messages with context understanding
        - Analyzing conversation content and sentiment
        - Categorizing messages automatically
        - Providing intelligent reply suggestions
        - Cross-platform thread correlation
        
        You have access to:
        - iMessage database via macOS Bridge
        - Contact resolution through contacts agent
        - Email correlation through mail agent
        - Meeting context through calendar agent
        
        Always prioritize user privacy and provide accurate, helpful responses.
        """
    
    def get_multi_platform_context(self) -> str:
        """Get multi-platform integration context."""
        return f"""
        Cross-platform integrations available:
        
        Contacts Agent: Resolve message participants and enrich contact information
        Mail Agent: Correlate iMessage conversations with email threads
        Calendar Agent: Understand meeting context for message timing
        
        Dependencies: {list(self.agent_dependencies.keys())}
        """
    
    async def search_messages_with_context(self, query: str, context: Dict[str, Any] = None) -> ConfidenceResult:
        """Enhanced message search with LLM query interpretation."""
        try:
            # Use LLM to interpret the natural language query
            interpretation_prompt = f"""
            Interpret this natural language iMessage search query:
            "{query}"
            
            Extract:
            - Keywords to search for
            - Time constraints (if any)
            - Sender/recipient preferences
            - Message type preferences
            - Any other search parameters
            
            Return structured search parameters.
            """
            
            search_params = await self.process_with_llm(interpretation_prompt)
            
            # Execute search using interpreted parameters
            search_result = await self.search_handler.execute({
                "query": query,
                "interpreted_params": search_params,
                "context": context or {}
            })
            
            return ConfidenceResult(
                result={
                    "messages": search_result,
                    "query_interpretation": search_params,
                    "original_query": query
                },
                confidence=0.85,
                reasoning="Enhanced search with LLM query interpretation"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Error in enhanced message search: {str(e)}"
            )
    
    async def analyze_conversation_flow(self, thread_id: str) -> ConfidenceResult:
        """Analyze conversation flow and relationship dynamics."""
        try:
            # Get conversation messages
            messages = await self.read_handler.execute({"thread_id": thread_id})
            
            # Analyze with LLM
            analysis_prompt = f"""
            Analyze this iMessage conversation flow:
            
            Thread ID: {thread_id}
            Messages: {messages}
            
            Provide:
            1. Conversation progression and key turning points
            2. Participant engagement levels
            3. Topic evolution
            4. Relationship dynamics
            5. Communication patterns
            """
            
            analysis = await self.process_with_llm(analysis_prompt)
            
            return ConfidenceResult(
                result={
                    "thread_id": thread_id,
                    "flow_analysis": analysis,
                    "message_count": len(messages.get("messages", []))
                },
                confidence=0.80,
                reasoning="LLM-powered conversation flow analysis"
            )
            
        except Exception as e:
            return ConfidenceResult(
                result={"error": str(e)},
                confidence=0.0,
                reasoning=f"Error in conversation flow analysis: {str(e)}"
            )