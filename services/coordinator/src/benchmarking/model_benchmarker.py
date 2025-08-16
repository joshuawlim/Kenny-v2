import asyncio
import time
import logging
import json
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage
import httpx

logger = logging.getLogger(__name__)

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_name: str
    avg_response_time: float
    tool_calling_accuracy: float
    success_rate: float
    total_queries: int
    errors: List[str]
    detailed_results: List[Dict[str, Any]]

class ModelBenchmarker:
    """Automated benchmarking framework for model comparison"""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        # Test models to benchmark
        self.test_models = [
            "llama3.2:3b-instruct",  # Current agent model
            "qwen2.5:3b-instruct",   # Lightweight alternative
            "qwen3:8b"               # Current baseline
        ]
        
        # Comprehensive test scenarios
        self.test_scenarios = [
            # Simple routing queries
            {
                "query": "check my email",
                "expected_intent": "mail_operation",
                "complexity": "simple",
                "category": "routing"
            },
            {
                "query": "find my contacts", 
                "expected_intent": "contacts_operation",
                "complexity": "simple",
                "category": "routing"
            },
            {
                "query": "show my calendar",
                "expected_intent": "calendar_operation",
                "complexity": "simple", 
                "category": "routing"
            },
            
            # Complex multi-agent queries
            {
                "query": "find emails from Sarah about project X and schedule follow-up meeting",
                "expected_intent": "mail_operation",
                "complexity": "complex",
                "category": "multi_agent"
            },
            {
                "query": "search messages from John about quarterly review and check if he's available tomorrow",
                "expected_intent": "messages_operation",
                "complexity": "complex",
                "category": "multi_agent"
            },
            {
                "query": "find contact info for the CEO of TechCorp and schedule a meeting next week",
                "expected_intent": "contacts_operation",
                "complexity": "complex",
                "category": "multi_agent"
            },
            
            # Edge cases and error handling
            {
                "query": "help me with xyz unknown thing",
                "expected_intent": "general_query",
                "complexity": "ambiguous",
                "category": "edge_case"
            },
            {
                "query": "find email from someone about something last week maybe",
                "expected_intent": "mail_operation",
                "complexity": "ambiguous",
                "category": "edge_case"
            },
            {
                "query": "asdf qwerty 12345",
                "expected_intent": "general_query",
                "complexity": "nonsense",
                "category": "edge_case"
            },
            
            # Tool calling accuracy tests
            {
                "query": "get me the last 5 emails from inbox",
                "expected_intent": "mail_operation",
                "expected_tools": ["messages.search"],
                "complexity": "specific",
                "category": "tool_calling"
            },
            {
                "query": "find contact for Alice Johnson",
                "expected_intent": "contacts_operation",
                "expected_tools": ["contacts.resolve"],
                "complexity": "specific",
                "category": "tool_calling"
            },
            {
                "query": "remember that I prefer morning meetings",
                "expected_intent": "memory_operation",
                "expected_tools": ["memory.store"],
                "complexity": "specific",
                "category": "tool_calling"
            }
        ]
    
    async def benchmark_all_models(self) -> Dict[str, ModelPerformance]:
        """Benchmark all test models across all scenarios"""
        logger.info(f"Starting comprehensive model benchmarking for {len(self.test_models)} models")
        
        results = {}
        
        for model_name in self.test_models:
            logger.info(f"Benchmarking model: {model_name}")
            try:
                performance = await self.benchmark_model(model_name)
                results[model_name] = performance
                logger.info(f"Completed benchmarking {model_name}: {performance.avg_response_time:.2f}s avg, {performance.tool_calling_accuracy:.2f} accuracy")
            except Exception as e:
                logger.error(f"Failed to benchmark {model_name}: {e}")
                results[model_name] = ModelPerformance(
                    model_name=model_name,
                    avg_response_time=float('inf'),
                    tool_calling_accuracy=0.0,
                    success_rate=0.0,
                    total_queries=0,
                    errors=[str(e)],
                    detailed_results=[]
                )
        
        return results
    
    async def benchmark_model(self, model_name: str) -> ModelPerformance:
        """Benchmark a specific model across all test scenarios"""
        # Check if model is available
        if not await self._is_model_available(model_name):
            raise ValueError(f"Model {model_name} is not available in Ollama")
        
        # Initialize model
        llm = ChatOllama(
            model=model_name,
            temperature=0.1,
            base_url=self.ollama_base_url
        )
        
        results = []
        response_times = []
        successful_queries = 0
        errors = []
        
        for scenario in self.test_scenarios:
            try:
                start_time = time.time()
                
                # Run the test
                result = await self._test_scenario(llm, scenario)
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Evaluate accuracy
                accuracy_score = self._evaluate_accuracy(result, scenario)
                
                detailed_result = {
                    "scenario": scenario,
                    "result": result,
                    "response_time": response_time,
                    "accuracy_score": accuracy_score,
                    "success": result is not None
                }
                
                results.append(detailed_result)
                
                if result is not None:
                    successful_queries += 1
                    
                logger.debug(f"Model {model_name} - Query: '{scenario['query']}' - Time: {response_time:.2f}s - Accuracy: {accuracy_score:.2f}")
                
            except Exception as e:
                logger.error(f"Error testing scenario '{scenario['query']}' with {model_name}: {e}")
                errors.append(f"Scenario '{scenario['query']}': {str(e)}")
                results.append({
                    "scenario": scenario,
                    "result": None,
                    "response_time": float('inf'),
                    "accuracy_score": 0.0,
                    "success": False,
                    "error": str(e)
                })
        
        # Calculate overall metrics
        avg_response_time = sum(response_times) / len(response_times) if response_times else float('inf')
        success_rate = successful_queries / len(self.test_scenarios)
        tool_calling_accuracy = sum(r["accuracy_score"] for r in results if r["success"]) / max(successful_queries, 1)
        
        return ModelPerformance(
            model_name=model_name,
            avg_response_time=avg_response_time,
            tool_calling_accuracy=tool_calling_accuracy,
            success_rate=success_rate,
            total_queries=len(self.test_scenarios),
            errors=errors,
            detailed_results=results
        )
    
    async def _test_scenario(self, llm: ChatOllama, scenario: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Test a single scenario with the given model"""
        system_prompt = self._build_system_prompt()
        human_prompt = f"User request: {scenario['query']}"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            response = await llm.ainvoke(messages)
            
            # Parse JSON response
            import re
            cleaned_response = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()
            
            json_match = re.search(r'\{.*\}', cleaned_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Try parsing the entire response
                return json.loads(cleaned_response)
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response: {response.content}")
            return None
        except Exception as e:
            logger.error(f"Model invocation failed: {e}")
            return None
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for intent classification testing"""
        return """You are an intelligent request router for Kenny v2.1, a multi-agent personal assistant.

Available agents and capabilities:
- intelligent-mail-agent: messages.search, messages.read, messages.propose_reply, messages.analyze, messages.categorize
- intelligent-contacts-agent: contacts.resolve, contacts.enrich, contacts.merge
- intelligent-imessage-agent: messages.search, messages.read, messages.analyze, conversations.summarize
- intelligent-calendar-agent: calendar.read, calendar.propose_event, calendar.smart_schedule, calendar.conflict_resolve
- memory-agent: memory.retrieve, memory.store, memory.embed

Your role is to interpret queries and route them to appropriate agents with confidence scoring.

Respond in JSON format:
{
    "primary_intent": "mail_operation|contacts_operation|messages_operation|calendar_operation|memory_operation|general_query",
    "confidence": 0.0-1.0,
    "interpretation": "Clear explanation of interpretation",
    "required_agents": [
        {
            "agent_id": "agent_name",
            "capabilities": ["capability1"],
            "priority": 1,
            "confidence": 0.0-1.0
        }
    ],
    "execution_strategy": "single_agent|multi_agent|sequential",
    "reasoning": "Detailed explanation of routing decision"
}"""
    
    def _evaluate_accuracy(self, result: Optional[Dict[str, Any]], scenario: Dict[str, Any]) -> float:
        """Evaluate the accuracy of the model's response"""
        if result is None:
            return 0.0
        
        accuracy_score = 0.0
        max_score = 4.0  # Total possible points
        
        # 1. Intent accuracy (1 point)
        expected_intent = scenario.get("expected_intent", "")
        actual_intent = result.get("primary_intent", "")
        if expected_intent and actual_intent == expected_intent:
            accuracy_score += 1.0
        elif expected_intent and actual_intent.replace("_operation", "") in expected_intent:
            accuracy_score += 0.5  # Partial credit
        
        # 2. Confidence score reasonableness (1 point)
        confidence = result.get("confidence", 0.0)
        if isinstance(confidence, (int, float)) and 0.0 <= confidence <= 1.0:
            if scenario.get("complexity") == "simple" and confidence >= 0.7:
                accuracy_score += 1.0
            elif scenario.get("complexity") == "complex" and confidence >= 0.5:
                accuracy_score += 1.0
            elif scenario.get("complexity") == "ambiguous" and confidence <= 0.6:
                accuracy_score += 1.0
            else:
                accuracy_score += 0.5  # Partial credit for valid range
        
        # 3. Required agents appropriateness (1 point)
        required_agents = result.get("required_agents", [])
        if required_agents and isinstance(required_agents, list):
            for agent in required_agents:
                if isinstance(agent, dict) and "agent_id" in agent and "capabilities" in agent:
                    accuracy_score += 0.5
                    if len(required_agents) <= 2:  # Reasonable number of agents
                        accuracy_score += 0.5
                    break
        
        # 4. Tool calling accuracy (1 point)
        expected_tools = scenario.get("expected_tools", [])
        if expected_tools:
            actual_tools = []
            for agent in required_agents:
                if isinstance(agent, dict):
                    actual_tools.extend(agent.get("capabilities", []))
            
            matching_tools = set(expected_tools) & set(actual_tools)
            if matching_tools:
                accuracy_score += len(matching_tools) / len(expected_tools)
        else:
            # If no specific tools expected, give partial credit for having any tools
            if any(agent.get("capabilities") for agent in required_agents if isinstance(agent, dict)):
                accuracy_score += 0.5
        
        return min(accuracy_score / max_score, 1.0)  # Normalize to 0-1
    
    async def _is_model_available(self, model_name: str) -> bool:
        """Check if model is available in Ollama"""
        try:
            response = await self.http_client.get(f"{self.ollama_base_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                model_names = [model.get("name", "") for model in models.get("models", [])]
                return any(model_name in name for name in model_names)
            return False
        except Exception as e:
            logger.error(f"Failed to check model availability: {e}")
            return False
    
    def generate_report(self, results: Dict[str, ModelPerformance]) -> str:
        """Generate a comprehensive benchmarking report"""
        report = ["\n=== MODEL BENCHMARKING REPORT ==="]
        report.append(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Models Tested: {len(results)}")
        report.append(f"Total Test Scenarios: {len(self.test_scenarios)}")
        report.append("")
        
        # Overall comparison
        report.append("=== OVERALL PERFORMANCE COMPARISON ===")
        sorted_models = sorted(results.items(), key=lambda x: x[1].avg_response_time)
        
        for rank, (model_name, perf) in enumerate(sorted_models, 1):
            report.append(f"{rank}. {model_name}:")
            report.append(f"   Average Response Time: {perf.avg_response_time:.2f}s")
            report.append(f"   Tool Calling Accuracy: {perf.tool_calling_accuracy:.1%}")
            report.append(f"   Success Rate: {perf.success_rate:.1%}")
            report.append(f"   Errors: {len(perf.errors)}")
            report.append("")
        
        # Detailed breakdown by category
        report.append("=== PERFORMANCE BY CATEGORY ===")
        categories = set(scenario["category"] for scenario in self.test_scenarios)
        
        for category in categories:
            report.append(f"\n{category.upper()} QUERIES:")
            category_scenarios = [s for s in self.test_scenarios if s["category"] == category]
            
            for model_name, perf in results.items():
                category_results = [
                    r for r in perf.detailed_results 
                    if r["scenario"]["category"] == category
                ]
                
                if category_results:
                    avg_time = sum(r["response_time"] for r in category_results) / len(category_results)
                    avg_accuracy = sum(r["accuracy_score"] for r in category_results) / len(category_results)
                    report.append(f"  {model_name}: {avg_time:.2f}s, {avg_accuracy:.1%} accuracy")
        
        # Recommendations
        report.append("\n=== RECOMMENDATIONS ===")
        
        best_overall = min(results.items(), key=lambda x: x[1].avg_response_time)
        best_accuracy = max(results.items(), key=lambda x: x[1].tool_calling_accuracy)
        
        report.append(f"Fastest Model: {best_overall[0]} ({best_overall[1].avg_response_time:.2f}s avg)")
        report.append(f"Most Accurate Model: {best_accuracy[0]} ({best_accuracy[1].tool_calling_accuracy:.1%} accuracy)")
        
        # Find best balance
        balanced_scores = {}
        for model_name, perf in results.items():
            # Score based on speed (lower is better) and accuracy (higher is better)
            speed_score = 1.0 / (1.0 + perf.avg_response_time)  # Normalize speed
            accuracy_score = perf.tool_calling_accuracy
            balanced_scores[model_name] = (speed_score + accuracy_score) / 2
        
        best_balanced = max(balanced_scores.items(), key=lambda x: x[1])
        report.append(f"Best Balanced Model: {best_balanced[0]} (score: {best_balanced[1]:.2f})")
        
        # Performance improvement recommendations
        report.append("\nPERFORMANCE OPTIMIZATION SUGGESTIONS:")
        if best_overall[1].avg_response_time < 5.0:
            report.append(f"✅ Target <5s response time achievable with {best_overall[0]}")
        else:
            report.append("❌ None of the tested models achieve <5s target consistently")
            report.append("   Consider: Model optimization, caching, or infrastructure improvements")
        
        return "\n".join(report)
    
    async def cleanup(self):
        """Cleanup resources"""
        await self.http_client.aclose()