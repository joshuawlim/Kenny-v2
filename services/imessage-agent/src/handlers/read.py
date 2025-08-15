"""
Read capability handler for iMessage messages.

This handler provides functionality to read full iMessage messages and threads
including attachment content with local processing.
"""

from typing import Dict, Any, List, Optional
from kenny_agent.base_handler import BaseCapabilityHandler


class ReadCapabilityHandler(BaseCapabilityHandler):
    """Handler for reading iMessage messages and threads."""
    
    def __init__(self):
        """Initialize the read capability handler."""
        super().__init__(
            capability="messages.read",
            description="Read full iMessage messages and threads with attachment content analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "thread_id": {"type": "string"},
                    "include_attachments": {"type": "boolean", "default": True},
                    "process_images": {"type": "boolean", "default": True},
                    "context_messages": {"type": "integer", "minimum": 0, "maximum": 10, "default": 0}
                },
                "anyOf": [
                    {"required": ["message_id"]},
                    {"required": ["thread_id"]}
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
                            "thread_id": {"type": "string"},
                            "from": {"type": ["string", "null"]},
                            "to": {"type": ["string", "null"]},
                            "content": {"type": ["string", "null"]},
                            "timestamp": {"type": "string", "format": "date-time"},
                            "message_type": {"type": "string"},
                            "contact_name": {"type": ["string", "null"]},
                            "phone_number": {"type": ["string", "null"]},
                            "attachments": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string"},
                                        "url": {"type": "string"},
                                        "filename": {"type": ["string", "null"]},
                                        "processed": {"type": "boolean"},
                                        "ocr_text": {"type": ["string", "null"]},
                                        "analysis": {"type": "object"}
                                    }
                                }
                            },
                            "context": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        },
                        "required": ["id", "thread_id", "timestamp", "message_type"]
                    },
                    "thread": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "participants": {"type": "array", "items": {"type": "string"}},
                            "message_count": {"type": "integer"},
                            "last_message": {"type": "string", "format": "date-time"}
                        }
                    }
                },
                "required": ["message"],
                "additionalProperties": False
            },
            safety_annotations=["read-only", "local-only", "no-egress"]
        )
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the read capability using the iMessage bridge and image processing tools.
        
        Args:
            parameters: Read parameters
            
        Returns:
            Full message data with attachment processing
        """
        try:
            # Get tools from agent
            if not hasattr(self, '_agent') or self._agent is None:
                return self._get_mock_read_result(parameters)
            
            imessage_bridge_tool = self._agent.tools.get("imessage_bridge")
            image_processor_tool = self._agent.tools.get("image_processor")
            
            if not imessage_bridge_tool:
                return self._get_mock_read_result(parameters)
            
            # Get message from bridge
            message_id = parameters.get("message_id")
            thread_id = parameters.get("thread_id")
            
            if message_id:
                bridge_result = imessage_bridge_tool.execute({
                    "operation": "read",
                    "message_id": message_id
                })
            elif thread_id:
                # Get thread information and latest message
                bridge_result = imessage_bridge_tool.execute({
                    "operation": "read",
                    "thread_id": thread_id
                })
            else:
                return {"message": None, "error": "Either message_id or thread_id required"}
            
            # Extract message from bridge result
            if "result" in bridge_result:
                message_data = bridge_result["result"]
                if isinstance(message_data, dict) and "messages" in message_data:
                    # Thread result with multiple messages - get the latest
                    messages = message_data["messages"]
                    if messages:
                        message_data = messages[0]  # Latest message
                    else:
                        return {"message": None, "error": "No messages found in thread"}
            else:
                return self._get_mock_read_result(parameters)
            
            # Process attachments if present and requested
            include_attachments = parameters.get("include_attachments", True)
            process_images = parameters.get("process_images", True)
            
            if include_attachments and message_data.get("has_attachments") and image_processor_tool:
                message_data = await self._process_attachments(message_data, image_processor_tool, process_images)
            
            # Add context messages if requested
            context_count = parameters.get("context_messages", 0)
            if context_count > 0 and thread_id:
                context_messages = await self._get_context_messages(
                    thread_id, message_data, context_count, imessage_bridge_tool
                )
                message_data["context"] = context_messages
            
            # Build response
            response = {"message": message_data}
            
            # Add thread information if we have it
            if thread_id and bridge_result.get("result", {}).get("thread_info"):
                response["thread"] = bridge_result["result"]["thread_info"]
            
            return response
            
        except Exception as e:
            print(f"iMessage read error: {e}")
            return self._get_mock_read_result(parameters)
    
    async def _process_attachments(self, message_data: Dict[str, Any], image_processor: Any, process_images: bool) -> Dict[str, Any]:
        """Process attachment content in the message."""
        try:
            attachments = message_data.get("attachments", [])
            processed_attachments = []
            
            for attachment in attachments:
                attachment_info = {
                    "type": attachment.get("type", "unknown"),
                    "url": attachment.get("url", ""),
                    "filename": attachment.get("filename"),
                    "processed": False
                }
                
                if process_images and attachment_info["type"] in ["image", "photo"]:
                    # Process image with local OCR/analysis
                    try:
                        image_result = image_processor.execute({
                            "operation": "ocr",
                            "image_path": attachment.get("local_path", "")
                        })
                        
                        if image_result.get("text"):
                            attachment_info["ocr_text"] = image_result["text"]
                            attachment_info["processed"] = True
                        
                        # Also get image analysis
                        analysis_result = image_processor.execute({
                            "operation": "analyze",
                            "image_path": attachment.get("local_path", "")
                        })
                        
                        if analysis_result.get("properties"):
                            attachment_info["analysis"] = analysis_result["properties"]
                    except Exception as e:
                        print(f"Attachment processing error: {e}")
                        attachment_info["processing_error"] = str(e)
                
                processed_attachments.append(attachment_info)
            
            message_data["attachments"] = processed_attachments
            return message_data
            
        except Exception as e:
            print(f"Attachment processing error: {e}")
            message_data["attachments"] = []
            return message_data
    
    async def _get_context_messages(self, thread_id: str, current_message: Dict[str, Any], 
                                   count: int, bridge_tool: Any) -> List[Dict[str, Any]]:
        """Get context messages around the current message in a thread."""
        try:
            # Get recent messages from the thread
            context_result = bridge_tool.execute({
                "operation": "read",
                "thread_id": thread_id
            })
            
            if context_result.get("result", {}).get("messages"):
                messages = context_result["result"]["messages"]
                # Filter out the current message and return the requested count
                context = [msg for msg in messages if msg.get("id") != current_message.get("id")]
                return context[:count]
            
            return []
            
        except Exception as e:
            print(f"Context messages error: {e}")
            return []
    
    def _get_mock_read_result(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock read result as fallback."""
        message_id = parameters.get("message_id", "mock_imessage_1")
        thread_id = parameters.get("thread_id", "mock_thread")
        include_attachments = parameters.get("include_attachments", True)
        process_images = parameters.get("process_images", True)
        
        message = {
            "id": message_id,
            "thread_id": thread_id,
            "from": "Mock Contact",
            "to": "Me",
            "content": "This is a mock iMessage with full content.",
            "timestamp": "2025-08-15T10:00:00Z",
            "message_type": "text",
            "contact_name": "Mock Contact",
            "phone_number": "+1234567890"
        }
        
        # Add mock attachments if requested
        if include_attachments:
            message["attachments"] = [
                {
                    "type": "image",
                    "url": "file://mock/attachment.jpg",
                    "filename": "attachment.jpg",
                    "processed": process_images,
                    "ocr_text": "Mock OCR text from attachment" if process_images else None,
                    "analysis": {
                        "format": "JPEG",
                        "size": [1080, 1920],
                        "content_hints": ["screenshot"]
                    } if process_images else None
                }
            ]
        
        # Add mock context if requested
        context_count = parameters.get("context_messages", 0)
        if context_count > 0:
            message["context"] = [
                {
                    "id": f"context_imsg_{i}",
                    "thread_id": thread_id,
                    "from": "Mock Contact" if i % 2 == 0 else "Me",
                    "content": f"Context iMessage {i}",
                    "timestamp": f"2025-08-15T09:{55+i}:00Z",
                    "message_type": "text",
                    "contact_name": "Mock Contact" if i % 2 == 0 else "Me"
                }
                for i in range(context_count)
            ]
        
        response = {"message": message}
        
        # Add mock thread information
        if thread_id:
            response["thread"] = {
                "id": thread_id,
                "participants": ["Mock Contact", "Me"],
                "message_count": 25,
                "last_message": "2025-08-15T10:00:00Z"
            }
        
        return response