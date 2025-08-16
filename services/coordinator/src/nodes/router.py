import logging
import asyncio
from typing import Dict, Any, List, Optional
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

from ..model_router import ModelRouter
from ..benchmarking.performance_metrics import PerformanceMetrics

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Enhanced LLM-based intent classification with dynamic model routing"""
    
    def __init__(self, model_name: str = "llama3.2:3b"):
        # Initialize dynamic model router
        self.model_router = ModelRouter()
        
        # Performance metrics for monitoring
        self.performance_metrics = PerformanceMetrics()
        
        # Current model configuration
        self.default_model = model_name
        self.current_llm = None
        self.current_model_name = None
        self.llm_available = False
        
        # Initialize with default model
        self._initialize_model(model_name)
        
        self.agent_capabilities = {}
        
    def _initialize_model(self, model_name: str) -> None:
        """Initialize LLM with specified model"""
        try:
            self.current_llm = ChatOllama(
                model=model_name,
                temperature=0.1,
                base_url="http://localhost:11434"
            )
            self.current_model_name = model_name
            self.llm_available = True
            logger.info(f"Initialized intent classifier with model: {model_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize model {model_name}: {e}")
            self.current_llm = None
            self.current_model_name = None
            self.llm_available = False
    
    async def _switch_model_if_needed(self, query: str, context: Dict[str, Any]) -> bool:
        """Switch model based on dynamic routing decision"""
        try:
            # Get optimal model for this query
            selected_model, routing_info = await self.model_router.route_query(query, context)
            
            # Switch model if different from current
            if selected_model != self.current_model_name:
                logger.info(f"Switching model from {self.current_model_name} to {selected_model} for query complexity: {routing_info.get('complexity_analysis', {}).get('complexity', 'unknown')}")
                
                # Record model switch
                if self.current_model_name:
                    self.performance_metrics.record_model_switch(
                        from_model=self.current_model_name,
                        to_model=selected_model,
                        reason=routing_info.get('selection_reasoning', {}).get('reason', 'performance_optimization')
                    )
                
                self._initialize_model(selected_model)
                
                # Store routing info in context for performance tracking
                context['routing_info'] = routing_info
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Model switching failed: {e}")
            return False
        
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
            # Fallback to known capabilities with updated intelligent agent IDs
            self.agent_capabilities = {
                "intelligent-mail-agent": [
                    {"verb": "messages.search", "description": "Search mail messages with natural language queries"},
                    {"verb": "messages.read", "description": "Read mail messages with context"},
                    {"verb": "messages.propose_reply", "description": "Generate intelligent reply proposals"},
                    {"verb": "messages.analyze", "description": "Analyze email content and context"},
                    {"verb": "messages.categorize", "description": "Categorize emails intelligently"}
                ],
                "intelligent-contacts-agent": [
                    {"verb": "contacts.resolve", "description": "Find and resolve contacts with natural language"},
                    {"verb": "contacts.enrich", "description": "Enrich contact information cross-platform"},
                    {"verb": "contacts.merge", "description": "Merge duplicate contacts intelligently"}
                ],
                "intelligent-imessage-agent": [
                    {"verb": "messages.search", "description": "Search iMessages with natural language"},
                    {"verb": "messages.read", "description": "Read iMessage conversations"},
                    {"verb": "messages.analyze", "description": "Analyze message content and sentiment"},
                    {"verb": "conversations.summarize", "description": "Summarize conversation threads"}
                ],
                "intelligent-calendar-agent": [
                    {"verb": "calendar.read", "description": "Read calendar events"},
                    {"verb": "calendar.propose_event", "description": "Propose calendar events"},
                    {"verb": "calendar.smart_schedule", "description": "Schedule events with natural language"},
                    {"verb": "calendar.conflict_resolve", "description": "Resolve scheduling conflicts"}
                ],
                "memory-agent": [
                    {"verb": "memory.retrieve", "description": "Search stored memories"},
                    {"verb": "memory.store", "description": "Store new memories"},
                    {"verb": "memory.embed", "description": "Generate embeddings"}
                ]
            }
    
    async def classify_intent(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Classify user intent with dynamic model selection and performance tracking"""
        import time
        start_time = time.time()
        
        # Initialize context if not provided
        if context is None:
            context = {}
        
        # Dynamic model selection based on query complexity
        await self._switch_model_if_needed(user_input, context)
        
        # Use fallback if LLM is not available
        if not self.llm_available or self.current_llm is None:
            logger.info("Using fallback classification (LLM not available)")
            result = self._fallback_classification(user_input)
            
            # Record performance even for fallback
            routing_info = context.get('routing_info', {})
            request_id = routing_info.get('request_id')
            if request_id:
                response_time = time.time() - start_time
                self.model_router.record_performance(
                    request_id=request_id,
                    success=True,
                    response_time=response_time,
                    accuracy=0.6  # Fallback accuracy estimate
                )
            
            return result
        
        try:
            # Create capability description for the LLM
            capabilities_text = self._format_capabilities_for_llm()
            
            system_prompt = f"""You are an intelligent request router for Kenny v2.1, a multi-agent personal assistant with intelligent services.

Available intelligent agents and their capabilities:
{capabilities_text}

Your role is to interpret natural language queries flexibly and route them to appropriate agents. You should:

1. HANDLE IMPERFECT QUERIES: Make reasonable interpretations of vague, incomplete, or ambiguous requests
2. USE BEST-GUESS INTERPRETATION: When unsure, choose the most likely intent based on context
3. ENABLE CROSS-PLATFORM INTELLIGENCE: Consider how multiple agents can work together
4. PROVIDE CONFIDENCE SCORING: Indicate your certainty about the interpretation

For each request, determine:
- Primary intent category and confidence level
- Required agent(s) with specific capabilities
- Execution strategy and reasoning
- Fallback options for uncertain interpretations

Guidelines for handling imperfect queries:
- "find something about..." → Use best guess for search scope
- Missing details → Suggest most common/relevant defaults
- Ambiguous references → Interpret based on typical user patterns
- Unclear intent → Route to most capable agent for that domain

Respond in JSON format:
{{
    "primary_intent": "mail_operation|contacts_operation|messages_operation|calendar_operation|memory_operation|general_query",
    "confidence": 0.0-1.0,
    "interpretation": "Clear explanation of how you interpreted the query",
    "required_agents": [
        {{
            "agent_id": "agent_name",
            "capabilities": ["capability1", "capability2"],
            "priority": 1,
            "confidence": 0.0-1.0
        }}
    ],
    "execution_strategy": "single_agent|multi_agent|sequential",
    "fallback_options": ["alternative interpretation if primary fails"],
    "reasoning": "Detailed explanation of routing decision and interpretation choices"
}}"""

            human_prompt = f"User request: {user_input}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = await self.current_llm.ainvoke(messages)
            
            # Parse the JSON response, filtering out thinking blocks
            import json
            import re
            try:
                # Remove thinking blocks from the response
                cleaned_response = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()
                
                # Try to find JSON in the cleaned response
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    intent_data = json.loads(json_match.group())
                    
                    # Record successful performance
                    routing_info = context.get('routing_info', {})
                    request_id = routing_info.get('request_id')
                    if request_id:
                        response_time = time.time() - start_time
                        accuracy = intent_data.get('confidence', 0.8)  # Use confidence as accuracy estimate
                        self.model_router.record_performance(
                            request_id=request_id,
                            success=True,
                            response_time=response_time,
                            accuracy=accuracy
                        )
                    
                    return intent_data
                else:
                    # Fall back to parsing the entire cleaned response
                    intent_data = json.loads(cleaned_response)
                    
                    # Record successful performance
                    routing_info = context.get('routing_info', {})
                    request_id = routing_info.get('request_id')
                    if request_id:
                        response_time = time.time() - start_time
                        accuracy = intent_data.get('confidence', 0.8)
                        self.model_router.record_performance(
                            request_id=request_id,
                            success=True,
                            response_time=response_time,
                            accuracy=accuracy
                        )
                    
                    return intent_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse LLM response as JSON: {response.content}")
                
                # Record parsing failure
                routing_info = context.get('routing_info', {})
                request_id = routing_info.get('request_id')
                if request_id:
                    response_time = time.time() - start_time
                    self.model_router.record_performance(
                        request_id=request_id,
                        success=False,
                        response_time=response_time,
                        error="JSON parsing failed"
                    )
                
                return self._fallback_classification(user_input)
                
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            
            # Record classification failure
            routing_info = context.get('routing_info', {})
            request_id = routing_info.get('request_id')
            if request_id:
                response_time = time.time() - start_time
                self.model_router.record_performance(
                    request_id=request_id,
                    success=False,
                    response_time=response_time,
                    error=str(e)
                )
            
            return self._enhanced_fallback_classification(user_input)
    
    async def classify_with_best_guess(self, user_input: str, min_confidence: float = 0.3, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Enhanced classification with best-guess interpretation for imperfect queries."""
        try:
            # First attempt standard classification
            result = await self.classify_intent(user_input, context)
            
            # If confidence is too low, attempt best-guess interpretation
            if result.get("confidence", 0) < min_confidence:
                print(f"Low confidence ({result.get('confidence', 0):.2f}), attempting best-guess interpretation...")
                return await self._best_guess_interpretation(user_input, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Best-guess classification failed: {e}")
            return self._enhanced_fallback_classification(user_input)
    
    async def _best_guess_interpretation(self, user_input: str, initial_result: Dict[str, Any]) -> Dict[str, Any]:
        """Perform best-guess interpretation for ambiguous queries."""
        if not self.llm_available or self.current_llm is None:
            return self._enhanced_fallback_classification(user_input)
        
        try:
            # Create a more flexible prompt for ambiguous queries
            system_prompt = f"""You are an expert at interpreting ambiguous user requests for Kenny v2.1.

Your task is to make the BEST POSSIBLE GUESS about what the user wants, even if the request is:
- Incomplete or vague
- Has typos or grammar errors  
- Uses informal language
- References unclear entities
- Has missing context

Available intelligent agents:
{self._format_capabilities_for_llm()}

For ambiguous queries, use these interpretation strategies:
1. ASSUME MOST COMMON INTENT: Choose the most likely interpretation based on typical user patterns
2. DEFAULT TO BROAD SEARCH: When in doubt, prefer search operations over specific actions
3. INFER MISSING DETAILS: Fill in reasonable defaults for missing information
4. PREFER RECENT DATA: When timeframes are unclear, assume recent/current data
5. MULTI-AGENT APPROACH: Consider using multiple agents for comprehensive results

Previous classification attempt:
{initial_result}

Respond with your best guess interpretation in JSON format:
{{
    "primary_intent": "mail_operation|contacts_operation|messages_operation|calendar_operation|memory_operation|general_query",
    "confidence": 0.4-0.8,
    "interpretation": "Clear explanation of your best guess interpretation",
    "required_agents": [
        {{
            "agent_id": "agent_name",
            "capabilities": ["capability1"],
            "priority": 1,
            "confidence": 0.4-0.8
        }}
    ],
    "execution_strategy": "single_agent|multi_agent|sequential",
    "best_guess_reasoning": "Detailed explanation of why this is your best guess",
    "fallback_options": ["alternative interpretations if this fails"],
    "assumed_defaults": {{"parameter": "default_value"}},
    "confidence_factors": ["factors that increase/decrease confidence"]
}}"""

            human_prompt = f"User request (ambiguous/unclear): {user_input}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            
            response = await self.current_llm.ainvoke(messages)
            
            # Parse the JSON response
            import json
            import re
            try:
                cleaned_response = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()
                json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                    # Ensure confidence is marked as best-guess
                    result["is_best_guess"] = True
                    result["original_confidence"] = initial_result.get("confidence", 0)
                    return result
                else:
                    return self._enhanced_fallback_classification(user_input)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse best-guess LLM response: {response.content}")
                return self._enhanced_fallback_classification(user_input)
                
        except Exception as e:
            logger.error(f"Best-guess interpretation failed: {e}")
            return self._enhanced_fallback_classification(user_input)
    
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
    
    def _enhanced_fallback_classification(self, user_input: str) -> Dict[str, Any]:
        """Enhanced fallback classification with better best-guess capabilities."""
        user_input_lower = user_input.lower()
        
        # Enhanced keyword mapping with confidence scoring
        keyword_mappings = {
            "mail_operation": {
                "keywords": ["mail", "email", "inbox", "send", "message", "envelope"],
                "confidence": 0.7,
                "agent": "intelligent-mail-agent",
                "capability": "messages.search"
            },
            "contacts_operation": {
                "keywords": ["contact", "person", "phone", "address", "name", "who"],
                "confidence": 0.7,
                "agent": "intelligent-contacts-agent", 
                "capability": "contacts.resolve"
            },
            "messages_operation": {
                "keywords": ["message", "text", "imessage", "chat", "conversation"],
                "confidence": 0.7,
                "agent": "intelligent-imessage-agent",
                "capability": "messages.search"
            },
            "calendar_operation": {
                "keywords": ["calendar", "schedule", "meeting", "event", "appointment", "when"],
                "confidence": 0.7,
                "agent": "intelligent-calendar-agent",
                "capability": "calendar.read"
            },
            "memory_operation": {
                "keywords": ["remember", "recall", "memory", "store", "save"],
                "confidence": 0.7,
                "agent": "memory-agent",
                "capability": "memory.retrieve"
            }
        }
        
        # Search action keywords that boost confidence
        search_keywords = ["find", "search", "get", "show", "recent", "latest", "check", "list"]
        
        # Question words that suggest search/retrieval
        question_words = ["what", "where", "when", "who", "how", "which"]
        
        # Best match tracking
        best_match = None
        best_score = 0
        
        for intent, mapping in keyword_mappings.items():
            score = 0
            keyword_matches = 0
            
            # Count keyword matches
            for keyword in mapping["keywords"]:
                if keyword in user_input_lower:
                    keyword_matches += 1
                    score += 1
            
            # Boost score for search-related terms
            for search_keyword in search_keywords:
                if search_keyword in user_input_lower:
                    score += 0.5
            
            # Boost score for question words (suggests search/retrieval)
            for question_word in question_words:
                if question_word in user_input_lower:
                    score += 0.3
            
            # Calculate confidence based on score and input length
            if keyword_matches > 0:
                word_count = len(user_input_lower.split())
                confidence = min(0.8, mapping["confidence"] * (score / max(word_count * 0.5, 1)))
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        "intent": intent,
                        "confidence": confidence,
                        "agent": mapping["agent"],
                        "capability": mapping["capability"],
                        "keyword_matches": keyword_matches,
                        "score": score
                    }
        
        # If we found a match, return it
        if best_match:
            return {
                "primary_intent": best_match["intent"],
                "confidence": best_match["confidence"],
                "interpretation": f"Best-guess interpretation based on keywords: {best_match['keyword_matches']} matches found",
                "required_agents": [
                    {
                        "agent_id": best_match["agent"],
                        "capabilities": [best_match["capability"]],
                        "priority": 1,
                        "confidence": best_match["confidence"]
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": ["Try multi-agent search if primary agent fails"],
                "reasoning": f"Enhanced fallback classification with score {best_match['score']:.1f}",
                "is_fallback": True
            }
        
        # Ultimate fallback - try to be smart about it
        if any(word in user_input_lower for word in search_keywords + question_words):
            # This looks like a search query, default to mail agent (most common)
            return {
                "primary_intent": "mail_operation",
                "confidence": 0.4,
                "interpretation": "Fallback interpretation: detected search intent, defaulting to mail search",
                "required_agents": [
                    {
                        "agent_id": "intelligent-mail-agent",
                        "capabilities": ["messages.search"],
                        "priority": 1,
                        "confidence": 0.4
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": [
                    "Try contacts agent if no mail results found",
                    "Try imessage agent for conversation search",
                    "Try calendar agent for event search"
                ],
                "reasoning": "Ultimate fallback: detected search intent, trying mail agent first",
                "is_fallback": True,
                "is_ultimate_fallback": True
            }
        
        # Very last resort - conversational
        return {
            "primary_intent": "conversational_query",
            "confidence": 0.3,
            "interpretation": "No clear intent detected, treating as conversational query",
            "required_agents": [],
            "execution_strategy": "single_agent",
            "fallback_options": ["Ask user to clarify their request"],
            "reasoning": "No keywords matched, defaulting to conversational response",
            "is_fallback": True,
            "is_ultimate_fallback": True
        }

    def _fallback_classification(self, user_input: str) -> Dict[str, Any]:
        """Fallback classification using keyword matching"""
        user_input_lower = user_input.lower()
        
        # First check for conversational queries that should use Ollama
        conversational_patterns = [
            # Questions about Kenny's capabilities
            ["what", "can", "you", "do"],
            ["what", "are", "you"],
            ["who", "are", "you"], 
            ["what", "tools"],
            ["what", "capabilities"],
            ["help", "me"],
            ["how", "can", "you", "help"],
            
            # General greetings and conversation
            ["hello", "hi", "hey"],
            ["good", "morning"],
            ["good", "afternoon"], 
            ["how", "are", "you"],
            ["thanks", "thank", "you"],
            
            # General questions
            ["tell", "me", "about"],
            ["explain"],
            ["what", "is"],
            ["how", "do", "i"],
        ]
        
        # Check if input matches pure conversational patterns only
        for pattern in conversational_patterns:
            # Create phrase from pattern words
            phrase = " ".join(pattern)
            if phrase in user_input_lower:
                # Strong check: ensure it's not asking about data/operations
                if not any(word in user_input_lower for word in ["email", "mail", "contact", "calendar", "meeting", "message", "search", "find", "get", "show", "recent", "latest", "check"]):
                    return {
                        "primary_intent": "conversational_query",
                        "confidence": 0.8,
                        "required_agents": [],
                        "execution_strategy": "single_agent",
                        "reasoning": f"Pure conversational query: matches pattern {pattern}"
                    }
        
        # Check for specific agent operations
        if any(word in user_input_lower for word in ["mail", "email", "inbox", "send"]) and not any(word in user_input_lower for word in ["what", "how", "can", "tell", "explain"]):
            return {
                "primary_intent": "mail_operation",
                "confidence": 0.7,
                "interpretation": "Detected mail-related keywords, routing to intelligent mail agent",
                "required_agents": [
                    {
                        "agent_id": "intelligent-mail-agent",
                        "capabilities": ["messages.search"],
                        "priority": 1,
                        "confidence": 0.8
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": ["Try contact search if no mail results found"],
                "reasoning": "Keyword-based fallback classification for mail operations"
            }
        elif any(word in user_input_lower for word in ["contact", "person", "phone", "address"]) and not any(word in user_input_lower for word in ["what", "how", "can", "tell", "explain"]):
            return {
                "primary_intent": "contacts_operation", 
                "confidence": 0.7,
                "interpretation": "Detected contact-related keywords, routing to intelligent contacts agent",
                "required_agents": [
                    {
                        "agent_id": "intelligent-contacts-agent",
                        "capabilities": ["contacts.resolve"],
                        "priority": 1,
                        "confidence": 0.8
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": ["Search across mail and messages if no direct contact found"],
                "reasoning": "Keyword-based fallback classification for contact operations"
            }
        elif any(word in user_input_lower for word in ["message", "text", "imessage", "chat"]) and not any(word in user_input_lower for word in ["what", "how", "can", "tell", "explain"]):
            return {
                "primary_intent": "messages_operation",
                "confidence": 0.7,
                "interpretation": "Detected messaging keywords, routing to intelligent iMessage agent",
                "required_agents": [
                    {
                        "agent_id": "intelligent-imessage-agent",
                        "capabilities": ["messages.search"],
                        "priority": 1,
                        "confidence": 0.8
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": ["Try contact search if no messages found"],
                "reasoning": "Keyword-based fallback classification for messaging operations"
            }
        elif any(word in user_input_lower for word in ["calendar", "schedule", "meeting", "event", "appointment"]) and not any(word in user_input_lower for word in ["what", "how", "can", "tell", "explain"]):
            return {
                "primary_intent": "calendar_operation",
                "confidence": 0.7,
                "interpretation": "Detected calendar keywords, routing to intelligent calendar agent",
                "required_agents": [
                    {
                        "agent_id": "intelligent-calendar-agent",
                        "capabilities": ["calendar.read"],
                        "priority": 1,
                        "confidence": 0.8
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": ["Check contacts for participant information"],
                "reasoning": "Keyword-based fallback classification for calendar operations"
            }
        elif any(word in user_input_lower for word in ["remember", "recall", "memory", "store"]) and not any(word in user_input_lower for word in ["what", "how", "can", "tell", "explain"]):
            return {
                "primary_intent": "memory_operation",
                "confidence": 0.7,
                "interpretation": "Detected memory keywords, routing to memory agent",
                "required_agents": [
                    {
                        "agent_id": "memory-agent", 
                        "capabilities": ["memory.retrieve"],
                        "priority": 1,
                        "confidence": 0.8
                    }
                ],
                "execution_strategy": "single_agent",
                "fallback_options": ["Search across other agents if no memories found"],
                "reasoning": "Keyword-based fallback classification for memory operations"
            }
        else:
            # Default to conversational for everything else
            return {
                "primary_intent": "conversational_query",
                "confidence": 0.6,
                "required_agents": [],
                "execution_strategy": "single_agent",
                "reasoning": "Default fallback to conversational query"
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
            
            # Classify intent using enhanced LLM with best-guess capabilities
            # Pass context for dynamic model routing
            routing_context = {
                'user_input': state['user_input'],
                'execution_path': state.get('execution_path', []),
                'previous_context': state.get('context', {})
            }
            intent_result = await self.classifier.classify_with_best_guess(state['user_input'], min_confidence=0.5, context=routing_context)
            
            # Store routing information in context
            state['context']['intent'] = intent_result['primary_intent']
            state['context']['confidence'] = intent_result['confidence'] 
            state['context']['interpretation'] = intent_result.get('interpretation', 'No interpretation provided')
            state['context']['required_agents'] = intent_result['required_agents']
            state['context']['execution_strategy'] = intent_result['execution_strategy']
            state['context']['fallback_options'] = intent_result.get('fallback_options', [])
            state['context']['routing_reasoning'] = intent_result.get('reasoning', 'No reasoning provided')
            
            # Store enhanced best-guess context
            state['context']['is_best_guess'] = intent_result.get('is_best_guess', False)
            state['context']['is_fallback'] = intent_result.get('is_fallback', False)
            state['context']['original_confidence'] = intent_result.get('original_confidence')
            state['context']['best_guess_reasoning'] = intent_result.get('best_guess_reasoning')
            state['context']['assumed_defaults'] = intent_result.get('assumed_defaults', {})
            state['context']['confidence_factors'] = intent_result.get('confidence_factors', [])
            
            # Enhanced logging with best-guess information
            log_msg = f"Intent classified as: {intent_result['primary_intent']} (confidence: {intent_result['confidence']:.2f})"
            if intent_result.get('is_best_guess'):
                log_msg += " [BEST-GUESS]"
            if intent_result.get('is_fallback'):
                log_msg += " [FALLBACK]"
            logger.info(log_msg)
            
        except Exception as e:
            logger.error(f"Error in routing: {e}")
            state['errors'].append(f"Routing error: {str(e)}")
            # Use fallback routing
            state['context']['intent'] = "general_query"
            state['context']['confidence'] = 0.3
            state['context']['required_agents'] = []
            state['context']['execution_strategy'] = "single_agent"
        
        return state
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics for monitoring"""
        snapshot = self.classifier.performance_metrics.get_current_snapshot()
        model_comparison = self.classifier.model_router.get_model_comparison()
        
        return {
            "current_model": self.classifier.current_model_name,
            "performance_snapshot": {
                "avg_response_time": snapshot.avg_response_time,
                "success_rate": snapshot.success_rate,
                "cache_hit_rate": snapshot.cache_hit_rate,
                "total_requests": snapshot.total_requests,
                "p95_response_time": snapshot.p95_response_time
            },
            "model_comparison": model_comparison,
            "performance_degraded": self.classifier.performance_metrics.is_performance_degraded()
        }
    
    def start_ab_test(self, control_model: str, treatment_model: str, test_name: str = "router_ab_test") -> str:
        """Start an A/B test for model comparison"""
        return self.classifier.model_router.start_ab_test(control_model, treatment_model, test_name)
    
    def get_ab_test_status(self) -> List[Dict[str, Any]]:
        """Get status of active A/B tests"""
        return self.classifier.model_router.ab_testing.get_active_tests()
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report"""
        router_metrics = self.get_performance_metrics()
        base_report = self.classifier.model_router.get_performance_report()
        
        # Add router-specific information
        router_section = f"""\n=== ROUTER PERFORMANCE ==="
Current Model: {router_metrics['current_model']}
Model Switches: Tracked via ModelRouter
Capabilities Loaded: {self._capabilities_loaded}

=== MODEL COMPARISON ==="
        for model, metrics in router_metrics['model_comparison'].items():
            model_section = f"{model}:\n  Avg Response Time: {metrics['avg_response_time']:.2f}s\n  Success Rate: {metrics['success_rate']:.1%}\n  Total Requests: {metrics['total_requests']}\n"
        
        return base_report + router_section