import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import re
from langchain_ollama import ChatOllama
from langchain.schema import HumanMessage, SystemMessage

from .benchmarking.performance_metrics import PerformanceMetrics
from .benchmarking.ab_testing import ABTesting, ABTestConfig

logger = logging.getLogger(__name__)

class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"           # Single intent, clear keywords
    MODERATE = "moderate"       # Multi-step or some ambiguity
    COMPLEX = "complex"         # Multi-agent, complex reasoning
    AMBIGUOUS = "ambiguous"     # Unclear intent, requires interpretation

@dataclass
class ModelConfig:
    """Model configuration with performance characteristics"""
    name: str
    avg_response_time: float
    accuracy_score: float
    max_complexity: QueryComplexity
    cost_per_request: float = 0.0
    availability_score: float = 1.0
    
class ModelRouter:
    """Dynamic model router with query complexity analysis and model selection"""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.performance_metrics = PerformanceMetrics()
        self.ab_testing = ABTesting()
        
        # Model configurations based on benchmarking
        self.models = {
            "llama3.2:3b-instruct": ModelConfig(
                name="llama3.2:3b-instruct",
                avg_response_time=2.1,  # Fastest
                accuracy_score=0.85,
                max_complexity=QueryComplexity.MODERATE,
                cost_per_request=0.001
            ),
            "qwen2.5:3b-instruct": ModelConfig(
                name="qwen2.5:3b-instruct", 
                avg_response_time=2.8,  # Good balance
                accuracy_score=0.88,
                max_complexity=QueryComplexity.COMPLEX,
                cost_per_request=0.002
            ),
            "qwen3:8b": ModelConfig(
                name="qwen3:8b",
                avg_response_time=12.5,  # Slowest but most accurate
                accuracy_score=0.92,
                max_complexity=QueryComplexity.COMPLEX,
                cost_per_request=0.005
            )
        }
        
        # Fallback mechanisms
        self.fallback_chain = [
            "llama3.2:3b-instruct",
            "qwen2.5:3b-instruct", 
            "qwen3:8b"
        ]
        
        # Current active model
        self.current_model = "qwen2.5:3b-instruct"  # Start with balanced option
        
        # Caching for model availability
        self._model_availability = {}
        self._availability_check_time = 0
        self._availability_cache_ttl = 300  # 5 minutes
        
    async def route_query(self, query: str, context: Dict[str, Any] = None) -> Tuple[str, Dict[str, Any]]:
        """Route query to optimal model based on complexity analysis"""
        request_id = f"req_{int(time.time() * 1000)}"
        
        try:
            # Analyze query complexity
            complexity_analysis = await self._analyze_query_complexity(query, context or {})
            
            # Select optimal model
            selected_model, selection_reasoning = await self._select_optimal_model(
                complexity_analysis, context or {}
            )
            
            # Check if we're in an A/B test
            active_tests = self.ab_testing.get_active_tests()
            if active_tests:
                test = active_tests[0]  # Use first active test
                test_id = test["test_id"]
                if self.ab_testing.should_use_treatment(test_id, context):
                    selected_model = test["treatment_model"]
                    selection_reasoning["ab_test"] = test_id
                else:
                    selected_model = test["control_model"]
                    selection_reasoning["ab_test"] = f"{test_id}_control"
            
            # Start performance tracking
            self.performance_metrics.start_request(request_id, selected_model, query)
            
            routing_info = {
                "request_id": request_id,
                "selected_model": selected_model,
                "complexity_analysis": complexity_analysis,
                "selection_reasoning": selection_reasoning,
                "fallback_models": self._get_fallback_models(selected_model),
                "estimated_response_time": self.models[selected_model].avg_response_time
            }
            
            logger.info(f"Routed query to {selected_model} (complexity: {complexity_analysis['complexity'].value})")
            return selected_model, routing_info
            
        except Exception as e:
            logger.error(f"Model routing failed: {e}")
            # Use default model as fallback
            fallback_model = self.fallback_chain[0]
            self.performance_metrics.start_request(request_id, fallback_model, query)
            
            return fallback_model, {
                "request_id": request_id,
                "selected_model": fallback_model,
                "error": str(e),
                "fallback_reason": "routing_error"
            }
    
    async def _analyze_query_complexity(self, query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze query complexity using multiple heuristics"""
        complexity_scores = {}
        
        # 1. Length and structure analysis
        complexity_scores["length"] = self._analyze_length_complexity(query)
        
        # 2. Keyword and intent analysis  
        complexity_scores["keywords"] = self._analyze_keyword_complexity(query)
        
        # 3. Multi-agent requirement analysis
        complexity_scores["multi_agent"] = self._analyze_multi_agent_complexity(query)
        
        # 4. Ambiguity detection
        complexity_scores["ambiguity"] = self._analyze_ambiguity(query)
        
        # 5. Context dependency
        complexity_scores["context_dependency"] = self._analyze_context_dependency(query, context)
        
        # Calculate overall complexity
        overall_complexity = self._calculate_overall_complexity(complexity_scores)
        
        return {
            "complexity": overall_complexity,
            "scores": complexity_scores,
            "confidence": self._calculate_complexity_confidence(complexity_scores),
            "reasoning": self._generate_complexity_reasoning(complexity_scores, overall_complexity)
        }
    
    def _analyze_length_complexity(self, query: str) -> float:
        """Analyze complexity based on query length and structure"""
        words = len(query.split())
        sentences = len(re.split(r'[.!?]+', query.strip()))
        
        # Simple heuristics
        if words <= 5 and sentences == 1:
            return 0.2  # Very simple
        elif words <= 10 and sentences <= 2:
            return 0.4  # Simple
        elif words <= 20 and sentences <= 3:
            return 0.6  # Moderate
        else:
            return 0.8  # Complex
    
    def _analyze_keyword_complexity(self, query: str) -> float:
        """Analyze complexity based on keywords and intent patterns"""
        query_lower = query.lower()
        
        # Simple action keywords
        simple_patterns = [
            r'\b(show|get|find|check)\s+my\s+(email|calendar|contacts?)\b',
            r'\b(search|list)\s+(email|message|contact)s?\b',
            r'\b(read|open)\s+.*\b'
        ]
        
        # Complex patterns
        complex_patterns = [
            r'\b(find|search)\s+.*\s+(and|then)\s+(schedule|create|send)\b',
            r'\b(compare|analyze|summarize)\b',
            r'\b(if|when|unless|provided|based\s+on)\b'
        ]
        
        # Multi-step indicators
        multi_step_patterns = [
            r'\b(then|after|next|also|additionally)\b',
            r'\b(and\s+then|and\s+also)\b'
        ]
        
        score = 0.3  # Base score
        
        for pattern in simple_patterns:
            if re.search(pattern, query_lower):
                score = max(score, 0.2)
                break
        
        for pattern in complex_patterns:
            if re.search(pattern, query_lower):
                score = max(score, 0.7)
                
        for pattern in multi_step_patterns:
            if re.search(pattern, query_lower):
                score = max(score, 0.6)
                
        return score
    
    def _analyze_multi_agent_complexity(self, query: str) -> float:
        """Analyze if query requires multiple agents"""
        query_lower = query.lower()
        
        # Different agent domains mentioned
        agent_domains = {
            "email": ["email", "mail", "inbox", "message"],
            "calendar": ["calendar", "schedule", "meeting", "appointment", "event"],
            "contacts": ["contact", "person", "phone", "address"],
            "messages": ["text", "imessage", "chat", "message"],
            "memory": ["remember", "recall", "note", "store"]
        }
        
        domains_mentioned = 0
        for domain, keywords in agent_domains.items():
            if any(keyword in query_lower for keyword in keywords):
                domains_mentioned += 1
        
        if domains_mentioned >= 3:
            return 0.9  # Very complex
        elif domains_mentioned == 2:
            return 0.6  # Moderate complexity
        else:
            return 0.2  # Single domain
    
    def _analyze_ambiguity(self, query: str) -> float:
        """Detect ambiguous or unclear queries"""
        query_lower = query.lower()
        
        # Ambiguity indicators
        ambiguous_patterns = [
            r'\b(something|anything|stuff|thing|someone|somebody)\b',
            r'\b(maybe|perhaps|possibly|might|could)\b',
            r'\b(not\s+sure|don\'t\s+know|unclear)\b',
            r'\b(help|assist)\s+(me\s+)?with\b',
            r'^(um|uh|well|so)\b'
        ]
        
        # Vague time references
        vague_time_patterns = [
            r'\b(sometime|recently|later|soon|eventually)\b',
            r'\b(the\s+other\s+day|last\s+week|next\s+week)\b'
        ]
        
        score = 0.1  # Base score
        
        for pattern in ambiguous_patterns:
            if re.search(pattern, query_lower):
                score += 0.2
                
        for pattern in vague_time_patterns:
            if re.search(pattern, query_lower):
                score += 0.1
        
        # Very short queries are often ambiguous
        if len(query.split()) <= 3:
            score += 0.1
            
        return min(score, 1.0)
    
    def _analyze_context_dependency(self, query: str, context: Dict[str, Any]) -> float:
        """Analyze how much the query depends on context"""
        # Pronouns and references that need context
        reference_patterns = [
            r'\b(this|that|these|those|it|them)\b',
            r'\b(he|she|they|him|her)\b',
            r'\b(the\s+one|the\s+person|the\s+email)\b'
        ]
        
        score = 0.1
        for pattern in reference_patterns:
            if re.search(pattern, query.lower()):
                score += 0.2
        
        # Check if context is available
        if context:
            # Rich context reduces complexity
            context_richness = len(context.keys())
            if context_richness > 3:
                score *= 0.7  # Reduce complexity if good context available
        
        return min(score, 1.0)
    
    def _calculate_overall_complexity(self, scores: Dict[str, float]) -> QueryComplexity:
        """Calculate overall complexity from individual scores"""
        # Weighted average of complexity scores
        weights = {
            "length": 0.15,
            "keywords": 0.25,
            "multi_agent": 0.30,
            "ambiguity": 0.20,
            "context_dependency": 0.10
        }
        
        weighted_score = sum(scores[key] * weights[key] for key in scores.keys() if key in weights)
        
        # Map to complexity levels
        if weighted_score <= 0.3:
            return QueryComplexity.SIMPLE
        elif weighted_score <= 0.5:
            return QueryComplexity.MODERATE
        elif weighted_score <= 0.7:
            return QueryComplexity.COMPLEX
        else:
            return QueryComplexity.AMBIGUOUS
    
    def _calculate_complexity_confidence(self, scores: Dict[str, float]) -> float:
        """Calculate confidence in complexity assessment"""
        # Higher variance in scores = lower confidence
        score_values = list(scores.values())
        if len(score_values) <= 1:
            return 0.5
        
        mean_score = sum(score_values) / len(score_values)
        variance = sum((score - mean_score) ** 2 for score in score_values) / len(score_values)
        
        # Convert variance to confidence (lower variance = higher confidence)
        confidence = max(0.5, 1.0 - (variance * 2))
        return confidence
    
    def _generate_complexity_reasoning(self, scores: Dict[str, float], complexity: QueryComplexity) -> str:
        """Generate human-readable reasoning for complexity assessment"""
        reasons = []
        
        if scores.get("length", 0) > 0.6:
            reasons.append("long/multi-sentence query")
        if scores.get("keywords", 0) > 0.6:
            reasons.append("complex action patterns")
        if scores.get("multi_agent", 0) > 0.5:
            reasons.append("multiple agent domains")
        if scores.get("ambiguity", 0) > 0.4:
            reasons.append("ambiguous language")
        if scores.get("context_dependency", 0) > 0.4:
            reasons.append("context-dependent references")
        
        if not reasons:
            reasons = ["simple direct query"]
        
        return f"Classified as {complexity.value}: {', '.join(reasons)}"
    
    async def _select_optimal_model(self, complexity_analysis: Dict[str, Any], 
                                   context: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Select optimal model based on complexity and performance requirements"""
        complexity = complexity_analysis["complexity"]
        confidence = complexity_analysis["confidence"]
        
        # Get current performance snapshot
        perf_snapshot = self.performance_metrics.get_current_snapshot()
        
        # Check model availability
        available_models = await self._get_available_models()
        
        selection_reasoning = {
            "complexity": complexity.value,
            "confidence": confidence,
            "available_models": available_models,
            "performance_snapshot": {
                "avg_response_time": perf_snapshot.avg_response_time,
                "success_rate": perf_snapshot.success_rate
            }
        }
        
        # Performance-first selection for simple queries
        if complexity == QueryComplexity.SIMPLE:
            # Use fastest available model
            for model_name in ["llama3.2:3b-instruct", "qwen2.5:3b-instruct", "qwen3:8b"]:
                if model_name in available_models:
                    selection_reasoning["strategy"] = "speed_optimized"
                    selection_reasoning["reason"] = f"Simple query routed to fastest model: {model_name}"
                    return model_name, selection_reasoning
        
        # Balanced selection for moderate complexity
        elif complexity == QueryComplexity.MODERATE:
            # Check if we're meeting performance targets
            if perf_snapshot.avg_response_time > 5.0:
                # Performance degraded, prefer speed
                if "llama3.2:3b-instruct" in available_models:
                    selection_reasoning["strategy"] = "performance_recovery"
                    selection_reasoning["reason"] = "Performance degraded, using fastest model"
                    return "llama3.2:3b-instruct", selection_reasoning
            
            # Normal case: use balanced model
            if "qwen2.5:3b-instruct" in available_models:
                selection_reasoning["strategy"] = "balanced"
                selection_reasoning["reason"] = "Moderate complexity, using balanced model"
                return "qwen2.5:3b-instruct", selection_reasoning
        
        # Accuracy-first selection for complex/ambiguous queries
        else:  # COMPLEX or AMBIGUOUS
            # Only use slow model if performance is currently good
            if perf_snapshot.avg_response_time <= 3.0 and perf_snapshot.success_rate >= 0.95:
                if "qwen3:8b" in available_models:
                    selection_reasoning["strategy"] = "accuracy_optimized"
                    selection_reasoning["reason"] = "Complex query, good performance allows accurate model"
                    return "qwen3:8b", selection_reasoning
            
            # Fallback to balanced model for complex queries when performance is poor
            if "qwen2.5:3b-instruct" in available_models:
                selection_reasoning["strategy"] = "complexity_fallback"
                selection_reasoning["reason"] = "Complex query but performance constraints require balanced model"
                return "qwen2.5:3b-instruct", selection_reasoning
        
        # Final fallback to any available model
        if available_models:
            fallback_model = available_models[0]
            selection_reasoning["strategy"] = "availability_fallback"
            selection_reasoning["reason"] = f"Using available model: {fallback_model}"
            return fallback_model, selection_reasoning
        
        # Ultimate fallback
        ultimate_fallback = "llama3.2:3b-instruct"
        selection_reasoning["strategy"] = "ultimate_fallback"
        selection_reasoning["reason"] = "No models available, using default"
        return ultimate_fallback, selection_reasoning
    
    async def _get_available_models(self) -> List[str]:
        """Get list of currently available models"""
        current_time = time.time()
        
        # Use cached availability if recent
        if current_time - self._availability_check_time < self._availability_cache_ttl:
            return [model for model, available in self._model_availability.items() if available]
        
        # Check model availability
        available_models = []
        for model_name in self.models.keys():
            try:
                # Quick availability check (could be enhanced with actual Ollama API call)
                available_models.append(model_name)
                self._model_availability[model_name] = True
            except Exception as e:
                logger.warning(f"Model {model_name} unavailable: {e}")
                self._model_availability[model_name] = False
        
        self._availability_check_time = current_time
        return available_models
    
    def _get_fallback_models(self, selected_model: str) -> List[str]:
        """Get fallback models in order of preference"""
        fallbacks = [model for model in self.fallback_chain if model != selected_model]
        return fallbacks
    
    def record_performance(self, request_id: str, success: bool, response_time: float, 
                         accuracy: Optional[float] = None, error: Optional[str] = None) -> None:
        """Record performance metrics for a completed request"""
        self.performance_metrics.end_request(
            request_id=request_id,
            success=success,
            confidence=accuracy,
            accuracy=accuracy,
            error=error
        )
        
        # Also record for A/B tests if active
        active_tests = self.ab_testing.get_active_tests()
        if active_tests:
            test = active_tests[0]
            test_id = test["test_id"]
            model_name = self.performance_metrics.current_model
            
            self.ab_testing.record_result(
                test_id=test_id,
                model_name=model_name,
                response_time=response_time,
                accuracy=accuracy or 0.0,
                success=success,
                error=error
            )
    
    def start_ab_test(self, control_model: str, treatment_model: str, 
                     test_name: str = "model_comparison") -> str:
        """Start an A/B test between two models"""
        config = ABTestConfig(
            test_name=test_name,
            control_model=control_model,
            treatment_model=treatment_model,
            traffic_split=0.5,
            min_samples=50,
            max_duration_hours=12
        )
        
        test_id = self.ab_testing.setup_test(config)
        self.ab_testing.start_test(test_id)
        
        logger.info(f"Started A/B test {test_id}: {control_model} vs {treatment_model}")
        return test_id
    
    def get_performance_report(self) -> str:
        """Get comprehensive performance report"""
        return self.performance_metrics.generate_performance_report()
    
    def get_model_comparison(self) -> Dict[str, Dict[str, float]]:
        """Get model performance comparison"""
        return self.performance_metrics.get_model_performance_comparison()