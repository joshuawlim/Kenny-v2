import asyncio
import time
import logging
import random
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import statistics

logger = logging.getLogger(__name__)

class TestPhase(Enum):
    """A/B test phases"""
    SETUP = "setup"
    RUNNING = "running"
    ANALYSIS = "analysis"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

@dataclass
class ABTestConfig:
    """A/B test configuration"""
    test_name: str
    control_model: str
    treatment_model: str
    traffic_split: float = 0.5  # Percentage of traffic to treatment
    min_samples: int = 100
    max_duration_hours: int = 24
    significance_threshold: float = 0.05
    performance_metrics: List[str] = None
    
    def __post_init__(self):
        if self.performance_metrics is None:
            self.performance_metrics = ["response_time", "accuracy", "success_rate"]

@dataclass
class ABTestResult:
    """A/B test result data"""
    model_name: str
    sample_count: int
    avg_response_time: float
    avg_accuracy: float
    success_rate: float
    p95_response_time: float
    error_count: int
    detailed_metrics: Dict[str, Any]

@dataclass
class ABTestOutcome:
    """Final A/B test outcome"""
    test_name: str
    winner: str
    confidence: float
    improvement: Dict[str, float]  # Percentage improvements
    recommendation: str
    control_results: ABTestResult
    treatment_results: ABTestResult
    statistical_significance: Dict[str, bool]

