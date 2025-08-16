import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TaskPlanner:
    """Intelligent task planning for multi-agent coordination"""
    
    def __init__(self):
        self.capability_mappings = {
            "mail_operation": {
                "search": ["messages.search"],
                "read": ["messages.read"],
                "reply": ["messages.propose_reply"],
                "compose": ["messages.propose_reply"]
            },
            "contacts_operation": {
                "find": ["contacts.resolve"],
                "lookup": ["contacts.resolve"],
                "enrich": ["contacts.enrich"],
                "merge": ["contacts.merge"],
                "update": ["contacts.enrich"]
            },
            "memory_operation": {
                "remember": ["memory.store"],
                "recall": ["memory.retrieve"],
                "find": ["memory.retrieve"],
                "store": ["memory.store"],
                "search": ["memory.retrieve"]
            },
            "conversational_query": {
                "respond": ["llm_response"]
            }
        }
    
    def create_execution_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed execution plan based on intent and required agents"""
        logger.info(f"Planning for intent: {state['context'].get('intent')}")
        
        intent = state['context'].get('intent')
        required_agents = state['context'].get('required_agents', [])
        execution_strategy = state['context'].get('execution_strategy', 'single_agent')
        user_input = state['user_input']
        
        # Generate execution plan
        if execution_strategy == "single_agent":
            plan = self._create_single_agent_plan(intent, required_agents, user_input)
        elif execution_strategy == "multi_agent":
            plan = self._create_multi_agent_plan(intent, required_agents, user_input)
        elif execution_strategy == "sequential":
            plan = self._create_sequential_plan(intent, required_agents, user_input)
        else:
            plan = self._create_fallback_plan(intent, user_input)
        
        state['context']['execution_plan'] = plan
        state['context']['plan_type'] = execution_strategy
        
        # Legacy compatibility - simple plan list
        state['context']['plan'] = [step['action'] for step in plan]
        
        logger.info(f"Created {execution_strategy} plan with {len(plan)} steps")
        return state
    
    def _create_single_agent_plan(self, intent: str, required_agents: List[Dict], user_input: str) -> List[Dict[str, Any]]:
        """Create plan for single agent execution"""
        # Handle conversational queries specially
        if intent == "conversational_query":
            return [{
                "step_id": "step_1",
                "action": "conversational_response",
                "agent_id": None,
                "capability": None,
                "parameters": {
                    "query": user_input,
                    "intent": intent,
                    "requires_llm_enhancement": True
                },
                "dependencies": []
            }]
        
        if not required_agents:
            return [{
                "step_id": "step_1",
                "action": "general_processing",
                "agent_id": None,
                "capability": None,
                "parameters": {"query": user_input},
                "dependencies": []
            }]
        
        agent = required_agents[0]
        capability = agent['capabilities'][0] if agent['capabilities'] else "general"
        
        return [{
            "step_id": "step_1",
            "action": f"execute_{capability.replace('.', '_')}",
            "agent_id": agent['agent_id'],
            "capability": capability,
            "parameters": self._extract_parameters(user_input, capability),
            "dependencies": []
        }]
    
    def _create_multi_agent_plan(self, intent: str, required_agents: List[Dict], user_input: str) -> List[Dict[str, Any]]:
        """Create plan for parallel multi-agent execution"""
        plan = []
        
        for i, agent in enumerate(required_agents):
            for j, capability in enumerate(agent['capabilities']):
                step_id = f"step_{i+1}_{j+1}"
                plan.append({
                    "step_id": step_id,
                    "action": f"execute_{capability.replace('.', '_')}",
                    "agent_id": agent['agent_id'],
                    "capability": capability,
                    "parameters": self._extract_parameters(user_input, capability),
                    "dependencies": [],
                    "parallel": True
                })
        
        # Add aggregation step
        if len(plan) > 1:
            plan.append({
                "step_id": f"step_{len(plan)+1}",
                "action": "aggregate_results",
                "agent_id": "coordinator",
                "capability": "aggregate",
                "parameters": {"source_steps": [step["step_id"] for step in plan[:-1]]},
                "dependencies": [step["step_id"] for step in plan[:-1]]
            })
        
        return plan
    
    def _create_sequential_plan(self, intent: str, required_agents: List[Dict], user_input: str) -> List[Dict[str, Any]]:
        """Create plan for sequential agent execution"""
        plan = []
        previous_step = None
        
        for i, agent in enumerate(required_agents):
            for j, capability in enumerate(agent['capabilities']):
                step_id = f"step_{i+1}_{j+1}"
                dependencies = [previous_step] if previous_step else []
                
                plan.append({
                    "step_id": step_id,
                    "action": f"execute_{capability.replace('.', '_')}",
                    "agent_id": agent['agent_id'],
                    "capability": capability,
                    "parameters": self._extract_parameters(user_input, capability),
                    "dependencies": dependencies,
                    "sequential": True
                })
                
                previous_step = step_id
        
        return plan
    
    def _create_fallback_plan(self, intent: str, user_input: str) -> List[Dict[str, Any]]:
        """Create fallback plan when no specific agents are available"""
        return [{
            "step_id": "step_1",
            "action": "general_processing",
            "agent_id": None,
            "capability": None,
            "parameters": {"query": user_input, "intent": intent},
            "dependencies": []
        }]
    
    def _extract_parameters(self, user_input: str, capability: str) -> Dict[str, Any]:
        """Extract parameters for capability execution from user input"""
        base_params = {"query": user_input}
        
        # Capability-specific parameter extraction
        if capability.startswith("messages."):
            if "inbox" in user_input.lower():
                base_params["mailbox"] = "Inbox"
            elif "sent" in user_input.lower():
                base_params["mailbox"] = "Sent"
            
            # Extract limit if specified
            import re
            # Try multiple patterns for extracting numeric limits
            limit_patterns = [
                r'(?:exactly|show|get|find)\s+(\d+)\s*(?:most\s+)?(?:recent|latest|last)',
                r'(\d+)\s*(?:recent|latest|last)',
                r'(?:top|first)\s+(\d+)',
                r'(\d+)\s*(?:most\s+)?(?:recent|latest|last)',
                r'(?:most\s+)?(?:recent|latest|last)\s+(\d+)',  # "most recent 3"
                r'(?:pull|get|fetch)\s+(?:me\s+)?(?:most\s+)?(?:recent|latest|last)\s+(\d+)'  # "pull me most recent 3"
            ]
            
            limit_found = False
            for pattern in limit_patterns:
                limit_match = re.search(pattern, user_input.lower())
                if limit_match:
                    base_params["limit"] = int(limit_match.group(1))
                    limit_found = True
                    break
            
            if not limit_found:
                base_params["limit"] = 10
                
        elif capability.startswith("contacts."):
            # Extract contact name if mentioned
            import re
            # Look for quoted names or names after "contact" or "person"
            name_patterns = [
                r'"([^"]+)"',
                r"'([^']+)'",
                r'(?:contact|person|find)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            ]
            
            for pattern in name_patterns:
                match = re.search(pattern, user_input)
                if match:
                    base_params["name"] = match.group(1)
                    break
                    
        elif capability.startswith("memory."):
            # For memory operations, use the full query
            base_params["content"] = user_input
            
            if capability == "memory.retrieve":
                base_params["limit"] = 5
                
        return base_params

class PlannerNode:
    """Enhanced planner node for intelligent task planning"""
    
    def __init__(self):
        self.planner = TaskPlanner()
    
    async def plan_execution(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Plan execution steps based on routing results"""
        logger.info(f"Planning execution for intent: {state['context'].get('intent')}")
        state['current_node'] = "planner"
        state['execution_path'].append("planner")
        
        try:
            # Create detailed execution plan
            state = self.planner.create_execution_plan(state)
            
            # Validate the plan
            plan = state['context'].get('execution_plan', [])
            if self._validate_plan(plan):
                logger.info(f"Plan validated successfully with {len(plan)} steps")
            else:
                logger.warning("Plan validation failed, using fallback")
                state['context']['execution_plan'] = [{
                    "step_id": "step_1",
                    "action": "general_processing",
                    "agent_id": None,
                    "capability": None,
                    "parameters": {"query": state['user_input']},
                    "dependencies": []
                }]
                state['context']['plan'] = ["general_processing"]
            
        except Exception as e:
            logger.error(f"Error in planning: {e}")
            state['errors'].append(f"Planning error: {str(e)}")
            # Fallback plan
            state['context']['plan'] = ["general_processing"]
            state['context']['execution_plan'] = [{
                "step_id": "step_1",
                "action": "general_processing",
                "agent_id": None,
                "capability": None,
                "parameters": {"query": state['user_input']},
                "dependencies": []
            }]
        
        return state
    
    def _validate_plan(self, plan: List[Dict[str, Any]]) -> bool:
        """Validate execution plan structure and dependencies"""
        if not plan:
            return False
        
        step_ids = {step.get('step_id') for step in plan}
        
        for step in plan:
            # Check required fields
            required_fields = ['step_id', 'action', 'parameters']
            if not all(field in step for field in required_fields):
                logger.warning(f"Step {step.get('step_id')} missing required fields")
                return False
            
            # Check dependency references
            dependencies = step.get('dependencies', [])
            for dep in dependencies:
                if dep not in step_ids:
                    logger.warning(f"Step {step.get('step_id')} has invalid dependency: {dep}")
                    return False
        
        return True