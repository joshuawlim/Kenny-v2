"""
Intelligent Mail Agent for Kenny v2.1

Enhanced Mail Agent with embedded LLM capabilities for natural language
query interpretation and semantic caching.

Transforms from: Coordinator → Direct Mail API → JXA Tools
To: Coordinator → Mail LLM → Intelligent Tool Selection → Cached Results
"""

import os
from typing import Dict, Any
from kenny_agent.agent_service_base import AgentServiceBase
from kenny_agent.registry import AgentRegistryClient

from .handlers.search import SearchCapabilityHandler
from .handlers.read import ReadCapabilityHandler
from .handlers.propose_reply import ProposeReplyCapabilityHandler
from .tools.mail_bridge import MailBridgeTool


class IntelligentMailAgent(AgentServiceBase):
    """Enhanced Mail Agent with LLM-driven query interpretation."""
    
    def __init__(self, llm_model: str = "llama3.2:3b"):
        """Initialize the Intelligent Mail Agent."""
        super().__init__(
            agent_id="intelligent-mail-agent",
            name="Intelligent Mail Agent", 
            description="AI-powered mail search, read, and reply proposals with natural language understanding",
            version="2.1.0",
            llm_model=llm_model,
            data_scopes=["mail:inbox", "mail:sent"],
            tool_access=["macos-bridge", "sqlite-db", "ollama"],
            egress_domains=[],
            health_check={"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
        )
        
        # Set fallback capability for low-confidence queries
        self.fallback_capability = "search"
        
        print(f"Initializing Intelligent Mail Agent with LLM: {llm_model}")
        
        # Register tools first so handlers can access them
        bridge_url = os.getenv("MAC_BRIDGE_URL", "http://localhost:5100")
        print(f"Registering mail bridge tool with URL: {bridge_url}")
        self.register_tool(MailBridgeTool(bridge_url))
        
        # Register capabilities with agent reference
        print("Registering intelligent capabilities...")
        search_handler = SearchCapabilityHandler()
        search_handler._agent = self
        self.register_capability(search_handler)
        
        read_handler = ReadCapabilityHandler()
        read_handler._agent = self
        self.register_capability(read_handler)
        
        reply_handler = ProposeReplyCapabilityHandler()
        reply_handler._agent = self
        self.register_capability(reply_handler)
        
        print(f"Registered capabilities: {list(self.capabilities.keys())}")
        
        # Set up enhanced health monitoring
        self.setup_intelligent_health_monitoring()
        
        # Initialize registry client
        self.registry_client = AgentRegistryClient(
            base_url=os.getenv("AGENT_REGISTRY_URL", "http://localhost:8001")
        )
        
        print("Intelligent Mail Agent initialization complete!")
    
    def get_agent_context(self) -> str:
        """Return context for LLM interpretation."""
        return "mail management system that can search emails, read specific messages, and propose replies"
    
    def setup_intelligent_health_monitoring(self):
        """Set up enhanced health checks for intelligent agent."""
        from kenny_agent.health import HealthMonitor, HealthCheck, HealthStatus
        
        self.health_monitor = HealthMonitor("intelligent_mail_agent_monitor")
        
        # Add standard health checks
        self.health_monitor.add_health_check(
            HealthCheck(
                name="agent_status",
                check_function=self.check_agent_status,
                description="Check agent operational status",
                critical=True
            )
        )
        
        self.health_monitor.add_health_check(
            HealthCheck(
                name="llm_availability",
                check_function=self.check_llm_availability,
                description="Check LLM processor availability",
                critical=True
            )
        )
        
        self.health_monitor.add_health_check(
            HealthCheck(
                name="performance_metrics",
                check_function=self.check_performance_metrics,
                description="Check response time performance"
            )
        )
        
        self.health_monitor.add_health_check(
            HealthCheck(
                name="cache_health",
                check_function=self.check_cache_health,
                description="Check semantic cache health"
            )
        )
    
    def check_agent_status(self):
        """Health check for agent status."""
        from kenny_agent.health import HealthStatus
        
        return HealthStatus(
            status="healthy",
            message="Intelligent Mail Agent is operational",
            details={
                "agent_id": self.agent_id,
                "capabilities": len(self.capabilities),
                "llm_model": self.llm_processor.model_name,
                "version": self.version
            }
        )
    
    def check_llm_availability(self):
        """Health check for LLM processor."""
        from kenny_agent.health import HealthStatus
        
        try:
            # Basic availability check
            if self.llm_processor and self.llm_processor.ollama_url:
                return HealthStatus(
                    status="healthy",
                    message="LLM processor available",
                    details={
                        "model": self.llm_processor.model_name,
                        "url": self.llm_processor.ollama_url
                    }
                )
            else:
                return HealthStatus(
                    status="unhealthy",
                    message="LLM processor not initialized",
                    details={}
                )
        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                message=f"LLM processor error: {str(e)}",
                details={"error": str(e)}
            )
    
    def check_performance_metrics(self):
        """Health check for performance metrics."""
        from kenny_agent.health import HealthStatus
        
        metrics = self.get_performance_metrics()
        
        if metrics["status"] == "optimal":
            return HealthStatus(
                status="healthy",
                message=f"Performance optimal: {metrics['avg_response_time']:.2f}s avg",
                details=metrics
            )
        elif metrics["status"] == "acceptable":
            return HealthStatus(
                status="healthy", 
                message=f"Performance acceptable: {metrics['avg_response_time']:.2f}s avg",
                details=metrics
            )
        else:
            return HealthStatus(
                status="degraded",
                message=f"Performance degraded: {metrics['avg_response_time']:.2f}s avg", 
                details=metrics
            )
    
    def check_cache_health(self):
        """Health check for semantic cache."""
        from kenny_agent.health import HealthStatus
        
        try:
            cache_stats = {
                "l1_cache_size": len(self.semantic_cache.l1_cache),
                "l1_max_size": self.semantic_cache.l1_max_size,
                "cache_hit_rate": self.get_performance_metrics()["cache_hit_rate"]
            }
            
            return HealthStatus(
                status="healthy",
                message="Semantic cache operational",
                details=cache_stats
            )
        except Exception as e:
            return HealthStatus(
                status="unhealthy",
                message=f"Cache error: {str(e)}",
                details={"error": str(e)}
            )
    
    async def handle_query(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main entry point for natural language queries.
        
        Args:
            query: Natural language query (e.g., "find emails about project updates")
            context: Optional context from coordinator or user
            
        Returns:
            Structured response with results and metadata
        """
        print(f"[IntelligentMailAgent] Processing query: {query}")
        
        # Use the natural language processing pipeline
        result = await self.process_natural_language_query(query, context)
        
        # Log performance metrics
        metrics = self.get_performance_metrics()
        print(f"[IntelligentMailAgent] Query processed in {result.get('response_time', 0):.2f}s")
        print(f"[IntelligentMailAgent] Cache hit rate: {metrics['cache_hit_rate']:.2%}")
        
        return result
    
    async def start(self):
        """Start the Intelligent Mail Agent and register with the registry."""
        print(f"Starting {self.name}...")
        print(f"Agent ID: {self.agent_id}")
        print(f"LLM Model: {self.llm_processor.model_name}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        
        # Try to register with agent registry
        try:
            manifest = self.generate_manifest()
            # Add intelligent agent specific manifest data
            manifest.update({
                "agent_type": "intelligent_service",
                "llm_model": self.llm_processor.model_name,
                "features": [
                    "natural_language_processing",
                    "semantic_caching", 
                    "confidence_scoring",
                    "performance_optimization"
                ],
                "performance_targets": {
                    "response_time": "5s",
                    "cache_hit_rate": "80%",
                    "query_success_rate": "95%"
                }
            })
            
            registration_data = {
                "manifest": manifest,
                "health_endpoint": "http://localhost:8000"
            }
            await self.registry_client.register_agent(registration_data)
            print(f"[intelligent-mail-agent] Successfully registered with registry")
        except Exception as registry_error:
            print(f"[intelligent-mail-agent] Warning: Could not register with registry: {registry_error}")
            print(f"[intelligent-mail-agent] Continuing without registry registration")
        
        # Update health status
        self.update_health_status("healthy", "Intelligent Mail Agent started successfully")
        print("Intelligent Mail Agent started successfully!")
    
    async def stop(self):
        """Stop the Intelligent Mail Agent."""
        print(f"Stopping {self.name}...")
        self.update_health_status("degraded", "Intelligent Mail Agent stopping")
        
        # Cleanup LLM and cache resources
        await super().stop()
        
        print("Intelligent Mail Agent stopped.")


# Factory function for backward compatibility
def create_mail_agent(intelligent: bool = True, llm_model: str = "llama3.2:3b"):
    """
    Factory function to create either intelligent or basic mail agent.
    
    Args:
        intelligent: If True, creates IntelligentMailAgent, otherwise basic MailAgent
        llm_model: LLM model to use for intelligent agent
        
    Returns:
        Mail agent instance
    """
    if intelligent:
        return IntelligentMailAgent(llm_model=llm_model)
    else:
        # Import basic agent for fallback
        from .agent import MailAgent
        return MailAgent()