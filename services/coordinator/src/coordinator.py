from typing import Dict, Any, List, Optional, TypedDict
from langgraph.graph import StateGraph, END
import asyncio
import logging

from .nodes.router import RouterNode
from .nodes.planner import PlannerNode  
from .nodes.executor import ExecutorNode
from .nodes.reviewer import ReviewerNode
from .agents.agent_client import AgentClient
from .policy.engine import PolicyEngine

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CoordinatorState(TypedDict):
    """State object for coordinator execution"""
    user_input: str
    context: Dict[str, Any]
    messages: List[str]
    current_node: Optional[str]
    execution_path: List[str]
    errors: List[str]
    results: Dict[str, Any]

class Coordinator:
    """Main coordinator class for multi-agent orchestration"""
    
    def __init__(self, registry_url: str = "http://localhost:8001"):
        self.graph = None
        self.registry_url = registry_url
        self.agent_client = AgentClient(registry_url)
        self.policy_engine = PolicyEngine()
        
        # Initialize enhanced nodes
        self.router_node = RouterNode()
        self.planner_node = PlannerNode()
        self.executor_node = ExecutorNode()
        self.reviewer_node = ReviewerNode(self.policy_engine)
        
        # Load default policies
        self.policy_engine.load_default_rules()
        
        self._build_graph()
    
    def _build_graph(self):
        """Build the LangGraph execution graph"""
        # Create state graph
        workflow = StateGraph(CoordinatorState)
        
        # Add nodes (will be implemented next)
        workflow.add_node("router", self._router_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("executor", self._executor_node)
        workflow.add_node("reviewer", self._reviewer_node)
        
        # Set entry point
        workflow.set_entry_point("router")
        
        # Define edges
        workflow.add_edge("router", "planner")
        workflow.add_edge("planner", "executor")
        workflow.add_edge("executor", "reviewer")
        workflow.add_edge("reviewer", END)
        
        # Compile the graph
        self.graph = workflow.compile()
        logger.info("Coordinator graph built successfully")
    
    async def _router_node(self, state: CoordinatorState) -> CoordinatorState:
        """Route user input with intelligent intent classification"""
        return await self.router_node.route_request(state, self.agent_client)
    
    async def _planner_node(self, state: CoordinatorState) -> CoordinatorState:
        """Plan execution steps based on routing results"""
        return await self.planner_node.plan_execution(state)
    
    async def _executor_node(self, state: CoordinatorState) -> CoordinatorState:
        """Execute planned actions on live agents"""
        return await self.executor_node.execute_plan(state)
    
    async def _reviewer_node(self, state: CoordinatorState) -> CoordinatorState:
        """Review and finalize execution results with policy checks"""
        return await self.reviewer_node.review_execution(state)
    
    async def process_request(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> CoordinatorState:
        """Process a user request through the coordinator"""
        logger.info(f"Processing request: {user_input}")
        
        # Create initial state
        initial_state: CoordinatorState = {
            "user_input": user_input,
            "context": context or {},
            "messages": [],
            "current_node": None,
            "execution_path": [],
            "errors": [],
            "results": {}
        }
        
        try:
            # Execute the graph
            final_state = await self.graph.ainvoke(initial_state)
            logger.info("Request processing completed successfully")
            return final_state
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            initial_state["errors"].append(str(e))
            return initial_state
    
    def get_graph_info(self) -> Dict[str, Any]:
        """Get information about the coordinator graph"""
        if self.graph is None:
            return {"status": "not_built"}
        
        return {
            "status": "built",
            "nodes": ["router", "planner", "executor", "reviewer"],
            "entry_point": "router",
            "end_point": "END",
            "registry_url": self.registry_url,
            "policy_rules_count": len(self.policy_engine.get_rules())
        }
    
    async def cleanup(self):
        """Cleanup coordinator resources"""
        try:
            await self.agent_client.close()
            await self.executor_node.cleanup()
            logger.info("Coordinator cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