class ABTesting:
    """Real-time A/B testing infrastructure for model comparison"""
    
    def __init__(self):
        self.active_tests: Dict[str, Dict[str, Any]] = {}
        self.test_history: List[ABTestOutcome] = []
        self.model_router: Optional[Callable] = None
        
    def setup_test(self, config: ABTestConfig) -> str:
        """Setup a new A/B test"""
        test_id = f"{config.test_name}_{int(time.time())}"
        
        self.active_tests[test_id] = {
            "config": config,
            "phase": TestPhase.SETUP,
            "start_time": time.time(),
            "control_samples": [],
            "treatment_samples": [],
            "control_errors": [],
            "treatment_errors": []
        }
        
        logger.info(f"A/B test '{test_id}' setup complete: {config.control_model} vs {config.treatment_model}")
        return test_id
    
    def start_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        if test_id not in self.active_tests:
            logger.error(f"Test {test_id} not found")
            return False
        
        test = self.active_tests[test_id]
        test["phase"] = TestPhase.RUNNING
        test["actual_start_time"] = time.time()
        
        logger.info(f"A/B test '{test_id}' started")
        return True
    
    def should_use_treatment(self, test_id: str, user_context: Optional[Dict[str, Any]] = None) -> bool:
        """Determine if a request should use treatment model"""
        if test_id not in self.active_tests:
            return False
        
        test = self.active_tests[test_id]
        if test["phase"] != TestPhase.RUNNING:
            return False
        
        config = test["config"]
        
        # Simple random traffic split
        return random.random() < config.traffic_split
    
    def record_result(self, test_id: str, model_name: str, response_time: float, 
                     accuracy: float, success: bool, error: Optional[str] = None,
                     additional_metrics: Optional[Dict[str, Any]] = None) -> None:
        """Record a test result"""
        if test_id not in self.active_tests:
            logger.warning(f"Recording result for unknown test {test_id}")
            return
        
        test = self.active_tests[test_id]
        config = test["config"]
        
        result_data = {
            "timestamp": time.time(),
            "response_time": response_time,
            "accuracy": accuracy,
            "success": success,
            "error": error,
            "additional_metrics": additional_metrics or {}
        }
        
        # Determine which group this belongs to
        if model_name == config.control_model:
            test["control_samples"].append(result_data)
            if error:
                test["control_errors"].append(error)
        elif model_name == config.treatment_model:
            test["treatment_samples"].append(result_data)
            if error:
                test["treatment_errors"].append(error)
        else:
            logger.warning(f"Unknown model {model_name} for test {test_id}")
            return
        
        # Check if test should be analyzed
        if self._should_analyze_test(test_id):
            self._analyze_test(test_id)
    
    def _should_analyze_test(self, test_id: str) -> bool:
        """Check if test has enough data for analysis"""
        test = self.active_tests[test_id]
        config = test["config"]
        
        control_count = len(test["control_samples"])
        treatment_count = len(test["treatment_samples"])
        
        # Check minimum sample size
        if control_count < config.min_samples or treatment_count < config.min_samples:
            return False
        
        # Check maximum duration
        if "actual_start_time" in test:
            elapsed_hours = (time.time() - test["actual_start_time"]) / 3600
            if elapsed_hours >= config.max_duration_hours:
                return True
        
        # Check for early statistical significance every 50 samples
        if (control_count + treatment_count) % 50 == 0:
            return True
        
        return False
    
    def _analyze_test(self, test_id: str) -> Optional[ABTestOutcome]:
        """Analyze A/B test results"""
        test = self.active_tests[test_id]
        config = test["config"]
        
        test["phase"] = TestPhase.ANALYSIS
        
        # Calculate results for both groups
        control_result = self._calculate_group_results(config.control_model, test["control_samples"])
        treatment_result = self._calculate_group_results(config.treatment_model, test["treatment_samples"])
        
        # Statistical significance testing
        significance = self._test_statistical_significance(test["control_samples"], test["treatment_samples"])
        
        # Determine winner and improvements
        winner, improvements = self._determine_winner(control_result, treatment_result)
        
        # Calculate confidence based on sample size and significance
        confidence = self._calculate_confidence(test["control_samples"], test["treatment_samples"], significance)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(winner, improvements, confidence, significance)
        
        outcome = ABTestOutcome(
            test_name=config.test_name,
            winner=winner,
            confidence=confidence,
            improvement=improvements,
            recommendation=recommendation,
            control_results=control_result,
            treatment_results=treatment_result,
            statistical_significance=significance
        )
        
        # Complete the test
        test["phase"] = TestPhase.COMPLETED
        test["outcome"] = outcome
        test["end_time"] = time.time()
        
        self.test_history.append(outcome)
        logger.info(f"A/B test '{test_id}' completed. Winner: {winner} (confidence: {confidence:.1%})")
        
        return outcome
    
    def _calculate_group_results(self, model_name: str, samples: List[Dict[str, Any]]) -> ABTestResult:
        """Calculate aggregated results for a test group"""
        if not samples:
            return ABTestResult(
                model_name=model_name,
                sample_count=0,
                avg_response_time=0.0,
                avg_accuracy=0.0,
                success_rate=0.0,
                p95_response_time=0.0,
                error_count=0,
                detailed_metrics={}
            )
        
        response_times = [s["response_time"] for s in samples]
        accuracies = [s["accuracy"] for s in samples]
        successes = [s for s in samples if s["success"]]
        
        return ABTestResult(
            model_name=model_name,
            sample_count=len(samples),
            avg_response_time=statistics.mean(response_times),
            avg_accuracy=statistics.mean(accuracies),
            success_rate=len(successes) / len(samples),
            p95_response_time=self._percentile(response_times, 0.95),
            error_count=len([s for s in samples if not s["success"]]),
            detailed_metrics={
                "median_response_time": statistics.median(response_times),
                "stddev_response_time": statistics.stdev(response_times) if len(response_times) > 1 else 0.0,
                "min_response_time": min(response_times),
                "max_response_time": max(response_times),
                "median_accuracy": statistics.median(accuracies),
                "stddev_accuracy": statistics.stdev(accuracies) if len(accuracies) > 1 else 0.0
            }
        )
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(percentile * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def _test_statistical_significance(self, control_samples: List[Dict[str, Any]], 
                                     treatment_samples: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Test statistical significance using simplified t-test approach"""
        # This is a simplified implementation. In production, you'd use proper statistical libraries
        
        def simple_ttest(control_values: List[float], treatment_values: List[float]) -> bool:
            if len(control_values) < 10 or len(treatment_values) < 10:
                return False
            
            control_mean = statistics.mean(control_values)
            treatment_mean = statistics.mean(treatment_values)
            
            # Simple significance test: if means differ by more than 10% and we have enough samples
            if len(control_values) > 30 and len(treatment_values) > 30:
                percent_diff = abs(treatment_mean - control_mean) / control_mean
                return percent_diff > 0.1  # 10% difference threshold
            
            return False
        
        control_response_times = [s["response_time"] for s in control_samples]
        treatment_response_times = [s["response_time"] for s in treatment_samples]
        
        control_accuracies = [s["accuracy"] for s in control_samples]
        treatment_accuracies = [s["accuracy"] for s in treatment_samples]
        
        return {
            "response_time": simple_ttest(control_response_times, treatment_response_times),
            "accuracy": simple_ttest(control_accuracies, treatment_accuracies),
            "success_rate": len(control_samples) > 50 and len(treatment_samples) > 50
        }
    
    def _determine_winner(self, control: ABTestResult, treatment: ABTestResult) -> Tuple[str, Dict[str, float]]:
        """Determine winner and calculate improvements"""
        # Calculate improvements (positive = treatment better, negative = control better)
        response_time_improvement = ((control.avg_response_time - treatment.avg_response_time) / control.avg_response_time) * 100
        accuracy_improvement = ((treatment.avg_accuracy - control.avg_accuracy) / control.avg_accuracy) * 100
        success_rate_improvement = ((treatment.success_rate - control.success_rate) / control.success_rate) * 100
        
        improvements = {
            "response_time": response_time_improvement,
            "accuracy": accuracy_improvement,
            "success_rate": success_rate_improvement
        }
        
        # Weighted scoring (response time is most important for our use case)
        score = (response_time_improvement * 0.5 +  # 50% weight on speed
                accuracy_improvement * 0.3 +         # 30% weight on accuracy
                success_rate_improvement * 0.2)      # 20% weight on reliability
        
        winner = treatment.model_name if score > 0 else control.model_name
        return winner, improvements
    
    def _calculate_confidence(self, control_samples: List[Dict[str, Any]], 
                            treatment_samples: List[Dict[str, Any]], 
                            significance: Dict[str, bool]) -> float:
        """Calculate confidence in the test results"""
        # Base confidence on sample size
        total_samples = len(control_samples) + len(treatment_samples)
        
        if total_samples < 100:
            base_confidence = 0.5
        elif total_samples < 500:
            base_confidence = 0.7
        elif total_samples < 1000:
            base_confidence = 0.85
        else:
            base_confidence = 0.95
        
        # Adjust based on statistical significance
        significant_metrics = sum(significance.values())
        if significant_metrics >= 2:
            base_confidence += 0.1
        elif significant_metrics == 1:
            base_confidence += 0.05
        
        # Ensure balance between groups
        control_count = len(control_samples)
        treatment_count = len(treatment_samples)
        balance_ratio = min(control_count, treatment_count) / max(control_count, treatment_count)
        
        if balance_ratio < 0.5:  # Very unbalanced
            base_confidence -= 0.2
        elif balance_ratio < 0.8:  # Somewhat unbalanced
            base_confidence -= 0.1
        
        return max(0.0, min(1.0, base_confidence))
    
    def _generate_recommendation(self, winner: str, improvements: Dict[str, float], 
                               confidence: float, significance: Dict[str, bool]) -> str:
        """Generate actionable recommendation"""
        if confidence < 0.6:
            return f"Inconclusive results. Recommend extending test or increasing sample size. Current winner: {winner}"
        
        response_time_imp = improvements["response_time"]
        accuracy_imp = improvements["accuracy"]
        
        if confidence >= 0.8 and response_time_imp > 10:
            return f"Strong recommendation: Deploy {winner}. Significant {response_time_imp:.1f}% response time improvement."
        elif confidence >= 0.7 and response_time_imp > 5:
            return f"Moderate recommendation: Consider deploying {winner}. {response_time_imp:.1f}% response time improvement."
        elif confidence >= 0.7 and accuracy_imp > 10:
            return f"Moderate recommendation: Consider deploying {winner}. {accuracy_imp:.1f}% accuracy improvement."
        else:
            return f"Weak recommendation: {winner} shows marginal improvements. Consider cost/benefit analysis."
    
    def get_test_status(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of an A/B test"""
        if test_id not in self.active_tests:
            return None
        
        test = self.active_tests[test_id]
        config = test["config"]
        
        status = {
            "test_id": test_id,
            "test_name": config.test_name,
            "phase": test["phase"].value,
            "control_model": config.control_model,
            "treatment_model": config.treatment_model,
            "control_samples": len(test["control_samples"]),
            "treatment_samples": len(test["treatment_samples"]),
            "min_samples_needed": config.min_samples,
            "progress": min(len(test["control_samples"]), len(test["treatment_samples"])) / config.min_samples
        }
        
        if "actual_start_time" in test:
            elapsed_hours = (time.time() - test["actual_start_time"]) / 3600
            status["elapsed_hours"] = elapsed_hours
            status["remaining_hours"] = max(0, config.max_duration_hours - elapsed_hours)
        
        if "outcome" in test:
            status["outcome"] = test["outcome"]
        
        return status
    
    def cancel_test(self, test_id: str, reason: str = "Manual cancellation") -> bool:
        """Cancel an active A/B test"""
        if test_id not in self.active_tests:
            return False
        
        test = self.active_tests[test_id]
        test["phase"] = TestPhase.CANCELLED
        test["cancellation_reason"] = reason
        test["end_time"] = time.time()
        
        logger.info(f"A/B test '{test_id}' cancelled: {reason}")
        return True
    
    def get_active_tests(self) -> List[Dict[str, Any]]:
        """Get all active tests"""
        return [
            self.get_test_status(test_id) 
            for test_id in self.active_tests.keys()
            if self.active_tests[test_id]["phase"] in [TestPhase.RUNNING, TestPhase.SETUP]
        ]
    
    def generate_test_report(self, test_id: str) -> str:
        """Generate comprehensive A/B test report"""
        if test_id not in self.active_tests:
            return f"Test {test_id} not found"
        
        test = self.active_tests[test_id]
        config = test["config"]
        
        report = [f"\n=== A/B TEST REPORT: {config.test_name} ==="]
        report.append(f"Test ID: {test_id}")
        report.append(f"Control Model: {config.control_model}")
        report.append(f"Treatment Model: {config.treatment_model}")
        report.append(f"Phase: {test['phase'].value}")
        report.append("")
        
        # Sample counts
        report.append("=== SAMPLE DATA ===")
        report.append(f"Control Samples: {len(test['control_samples'])}")
        report.append(f"Treatment Samples: {len(test['treatment_samples'])}")
        report.append(f"Minimum Required: {config.min_samples}")
        report.append("")
        
        # Results if available
        if "outcome" in test:
            outcome = test["outcome"]
            report.append("=== RESULTS ===")
            report.append(f"Winner: {outcome.winner}")
            report.append(f"Confidence: {outcome.confidence:.1%}")
            report.append("")
            
            report.append("Performance Improvements:")
            for metric, improvement in outcome.improvement.items():
                report.append(f"  {metric}: {improvement:+.1f}%")
            report.append("")
            
            report.append(f"Recommendation: {outcome.recommendation}")
            report.append("")
            
            # Detailed metrics
            report.append("=== DETAILED METRICS ===")
            report.append(f"Control ({outcome.control_results.model_name}):")
            report.append(f"  Avg Response Time: {outcome.control_results.avg_response_time:.2f}s")
            report.append(f"  Avg Accuracy: {outcome.control_results.avg_accuracy:.1%}")
            report.append(f"  Success Rate: {outcome.control_results.success_rate:.1%}")
            report.append("")
            
            report.append(f"Treatment ({outcome.treatment_results.model_name}):")
            report.append(f"  Avg Response Time: {outcome.treatment_results.avg_response_time:.2f}s")
            report.append(f"  Avg Accuracy: {outcome.treatment_results.avg_accuracy:.1%}")
            report.append(f"  Success Rate: {outcome.treatment_results.success_rate:.1%}")
        
        return "\n".join(report)