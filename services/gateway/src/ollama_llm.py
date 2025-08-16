import asyncio
import json
import logging
from typing import Dict, Any, AsyncGenerator, Optional
import httpx

logger = logging.getLogger(__name__)

class OllamaLLM:
    """Direct Ollama integration for conversational responses using Qwen3:8b"""
    
    def __init__(self, model: str = "qwen3:8b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.http_client: Optional[httpx.AsyncClient] = None
        self.is_available = False
        
    async def initialize(self):
        """Initialize the Ollama connection"""
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Test Ollama availability
        try:
            response = await self.http_client.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                model_names = [model.get("name", "") for model in models.get("models", [])]
                
                if any(self.model in name for name in model_names):
                    self.is_available = True
                    logger.info(f"Ollama LLM initialized successfully with model {self.model}")
                else:
                    logger.warning(f"Model {self.model} not found in Ollama. Available models: {model_names}")
            else:
                logger.warning(f"Ollama API returned {response.status_code}")
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
    
    async def cleanup(self):
        """Cleanup HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
    
    async def generate_response(self, user_input: str, context: Dict[str, Any]) -> str:
        """Generate a conversational response using Qwen3:8b"""
        if not self.is_available or not self.http_client:
            return self._fallback_response(user_input)
        
        try:
            system_prompt = self._build_system_prompt(context)
            
            request_data = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\nUser: {user_input}\nKenny:",
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500,
                    "stop": ["User:", "Human:"]
                }
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/api/generate",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get("response", "").strip()
                
                # Filter out thinking blocks from the response
                filtered_text = self._filter_thinking_blocks(generated_text)
                
                if filtered_text:
                    return filtered_text
                else:
                    logger.warning("Empty response from Ollama")
                    return self._fallback_response(user_input)
            else:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return self._fallback_response(user_input)
                
        except Exception as e:
            logger.error(f"Failed to generate Ollama response: {e}")
            return self._fallback_response(user_input)
    
    async def generate_response_stream(self, user_input: str, context: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """Generate a streaming conversational response using Qwen3:8b"""
        if not self.is_available or not self.http_client:
            yield self._fallback_response(user_input)
            return
        
        try:
            system_prompt = self._build_system_prompt(context)
            
            request_data = {
                "model": self.model,
                "prompt": f"{system_prompt}\n\nUser: {user_input}\nKenny:",
                "stream": True,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_tokens": 500,
                    "stop": ["User:", "Human:"]
                }
            }
            
            async with self.http_client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=request_data
            ) as response:
                
                if response.status_code != 200:
                    yield self._fallback_response(user_input)
                    return
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            done = data.get("done", False)
                            
                            if token:
                                yield token
                            
                            if done:
                                break
                                
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Failed to generate streaming Ollama response: {e}")
            yield self._fallback_response(user_input)
    
    def _build_system_prompt(self, context: Dict[str, Any]) -> str:
        """Build system prompt with Kenny's personality and context"""
        available_agents = context.get("available_agents", [])
        user_query = context.get("user_input", "")
        
        # Build dynamic capabilities list
        capabilities_text = ""
        if available_agents:
            capabilities_text = "I have access to these specialized agents and capabilities:\n"
            for agent in available_agents:
                agent_name = agent.get("display_name", agent.get("agent_id", "Unknown"))
                capabilities = agent.get("capabilities", [])
                if capabilities:
                    capabilities_text += f"• {agent_name}: {', '.join(capabilities)}\n"
        
        system_prompt = f"""You are Kenny, a helpful and friendly personal AI assistant. You have a casual, tech-savvy personality and you're great at helping users with various tasks.

{capabilities_text}

Your key traits:
- Helpful and efficient
- Friendly but not overly chatty  
- Tech-savvy and knowledgeable
- Can coordinate multiple services
- Always try to provide actionable help

When users ask about your capabilities or tools, explain what you can actually do with the agents and services available to you. Be specific about the types of tasks you can help with.

If a user's request can be handled by one of your specialized agents, mention that you can help with that specific task. Otherwise, provide general assistance and conversation.

Keep responses concise and natural. Don't be overly formal."""

        return system_prompt
    
    def _filter_thinking_blocks(self, text: str) -> str:
        """Remove thinking blocks from LLM responses to show only user-facing content"""
        import re
        
        # Remove content between <think> and </think> tags
        filtered = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        
        # Clean up extra whitespace
        filtered = re.sub(r'\n\s*\n', '\n\n', filtered).strip()
        
        return filtered
    
    def _fallback_response(self, user_input: str) -> str:
        """Fallback response when Ollama is not available"""
        if any(word in user_input.lower() for word in ["tools", "capabilities", "what can you", "help"]):
            return """I'm Kenny, your personal AI assistant! I can help you with:

• Email management (search, read, reply suggestions)
• Contact management (find, enrich contact info)
• Calendar operations (read events, schedule meetings)
• Memory storage and retrieval
• Message handling (iMessage, WhatsApp)

I work with multiple specialized agents to coordinate these tasks. What would you like me to help you with?"""
        
        elif any(word in user_input.lower() for word in ["hello", "hi", "hey"]):
            return "Hey there! I'm Kenny, your personal assistant. I'm here to help you manage your digital life. What can I do for you today?"
        
        else:
            return f"I received your message: '{user_input}'. I'm Kenny, and I'm here to help! While I'm having some connectivity issues with my language model right now, I can still help you with emails, contacts, calendar, and more. What would you like to do?"