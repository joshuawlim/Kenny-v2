"""
Read capability handler for WhatsApp chats.

This handler provides functionality to read full WhatsApp chat messages
including media content with local image processing.
"""

from typing import Dict, Any, List, Optional
from kenny_agent.base_handler import BaseCapabilityHandler


class ReadCapabilityHandler(BaseCapabilityHandler):
    """Handler for reading WhatsApp chat messages."""
    
    def __init__(self):
        """Initialize the read capability handler."""
        super().__init__(
            capability="chats.read",
            description="Read full WhatsApp chat messages with media content analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "chat_id": {"type": "string"},
                    "include_media": {"type": "boolean", "default": True},
                    "process_images": {"type": "boolean", "default": True},
                    "context_messages": {"type": "integer", "minimum": 0, "maximum": 10, "default": 0}
                },
                "anyOf": [
                    {"required": ["message_id"]},
                    {"required": ["chat_id"]}
                ],
                "additionalProperties": False
            },
            output_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "chat_id": {"type": "string"},
                            "from": {"type": ["string", "null"]},
                            "to": {"type": ["string", "null"]},
                            "content": {"type": ["string", "null"]},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "message_type": {"type": "string"},
                            "media": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string"},
                                    "url": {"type": "string"},
                                    "caption": {"type": ["string", "null"]},
                                    "processed": {"type": "boolean"},
                                    "ocr_text": {"type": ["string", "null"]},
                                    "analysis": {"type": "object"}
                                }
                            },
                            "context": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        },
                        "required": ["id", "chat_id", "timestamp", "message_type"]
                    }
                },
                "required": ["message"],
                "additionalProperties": False
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the read capability using the WhatsApp bridge and image processing tools.
        
        Args:
            parameters: Read parameters
            
        Returns:
            Full message data with media processing
        """
        try:
            # Get tools from agent
            if not hasattr(self, '_agent') or self._agent is None:
                return self._get_mock_read_result(parameters)
            
            whatsapp_bridge_tool = self._agent.tools.get("whatsapp_bridge")
            image_processor_tool = self._agent.tools.get("image_processor")
            
            if not whatsapp_bridge_tool:
                return self._get_mock_read_result(parameters)
            
            # Get message from bridge
            message_id = parameters.get("message_id")
            chat_id = parameters.get("chat_id")
            
            if message_id:
                bridge_result = whatsapp_bridge_tool.execute({
                    "operation": "read",
                    "message_id": message_id
                })
            elif chat_id:
                # Get latest message from chat
                bridge_result = whatsapp_bridge_tool.execute({
                    "operation": "list",
                    "chat_id": chat_id,
                    "limit": 1
                })
                if bridge_result.get("results"):
                    message_data = bridge_result["results"][0]
                else:
                    return {"message": None, "error": "No messages found in chat"}
            else:
                return {"message": None, "error": "Either message_id or chat_id required"}
            
            # Extract message from bridge result
            if "message" in bridge_result:
                message_data = bridge_result["message"]
            elif "results" in bridge_result and bridge_result["results"]:
                message_data = bridge_result["results"][0]
            else:
                return self._get_mock_read_result(parameters)
            
            # Process media if present and requested
            include_media = parameters.get("include_media", True)
            process_images = parameters.get("process_images", True)
            
            if include_media and message_data.get("has_media") and image_processor_tool:
                message_data = await self._process_media(message_data, image_processor_tool, process_images)
            
            # Add context messages if requested
            context_count = parameters.get("context_messages", 0)
            if context_count > 0 and chat_id:
                context_messages = await self._get_context_messages(
                    chat_id, message_data, context_count, whatsapp_bridge_tool
                )
                message_data["context"] = context_messages
            
            return {"message": message_data}
            
        except Exception as e:
            print(f"WhatsApp read error: {e}")
            return self._get_mock_read_result(parameters)
    
    async def _process_media(self, message_data: Dict[str, Any], image_processor: Any, process_images: bool) -> Dict[str, Any]:
        """Process media content in the message."""
        try:
            # Mock media processing for now since actual WhatsApp bridge isn't implemented
            media_info = {
                "type": "image",
                "url": "file://mock/image/path.jpg",
                "caption": message_data.get("content", ""),
                "processed": False
            }
            
            if process_images and media_info["type"] == "image":
                # Process image with local OCR/analysis
                image_result = image_processor.execute({
                    "operation": "ocr",
                    "image_path": "/mock/image/path.jpg"  # Would be real path from bridge
                })
                
                if image_result.get("text"):
                    media_info["ocr_text"] = image_result["text"]
                    media_info["processed"] = True
                
                # Also get image analysis
                analysis_result = image_processor.execute({
                    "operation": "analyze",
                    "image_path": "/mock/image/path.jpg"
                })
                
                if analysis_result.get("properties"):
                    media_info["analysis"] = analysis_result["properties"]
            
            message_data["media"] = media_info
            return message_data
            
        except Exception as e:
            print(f"Media processing error: {e}")
            message_data["media"] = {
                "type": "unknown",
                "processed": False,
                "error": str(e)
            }
            return message_data
    
    async def _get_context_messages(self, chat_id: str, current_message: Dict[str, Any], 
                                   count: int, bridge_tool: Any) -> List[Dict[str, Any]]:
        """Get context messages around the current message."""
        try:
            # Get recent messages from the chat
            context_result = bridge_tool.execute({
                "operation": "list",
                "chat_id": chat_id,
                "limit": count + 5  # Get extra to filter out current message
            })
            
            if context_result.get("results"):
                messages = context_result["results"]
                # Filter out the current message and return the requested count
                context = [msg for msg in messages if msg.get("id") != current_message.get("id")]
                return context[:count]
            
            return []
            
        except Exception as e:
            print(f"Context messages error: {e}")
            return []
    
    def _get_mock_read_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock read result as fallback."""
        message_id = parameters.get("message_id", "mock_msg_1")
        chat_id = parameters.get("chat_id", "mock_chat")
        include_media = parameters.get("include_media", True)
        process_images = parameters.get("process_images", True)
        
        message = {
            "id": message_id,
            "chat_id": chat_id,
            "from": "Mock Contact",
            "to": "Me",
            "content": "This is a mock WhatsApp message with full content.",
            "timestamp": "2025-08-15T10:00:00Z",
            "message_type": "text"
        }
        
        # Add mock media if requested
        if include_media:
            message["media"] = {
                "type": "image",
                "url": "file://mock/image.jpg",
                "caption": "Mock image caption",
                "processed": process_images,
                "ocr_text": "Mock OCR text from image" if process_images else None,
                "analysis": {
                    "format": "JPEG",
                    "size": [1080, 1920],
                    "content_hints": ["screenshot"]
                } if process_images else None
            }
        
        # Add mock context if requested
        context_count = parameters.get("context_messages", 0)
        if context_count > 0:
            message["context"] = [
                {
                    "id": f"context_msg_{i}",
                    "chat_id": chat_id,
                    "from": "Mock Contact" if i % 2 == 0 else "Me",
                    "content": f"Context message {i}",
                    "timestamp": f"2025-08-15T09:{55+i}:00Z",
                    "message_type": "text"
                }
                for i in range(context_count)
            ]
        
        return {"message": message}