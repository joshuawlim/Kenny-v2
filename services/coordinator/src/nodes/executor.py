import logging
import asyncio
import httpx
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AgentExecutor:
    """Execute capabilities on live agents"""
    
    def __init__(self, registry_url: str = "http://localhost:8001"):
        self.registry_url = registry_url
        self.agent_urls = {}
        self.http_client = httpx.AsyncClient(timeout=90.0)
    
    async def load_agent_urls(self):
        """Load agent URLs from registry"""
        try:
            response = await self.http_client.get(f"{self.registry_url}/agents")
            response.raise_for_status()
            agents = response.json()
            
            for agent in agents:
                agent_id = agent.get("agent_id")
                health_endpoint = agent.get("health_endpoint")
                if agent_id and health_endpoint:
                    # Extract base URL from health endpoint
                    base_url = health_endpoint.replace("/health", "")
                    self.agent_urls[agent_id] = base_url
                    
            logger.info(f"Loaded URLs for {len(self.agent_urls)} agents")
            
        except Exception as e:
            logger.warning(f"Failed to load agent URLs from registry: {e}")
            # Use default URLs with correct agent IDs
            self.agent_urls = {
                "mail-agent": "http://localhost:8000",
                "contacts-agent": "http://localhost:8003", 
                "memory-agent": "http://localhost:8004"
            }
    
    async def execute_capability(self, agent_id: str, capability: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a capability on a specific agent"""
        if agent_id not in self.agent_urls:
            await self.load_agent_urls()
        
        if agent_id not in self.agent_urls:
            logger.error(f"No URL found for agent: {agent_id}")
            return {
                "status": "error",
                "error": f"Agent {agent_id} not available",
                "agent_id": agent_id,
                "capability": capability
            }
        
        agent_url = self.agent_urls[agent_id]
        endpoint = f"{agent_url}/capabilities/{capability}"
        
        try:
            logger.info(f"Executing {capability} on {agent_id} at {endpoint}")
            logger.info(f"Sending parameters: {parameters}")
            
            response = await self.http_client.post(
                endpoint,
                json={"input": parameters},
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully executed {capability} on {agent_id}")
                return {
                    "status": "success",
                    "agent_id": agent_id,
                    "capability": capability,
                    "result": result
                }
            else:
                logger.error(f"Agent {agent_id} returned {response.status_code}: {response.text}")
                return {
                    "status": "error",
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "agent_id": agent_id,
                    "capability": capability
                }
                
        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            traceback_info = traceback.format_exc()
            logger.error(f"Failed to execute {capability} on {agent_id}: {error_details}")
            logger.error(f"Full traceback: {traceback_info}")
            return {
                "status": "error",
                "error": error_details if str(e) else f"{type(e).__name__} with no message",
                "agent_id": agent_id,
                "capability": capability
            }
    
    async def execute_parallel(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multiple capabilities in parallel"""
        logger.info(f"Executing {len(tasks)} tasks in parallel")
        
        async def execute_task(task):
            agent_id = task.get('agent_id')
            capability = task.get('capability')
            parameters = task.get('parameters', {})
            step_id = task.get('step_id')
            
            result = await self.execute_capability(agent_id, capability, parameters)
            result['step_id'] = step_id
            return result
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*[execute_task(task) for task in tasks])
        return results
    
    async def execute_sequential(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute capabilities sequentially, passing results between steps"""
        logger.info(f"Executing {len(tasks)} tasks sequentially")
        
        results = []
        context = {}
        
        for task in tasks:
            agent_id = task.get('agent_id')
            capability = task.get('capability')
            parameters = task.get('parameters', {}).copy()
            step_id = task.get('step_id')
            dependencies = task.get('dependencies', [])
            
            # Inject results from dependent steps
            for dep_step_id in dependencies:
                if dep_step_id in context:
                    dep_result = context[dep_step_id]
                    # Add dependent result to parameters
                    parameters[f"from_{dep_step_id}"] = dep_result
            
            result = await self.execute_capability(agent_id, capability, parameters)
            result['step_id'] = step_id
            
            # Store result for dependent steps
            context[step_id] = result.get('result', {})
            results.append(result)
        
        return results
    
    async def close(self):
        """Close HTTP client"""
        await self.http_client.aclose()

class ExecutorNode:
    """Enhanced executor node for live agent communication"""
    
    def __init__(self):
        self.executor = AgentExecutor()
    
    async def execute_plan(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the planned actions on live agents"""
        logger.info("Executing planned actions")
        state['current_node'] = "executor"
        state['execution_path'].append("executor")
        
        try:
            execution_plan = state['context'].get('execution_plan', [])
            plan_type = state['context'].get('plan_type', 'single_agent')
            
            if not execution_plan:
                # Fallback to legacy plan format
                legacy_plan = state['context'].get('plan', [])
                execution_plan = self._convert_legacy_plan(legacy_plan, state)
            
            # Execute based on plan type
            if plan_type == "multi_agent":
                results = await self._execute_multi_agent_plan(execution_plan)
            elif plan_type == "sequential":
                results = await self._execute_sequential_plan(execution_plan)
            else:
                results = await self._execute_single_agent_plan(execution_plan)
            
            # Store results
            state['results']['execution_results'] = results
            
            # Legacy compatibility - store results by action name
            for result in results:
                step_id = result.get('step_id', 'unknown')
                action = self._extract_action_from_step_id(step_id, execution_plan)
                state['results'][action] = result
            
            # Check for errors
            errors = [r for r in results if r.get('status') == 'error']
            if errors:
                for error in errors:
                    state['errors'].append(f"Step {error.get('step_id')}: {error.get('error')}")
            
            logger.info(f"Executed {len(results)} steps with {len(errors)} errors")
            
        except Exception as e:
            logger.error(f"Error in execution: {e}")
            state['errors'].append(f"Execution error: {str(e)}")
            # Store empty results
            state['results']['execution_results'] = []
        
        return state
    
    async def _execute_single_agent_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute single agent plan"""
        results = []
        
        for step in plan:
            agent_id = step.get('agent_id')
            capability = step.get('capability')
            parameters = step.get('parameters', {})
            
            if agent_id and capability:
                result = await self.executor.execute_capability(agent_id, capability, parameters)
                result['step_id'] = step.get('step_id')
                results.append(result)
            else:
                # Handle conversational responses and general processing
                action = step.get('action', '')
                if action == "conversational_response" or parameters.get('requires_llm_enhancement'):
                    # This is a conversational query that should be handled by Ollama
                    results.append({
                        "status": "success",
                        "step_id": step.get('step_id'),
                        "action": action,
                        "result": {
                            "message": f"CONVERSATIONAL_QUERY: {parameters.get('query', 'N/A')}",
                            "requires_llm_enhancement": True,
                            "query_type": "conversational",
                            "intent": parameters.get('intent', 'unknown')
                        }
                    })
                else:
                    # Handle other general processing - indicate this needs Gateway enhancement
                    results.append({
                        "status": "success",
                        "step_id": step.get('step_id'),
                        "action": action,
                        "result": {
                            "message": f"GENERAL_QUERY: {parameters.get('query', 'N/A')}",
                            "requires_llm_enhancement": True,
                            "query_type": "general"
                        }
                    })
        
        return results
    
    async def _execute_multi_agent_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute multi-agent plan with parallel execution"""
        # Separate parallel tasks from aggregation tasks
        parallel_tasks = [step for step in plan if step.get('parallel', False)]
        sequential_tasks = [step for step in plan if not step.get('parallel', False)]
        
        results = []
        
        # Execute parallel tasks
        if parallel_tasks:
            parallel_results = await self.executor.execute_parallel(parallel_tasks)
            results.extend(parallel_results)
        
        # Execute remaining tasks sequentially (like aggregation)
        if sequential_tasks:
            sequential_results = await self.executor.execute_sequential(sequential_tasks)
            results.extend(sequential_results)
        
        return results
    
    async def _execute_sequential_plan(self, plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute sequential plan with dependency handling"""
        return await self.executor.execute_sequential(plan)
    
    def _convert_legacy_plan(self, legacy_plan: List[str], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert legacy plan format to new execution plan format"""
        execution_plan = []
        
        for i, action in enumerate(legacy_plan):
            step_id = f"step_{i+1}"
            
            # Try to map legacy actions to agent capabilities
            if action in ["search_mail", "process_results"]:
                execution_plan.append({
                    "step_id": step_id,
                    "action": action,
                    "agent_id": "mail-agent",
                    "capability": "messages.search",
                    "parameters": {"query": state['user_input'], "limit": 10},
                    "dependencies": []
                })
            elif action in ["check_calendar", "propose_event"]:
                execution_plan.append({
                    "step_id": step_id,
                    "action": action,
                    "agent_id": None,  # No calendar agent yet
                    "capability": None,
                    "parameters": {"query": state['user_input']},
                    "dependencies": []
                })
            else:
                execution_plan.append({
                    "step_id": step_id,
                    "action": action,
                    "agent_id": None,
                    "capability": None,
                    "parameters": {"query": state['user_input']},
                    "dependencies": []
                })
        
        return execution_plan
    
    def _extract_action_from_step_id(self, step_id: str, execution_plan: List[Dict[str, Any]]) -> str:
        """Extract action name from step_id for legacy compatibility"""
        for step in execution_plan:
            if step.get('step_id') == step_id:
                return step.get('action', step_id)
        return step_id
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.executor.close()