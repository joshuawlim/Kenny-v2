from typing import Dict, Any, List, Optional, TypedDict, AsyncGenerator
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
    
    async def process_request_progressive(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a user request with progressive streaming results"""
        logger.info(f"Starting progressive processing: {user_input}")
        
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
            # Stream progress through each node
            current_state = initial_state
            
            # Router node
            yield {
                "type": "node_start",
                "node": "router",
                "message": "Analyzing request intent...",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            current_state = await self.router_node.route_request(current_state, self.agent_client)
            
            yield {
                "type": "node_complete",
                "node": "router", 
                "result": {
                    "intent": current_state["context"].get("intent"),
                    "confidence": current_state["context"].get("confidence", 0.0)
                },
                "message": f"Intent classified: {current_state['context'].get('intent', 'unknown')}",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Planner node
            yield {
                "type": "node_start",
                "node": "planner",
                "message": "Creating execution plan...",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            current_state = await self.planner_node.plan_execution(current_state)
            
            execution_plan = current_state["context"].get("execution_plan", [])
            yield {
                "type": "node_complete",
                "node": "planner",
                "result": {
                    "execution_plan": execution_plan,
                    "agents_required": [step.get("agent_id") for step in execution_plan if step.get("agent_id")],
                    "estimated_duration": "unknown"
                },
                "message": f"Plan created with {len(execution_plan)} steps",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Executor node with progressive agent results
            yield {
                "type": "node_start", 
                "node": "executor",
                "message": "Executing agent tasks...",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Execute with streaming from individual agents
            async for agent_update in self._execute_with_streaming(current_state):
                yield agent_update
            
            # Get final state after streaming execution
            current_state = current_state  # State is updated in place during streaming
            
            yield {
                "type": "node_complete",
                "node": "executor", 
                "result": current_state["results"],
                "message": f"Execution completed with {len(current_state['results'])} agent results",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Reviewer node
            yield {
                "type": "node_start",
                "node": "reviewer", 
                "message": "Reviewing results and policies...",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            current_state = await self.reviewer_node.review_execution(current_state)
            
            yield {
                "type": "node_complete",
                "node": "reviewer",
                "result": {
                    "review_status": current_state["context"].get("review_status"),
                    "policy_compliance": current_state["context"].get("policy_compliance", {}),
                    "recommendations": current_state["context"].get("recommendations", [])
                },
                "message": "Review completed",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            # Final result
            yield {
                "type": "final_result",
                "result": {
                    "intent": current_state["context"].get("intent"),
                    "plan": current_state["context"].get("plan"),
                    "execution_path": current_state["execution_path"],
                    "results": current_state["results"],
                    "errors": current_state["errors"],
                    "review": {
                        "status": current_state["context"].get("review_status"),
                        "compliance": current_state["context"].get("policy_compliance", {})
                    }
                },
                "message": "Request processing completed successfully",
                "timestamp": asyncio.get_event_loop().time()
            }
            
        except Exception as e:
            logger.error(f"Error in progressive processing: {e}")
            yield {
                "type": "error",
                "message": str(e),
                "timestamp": asyncio.get_event_loop().time()
            }
    
    async def _execute_with_streaming(self, state: CoordinatorState) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute agents with streaming progress updates"""
        execution_plan = state["context"].get("execution_plan", [])
        
        if not execution_plan:
            return
        
        # Execute agents and stream individual results
        for i, step in enumerate(execution_plan):
            agent_id = step.get("agent_id")
            capability = step.get("capability")
            
            yield {
                "type": "agent_start",
                "agent_id": agent_id,
                "capability": capability,
                "message": f"Executing {capability} on {agent_id}...",
                "progress": f"{i+1}/{len(execution_plan)}",
                "timestamp": asyncio.get_event_loop().time()
            }
            
            try:
                # Execute the individual agent task using the executor
                agent_id = step.get("agent_id") 
                capability = step.get("capability")
                parameters = step.get("parameters", {})
                
                result = await self.executor_node.executor.execute_capability(agent_id, capability, parameters)
                
                yield {
                    "type": "agent_complete",
                    "agent_id": agent_id,
                    "capability": capability,
                    "result": result,
                    "message": f"Completed {capability} on {agent_id}",
                    "progress": f"{i+1}/{len(execution_plan)}",
                    "timestamp": asyncio.get_event_loop().time()
                }
                
                # Update state with result
                if agent_id not in state["results"]:
                    state["results"][agent_id] = {}
                state["results"][agent_id][capability] = result
                
            except Exception as e:
                error_msg = f"Agent {agent_id} failed: {str(e)}"
                logger.error(error_msg)
                state["errors"].append(error_msg)
                
                yield {
                    "type": "agent_error",
                    "agent_id": agent_id,
                    "capability": capability,
                    "error": str(e),
                    "message": f"Failed {capability} on {agent_id}: {str(e)}",
                    "progress": f"{i+1}/{len(execution_plan)}",
                    "timestamp": asyncio.get_event_loop().time()
                }
    
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
