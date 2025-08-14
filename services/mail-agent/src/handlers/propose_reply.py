"""
Propose reply capability handler for mail messages.

This handler generates reply suggestions for mail messages.
"""

from typing import Dict, Any, List
from kenny_agent.base_handler import BaseCapabilityHandler


class ProposeReplyCapabilityHandler(BaseCapabilityHandler):
    """Handler for proposing reply suggestions."""
    
    def __init__(self):
        """Initialize the propose reply capability handler."""
        super().__init__(
            capability="messages.propose_reply",
            description="Generate reply suggestions for a message",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "context": {"type": "string"}
                },
                "required": ["id"],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "suggestions": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": ["suggestions"]
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the propose reply capability using the mail bridge tool and analysis.
        
        Args:
            parameters: Parameters containing message ID and context
            
        Returns:
            Reply suggestions based on message content
        """
        message_id = parameters.get("id")
        context = parameters.get("context", "")
        
        if not message_id:
            raise ValueError("Message ID is required")
        
        try:
            # Get the mail bridge tool from the agent
            if not hasattr(self, '_agent') or self._agent is None:
                # Fallback to mock data if no agent context
                return self._get_mock_reply_suggestions(context)
            
            mail_bridge_tool = self._agent.tools.get("mail_bridge")
            if not mail_bridge_tool:
                # Fallback to mock data if mail bridge tool not available
                return self._get_mock_reply_suggestions(context)
            
            # First, read the message to get its content
            read_result = await mail_bridge_tool.execute({
                "operation": "read_message",
                "id": message_id
            })
            
            if read_result.get("success") and "message" in read_result:
                message = read_result["message"]
                message_content = message.get("body_text", "")
                subject = message.get("headers", {}).get("subject", "")
                from_addr = message.get("headers", {}).get("from", "")
                
                # Generate contextual suggestions based on message content
                suggestions = self._generate_contextual_suggestions(
                    message_content, subject, from_addr, context
                )
                return {"suggestions": suggestions}
            else:
                # Fallback to mock data on bridge failure
                return self._get_mock_reply_suggestions(context)
                
        except Exception as e:
            # Fallback to mock data on any error
            return self._get_mock_reply_suggestions(context)
    
    def _generate_contextual_suggestions(
        self, 
        message_content: str, 
        subject: str, 
        from_addr: str, 
        context: str
    ) -> List[str]:
        """
        Generate contextual reply suggestions based on message content.
        
        Args:
            message_content: The body text of the message
            subject: The message subject
            from_addr: The sender's email address
            context: Additional context provided
            
        Returns:
            List of contextual reply suggestions
        """
        suggestions = []
        
        # Analyze message content for key patterns
        content_lower = message_content.lower()
        subject_lower = subject.lower()
        
        # Meeting-related
        if any(word in content_lower or word in subject_lower for word in ['meeting', 'call', 'schedule', 'available']):
            suggestions.extend([
                "Thank you for reaching out about scheduling. Let me check my availability and get back to you.",
                "I'd be happy to meet. Could you share a few times that work for you?",
                "Thanks for the meeting request. I'll review my calendar and propose some times."
            ])
        
        # Question-related
        elif any(word in content_lower for word in ['question', 'help', 'clarify', 'explain']):
            suggestions.extend([
                "Thank you for your question. Let me provide some clarification on this.",
                "I appreciate you reaching out for help. I'll be happy to explain this further.",
                "Thanks for your inquiry. Here's what I can share about this topic."
            ])
        
        # Thank you messages
        elif any(word in content_lower for word in ['thank', 'appreciate', 'grateful']):
            suggestions.extend([
                "You're very welcome! I'm glad I could help.",
                "I appreciate your kind words. It was my pleasure to assist.",
                "Thank you for your message. I'm happy to help anytime."
            ])
        
        # Project/work related
        elif any(word in content_lower for word in ['project', 'work', 'deadline', 'task']):
            suggestions.extend([
                "Thank you for the update on this project. I'll review and respond with my thoughts.",
                "I appreciate you keeping me informed about the project status.",
                "Thanks for reaching out about this. Let me review the details and get back to you."
            ])
        
        # Use context if provided
        if context:
            suggestions.insert(0, f"Thank you for your message about {context}. I appreciate you reaching out.")
        
        # Default suggestions if no specific patterns matched
        if not suggestions:
            suggestions = [
                "Thank you for your message. I appreciate you reaching out.",
                "I've received your message and will get back to you soon.",
                "Thanks for contacting me. I'll review this and respond in detail."
            ]
        
        # Limit to 3 suggestions
        return suggestions[:3]
    
    def _get_mock_reply_suggestions(self, context: str) -> Dict[str, Any]:
        """
        Generate mock reply suggestions as fallback.
        
        Args:
            context: Additional context for suggestions
            
        Returns:
            Mock reply suggestions
        """
        if context:
            suggestions = [
                f"Thank you for your message about {context}. I appreciate you reaching out.",
                f"Regarding {context}, I think we should discuss this further. Would you be available for a call?",
                f"I've reviewed your message about {context} and have some thoughts to share."
            ]
        else:
            suggestions = [
                "Thank you for your message. I appreciate you reaching out.",
                "I've received your message and will get back to you soon.",
                "Thanks for contacting me. I'll review this and respond in detail."
            ]
        
        return {"suggestions": suggestions}
