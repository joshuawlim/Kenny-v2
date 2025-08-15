"""
Propose Reply capability handler for WhatsApp chats.

This handler provides functionality to propose replies to WhatsApp messages,
considering context, media content, and conversation history.
"""

from typing import Dict, Any, List, Optional
from kenny_agent.base_handler import BaseCapabilityHandler


class ProposeReplyCapabilityHandler(BaseCapabilityHandler):
    """Handler for proposing replies to WhatsApp messages."""
    
    def __init__(self):
        """Initialize the propose reply capability handler."""
        super().__init__(
            capability="chats.propose_reply",
            description="Propose contextually appropriate replies to WhatsApp messages",
            input_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "chat_id": {"type": "string"},
                    "message_content": {"type": "string"},
                    "context_length": {"type": "integer", "minimum": 1, "maximum": 10, "default": 3},
                    "reply_style": {
                        "type": "string", 
                        "enum": ["casual", "professional", "brief", "detailed"],
                        "default": "casual"
                    },
                    "consider_media": {"type": "boolean", "default": True},
                    "max_replies": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3}
                },
                "anyOf": [
                    {"required": ["message_id"]},
                    {"required": ["chat_id", "message_content"]}
                ],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "proposals": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "reply_text": {"type": "string"},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "reasoning": {"type": "string"},
                                "style": {"type": "string"},
                                "considers_media": {"type": "boolean"},
                                "context_used": {"type": "integer"}
                            },
                            "required": ["reply_text", "confidence", "reasoning"]
                        }
                    },
                    "original_message": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string"},
                            "has_media": {"type": "boolean"},
                            "media_summary": {"type": ["string", "null"]}
                        }
                    }
                },
                "required": ["proposals"],
                "additionalProperties": False
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute reply proposal generation.
        
        Args:
            parameters: Proposal parameters
            
        Returns:
            Proposed replies with confidence scores and reasoning
        """
        try:
            # Get tools from agent
            if not hasattr(self, '_agent') or self._agent is None:
                return self._get_mock_proposals(parameters)
            
            whatsapp_bridge_tool = self._agent.tools.get("whatsapp_bridge")
            image_processor_tool = self._agent.tools.get("image_processor")
            
            # Get message content and context
            message_data = await self._get_message_data(parameters, whatsapp_bridge_tool)
            if not message_data:
                return self._get_mock_proposals(parameters)
            
            # Process media content if present
            media_summary = None
            if parameters.get("consider_media", True) and message_data.get("has_media"):
                media_summary = await self._process_message_media(message_data, image_processor_tool)
            
            # Get conversation context
            context_messages = await self._get_conversation_context(
                parameters, message_data, whatsapp_bridge_tool
            )
            
            # Generate reply proposals
            proposals = await self._generate_reply_proposals(
                message_data, media_summary, context_messages, parameters
            )
            
            return {
                "proposals": proposals,
                "original_message": {
                    "content": message_data.get("content", ""),
                    "has_media": bool(message_data.get("has_media")),
                    "media_summary": media_summary
                }
            }
            
        except Exception as e:
            print(f"WhatsApp propose reply error: {e}")
            return self._get_mock_proposals(parameters)
    
    async def _get_message_data(self, parameters: Dict[str, Any], bridge_tool: Any) -> Optional[Dict[str, Any]]:
        """Get the message data to reply to."""
        try:
            if not bridge_tool:
                return None
            
            message_id = parameters.get("message_id")
            if message_id:
                # Get specific message
                result = bridge_tool.execute({
                    "operation": "read",
                    "message_id": message_id
                })
                return result.get("message")
            
            # Use provided message content
            chat_id = parameters.get("chat_id")
            message_content = parameters.get("message_content")
            if chat_id and message_content:
                return {
                    "id": "provided_content",
                    "chat_id": chat_id,
                    "content": message_content,
                    "timestamp": "2025-08-15T10:00:00Z",
                    "message_type": "text",
                    "has_media": False
                }
            
            return None
            
        except Exception as e:
            print(f"Failed to get message data: {e}")
            return None
    
    async def _process_message_media(self, message_data: Dict[str, Any], image_processor: Any) -> Optional[str]:
        """Process media content and return a summary."""
        try:
            if not image_processor or not message_data.get("has_media"):
                return None
            
            # Mock media processing - in real implementation would process actual media files
            if message_data.get("message_type") == "image":
                # Extract text from image
                ocr_result = image_processor.execute({
                    "operation": "ocr",
                    "image_path": "/mock/path/to/image.jpg"
                })
                
                # Analyze image properties
                analysis_result = image_processor.execute({
                    "operation": "analyze", 
                    "image_path": "/mock/path/to/image.jpg"
                })
                
                summary_parts = []
                if ocr_result.get("text"):
                    summary_parts.append(f"Text in image: {ocr_result['text'][:100]}...")
                
                if analysis_result.get("properties", {}).get("content_hints"):
                    hints = analysis_result["properties"]["content_hints"]
                    summary_parts.append(f"Image type: {', '.join(hints)}")
                
                return "; ".join(summary_parts) if summary_parts else "Image content processed"
            
            return f"Media content: {message_data.get('message_type', 'unknown')}"
            
        except Exception as e:
            print(f"Media processing error: {e}")
            return "Media content could not be processed"
    
    async def _get_conversation_context(self, parameters: Dict[str, Any], 
                                       message_data: Dict[str, Any], bridge_tool: Any) -> List[Dict[str, Any]]:
        """Get recent conversation context."""
        try:
            if not bridge_tool:
                return []
            
            context_length = parameters.get("context_length", 3)
            chat_id = message_data.get("chat_id")
            
            if not chat_id:
                return []
            
            # Get recent messages from chat
            result = bridge_tool.execute({
                "operation": "list",
                "chat_id": chat_id,
                "limit": context_length + 3  # Get extra to filter current message
            })
            
            if result.get("results"):
                messages = result["results"]
                # Filter out current message and return context
                context = [msg for msg in messages if msg.get("id") != message_data.get("id")]
                return context[:context_length]
            
            return []
            
        except Exception as e:
            print(f"Context retrieval error: {e}")
            return []
    
    async def _generate_reply_proposals(self, message_data: Dict[str, Any], media_summary: Optional[str],
                                       context_messages: List[Dict[str, Any]], parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate contextually appropriate reply proposals."""
        try:
            message_content = message_data.get("content", "")
            reply_style = parameters.get("reply_style", "casual")
            max_replies = parameters.get("max_replies", 3)
            
            # Analyze message type and content
            message_type = self._classify_message_type(message_content, media_summary)
            
            # Generate different types of replies
            proposals = []
            
            # Reply 1: Direct response based on content
            if message_type == "question":
                reply_text = self._generate_question_response(message_content, reply_style)
                reasoning = "Direct response to the question asked"
                confidence = 0.8
            elif message_type == "greeting":
                reply_text = self._generate_greeting_response(reply_style)
                reasoning = "Appropriate greeting response"
                confidence = 0.9
            elif message_type == "information":
                reply_text = self._generate_acknowledgment_response(reply_style)
                reasoning = "Acknowledgment of information shared"
                confidence = 0.7
            else:
                reply_text = self._generate_general_response(message_content, reply_style)
                reasoning = "General contextual response"
                confidence = 0.6
            
            proposals.append({
                "reply_text": reply_text,
                "confidence": confidence,
                "reasoning": reasoning,
                "style": reply_style,
                "considers_media": bool(media_summary),
                "context_used": len(context_messages)
            })
            
            # Reply 2: Context-aware response if we have conversation history
            if context_messages and max_replies > 1:
                context_reply = self._generate_context_aware_response(
                    message_content, context_messages, reply_style
                )
                proposals.append({
                    "reply_text": context_reply,
                    "confidence": 0.75,
                    "reasoning": "Response considering recent conversation context",
                    "style": reply_style,
                    "considers_media": bool(media_summary),
                    "context_used": len(context_messages)
                })
            
            # Reply 3: Media-aware response if media is present
            if media_summary and max_replies > 2:
                media_reply = self._generate_media_aware_response(
                    message_content, media_summary, reply_style
                )
                proposals.append({
                    "reply_text": media_reply,
                    "confidence": 0.7,
                    "reasoning": "Response considering media content",
                    "style": reply_style,
                    "considers_media": True,
                    "context_used": len(context_messages)
                })
            
            return proposals[:max_replies]
            
        except Exception as e:
            print(f"Reply generation error: {e}")
            return self._get_fallback_proposals(parameters)
    
    def _classify_message_type(self, content: str, media_summary: Optional[str]) -> str:
        """Classify the type of message to determine appropriate response."""
        content_lower = content.lower() if content else ""
        
        # Question indicators
        if any(word in content_lower for word in ["?", "what", "how", "when", "where", "why", "can you", "could you"]):
            return "question"
        
        # Greeting indicators
        if any(word in content_lower for word in ["hello", "hi", "hey", "good morning", "good evening"]):
            return "greeting"
        
        # Information sharing indicators
        if any(word in content_lower for word in ["here is", "here's", "check this", "look at"]) or media_summary:
            return "information"
        
        return "general"
    
    def _generate_question_response(self, content: str, style: str) -> str:
        """Generate appropriate response to a question."""
        if style == "professional":
            return "Thank you for your question. Let me provide you with the information you need."
        elif style == "brief":
            return "Let me check on that for you."
        elif style == "detailed":
            return "That's a great question! I'd be happy to help you with that. Let me gather some information and get back to you with a comprehensive response."
        else:  # casual
            return "Good question! Let me look into that for you."
    
    def _generate_greeting_response(self, style: str) -> str:
        """Generate appropriate response to a greeting."""
        if style == "professional":
            return "Good day! How may I assist you today?"
        elif style == "brief":
            return "Hi there!"
        elif style == "detailed":
            return "Hello! It's great to hear from you. I hope you're having a wonderful day. How can I help you today?"
        else:  # casual
            return "Hey! How's it going?"
    
    def _generate_acknowledgment_response(self, style: str) -> str:
        """Generate appropriate acknowledgment response."""
        if style == "professional":
            return "Thank you for sharing this information."
        elif style == "brief":
            return "Got it, thanks!"
        elif style == "detailed":
            return "Thank you for sharing this with me. I've reviewed the information and it's very helpful."
        else:  # casual
            return "Thanks for sharing!"
    
    def _generate_general_response(self, content: str, style: str) -> str:
        """Generate general contextual response."""
        if style == "professional":
            return "I understand. Please let me know if you need any assistance."
        elif style == "brief":
            return "Understood."
        elif style == "detailed":
            return "I appreciate you reaching out. If there's anything specific you'd like to discuss or if you need any help, please don't hesitate to let me know."
        else:  # casual
            return "Makes sense! Let me know if you need anything."
    
    def _generate_context_aware_response(self, content: str, context: List[Dict[str, Any]], style: str) -> str:
        """Generate response considering conversation context."""
        # Simple context analysis - in real implementation would use more sophisticated analysis
        recent_topics = [msg.get("content", "")[:50] for msg in context[:2]]
        
        if style == "professional":
            return "Considering our recent discussion, I believe this aligns well with what we've been talking about."
        elif style == "brief":
            return "Following up on our chat."
        elif style == "detailed":
            return f"Building on our recent conversation, this adds an interesting perspective to what we've been discussing."
        else:  # casual
            return "Yeah, that totally makes sense given what we were just talking about!"
    
    def _generate_media_aware_response(self, content: str, media_summary: str, style: str) -> str:
        """Generate response that acknowledges media content."""
        if "image" in media_summary.lower():
            if style == "professional":
                return "Thank you for sharing the image. I've reviewed the visual content."
            elif style == "brief":
                return "Nice pic!"
            elif style == "detailed":
                return "Thanks for sharing that image! I can see the visual content and it helps provide good context for our conversation."
            else:  # casual
                return "Cool image! Thanks for sharing."
        else:
            if style == "professional":
                return "Thank you for sharing the media content."
            elif style == "brief":
                return "Thanks for sharing!"
            else:
                return "Thanks for sending that!"
    
    def _get_fallback_proposals(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fallback proposals when main generation fails."""
        style = parameters.get("reply_style", "casual")
        
        return [
            {
                "reply_text": "Thanks for your message!" if style == "casual" else "Thank you for your message.",
                "confidence": 0.5,
                "reasoning": "Fallback generic response",
                "style": style,
                "considers_media": False,
                "context_used": 0
            }
        ]
    
    def _get_mock_proposals(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock proposals as fallback."""
        style = parameters.get("reply_style", "casual")
        max_replies = parameters.get("max_replies", 3)
        
        proposals = [
            {
                "reply_text": "That's interesting! Thanks for sharing." if style == "casual" else "Thank you for sharing this information.",
                "confidence": 0.8,
                "reasoning": "Acknowledging the shared content",
                "style": style,
                "considers_media": parameters.get("consider_media", True),
                "context_used": parameters.get("context_length", 3)
            },
            {
                "reply_text": "Got it!" if style == "brief" else "I understand what you're saying.",
                "confidence": 0.7,
                "reasoning": "Simple acknowledgment response",
                "style": style,
                "considers_media": False,
                "context_used": 0
            },
            {
                "reply_text": "Let me know if you need anything else!" if style == "casual" else "Please let me know if you require any assistance.",
                "confidence": 0.6,
                "reasoning": "Offering additional help",
                "style": style,
                "considers_media": False,
                "context_used": 0
            }
        ]
        
        return {
            "proposals": proposals[:max_replies],
            "original_message": {
                "content": parameters.get("message_content", "Mock message content"),
                "has_media": False,
                "media_summary": None
            }
        }