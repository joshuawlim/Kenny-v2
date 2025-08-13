#!/usr/bin/env python3
"""
Example usage of the Kenny Agent SDK.

This script demonstrates how to create agents, capabilities, and tools
using the base framework.
"""

import asyncio
from kenny_agent import (
    BaseAgent, 
    BaseCapabilityHandler, 
    BaseTool, 
    HealthMonitor, 
    HealthCheck, 
    HealthStatus
)


class SearchCapability(BaseCapabilityHandler):
    """Example capability for searching information."""
    
    def __init__(self):
        super().__init__(
            capability="search.query",
            description="Search for information using various sources",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "source": {"type": "string", "description": "Source to search", "default": "all"}
                },
                "required": ["query"]
            },
            safety_annotations=["read-only", "local-only"]
        )
    
    async def execute(self, parameters):
        """Execute the search capability."""
        query = parameters.get("query", "")
        source = parameters.get("source", "all")
        
        # Simulate search results
        results = [
            f"Result 1 for '{query}' from {source}",
            f"Result 2 for '{query}' from {source}",
            f"Result 3 for '{query}' from {source}"
        ]
        
        return {
            "query": query,
            "source": source,
            "results": results,
            "count": len(results)
        }


class DatabaseTool(BaseTool):
    """Example tool for database operations."""
    
    def __init__(self):
        super().__init__(
            name="database_query",
            description="Execute database queries",
            category="database",
            parameters_schema={
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL query to execute"},
                    "params": {"type": "object", "description": "Query parameters"}
                },
                "required": ["sql"]
            }
        )
    
    def execute(self, parameters):
        """Execute the database query."""
        sql = parameters.get("sql", "")
        params = parameters.get("params", {})
        
        # Simulate database query execution
        print(f"Executing SQL: {sql}")
        print(f"Parameters: {params}")
        
        # Record usage
        self.record_usage()
        
        return {
            "sql": sql,
            "params": params,
            "result": "Query executed successfully",
            "rows_affected": 1
        }


class ExampleAgent(BaseAgent):
    """Example agent that demonstrates the SDK capabilities."""
    
    def __init__(self):
        super().__init__(
            agent_id="example-agent",
            name="Example Agent",
            description="A demonstration agent showing SDK features",
            data_scopes=["example:data", "example:search"],
            tool_access=["database", "search_engine"],
            egress_domains=[],
            health_check={"endpoint": "/health", "interval_seconds": 60, "timeout_seconds": 10}
        )
        
        # Register capabilities
        self.register_capability(SearchCapability())
        
        # Register tools
        self.register_tool(DatabaseTool())
        
        # Set up health monitoring
        self.setup_health_monitoring()
    
    def setup_health_monitoring(self):
        """Set up health checks for the agent."""
        self.health_monitor = HealthMonitor("example_agent_monitor")
        
        # Add health checks
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
                name="capability_count",
                check_function=self.check_capability_count,
                description="Check number of registered capabilities"
            )
        )
    
    def check_agent_status(self):
        """Health check for agent status."""
        return HealthStatus(
            status="healthy",
            message="Agent is operational",
            details={"agent_id": self.agent_id, "capabilities": len(self.capabilities)}
        )
    
    def check_capability_count(self):
        """Health check for capability count."""
        if len(self.capabilities) > 0:
            return HealthStatus(
                status="healthy",
                message="Capabilities are registered",
                details={"capability_count": len(self.capabilities)}
            )
        else:
            return HealthStatus(
                status="unhealthy",
                message="No capabilities registered",
                details={"capability_count": 0}
            )
    
    async def start(self):
        """Start the agent."""
        print(f"Starting {self.name}...")
        print(f"Agent ID: {self.agent_id}")
        print(f"Capabilities: {list(self.capabilities.keys())}")
        print(f"Tools: {list(self.tools.keys())}")
        
        # Update health status
        self.update_health_status("healthy", "Agent started successfully")
        print("Agent started successfully!")
    
    async def stop(self):
        """Stop the agent."""
        print(f"Stopping {self.name}...")
        self.update_health_status("degraded", "Agent stopping")
        print("Agent stopped.")


async def main():
    """Main function demonstrating agent usage."""
    print("=== Kenny Agent SDK Example ===\n")
    
    # Create and start the agent
    agent = ExampleAgent()
    await agent.start()
    
    print("\n--- Testing Capabilities ---")
    
    # Test capability execution
    search_result = await agent.execute_capability("search.query", {
        "query": "artificial intelligence",
        "source": "web"
    })
    print(f"Search result: {search_result}")
    
    print("\n--- Testing Tools ---")
    
    # Test tool execution
    db_result = agent.execute_tool("database_query", {
        "sql": "SELECT * FROM users WHERE active = true",
        "params": {"active": True}
    })
    print(f"Database result: {db_result}")
    
    print("\n--- Health Monitoring ---")
    
    # Get health status
    health_status = agent.get_health_status()
    print(f"Agent health: {health_status}")
    
    # Get overall health from monitor
    overall_health = agent.health_monitor.get_overall_health()
    print(f"Overall health: {overall_health.status} - {overall_health.message}")
    
    print("\n--- Agent Manifest ---")
    
    # Generate and display manifest
    manifest = agent.generate_manifest()
    print(f"Agent manifest: {manifest}")
    
    print("\n--- Stopping Agent ---")
    
    # Stop the agent
    await agent.stop()
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
