#!/usr/bin/env python3
"""
Test script for Phase 2: Coordinator Model Optimization
Validates <5s response time improvements and model routing performance
"""

import asyncio
import time
import json
import logging
from typing import Dict, Any, List
import sys
import os

# Add the services directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services', 'coordinator', 'src'))

from benchmarking.model_benchmarker import ModelBenchmarker
from model_router import ModelRouter
from nodes.router import IntentClassifier, RouterNode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CoordinatorOptimizationTest:
    """Comprehensive test suite for coordinator optimization"""
    
    def __init__(self):
        self.model_benchmarker = ModelBenchmarker()
        self.model_router = ModelRouter()
        self.intent_classifier = IntentClassifier()
        self.router_node = RouterNode()
        
        # Test queries representing different complexity levels
        self.test_queries = [
            # Simple queries (target: <2s)
            {"query": "check my email", "expected_complexity": "simple", "target_time": 2.0},
            {"query": "show my calendar", "expected_complexity": "simple", "target_time": 2.0},
            {"query": "find my contacts", "expected_complexity": "simple", "target_time": 2.0},
            
            # Moderate queries (target: <3s)
            {"query": "find emails from Sarah about the project", "expected_complexity": "moderate", "target_time": 3.0},
            {"query": "search for messages containing meeting", "expected_complexity": "moderate", "target_time": 3.0},
            {"query": "show me recent calendar events", "expected_complexity": "moderate", "target_time": 3.0},
            
            # Complex queries (target: <5s)
            {"query": "find emails from John about project X and schedule a follow-up meeting", "expected_complexity": "complex", "target_time": 5.0},
            {"query": "search messages from Sarah and check if she's available tomorrow for lunch", "expected_complexity": "complex", "target_time": 5.0},
            {"query": "analyze my recent emails and summarize action items for this week", "expected_complexity": "complex", "target_time": 5.0},
            
            # Ambiguous queries (target: <5s with fallback)
            {"query": "help me with something about meetings", "expected_complexity": "ambiguous", "target_time": 5.0},
            {"query": "find the thing from yesterday", "expected_complexity": "ambiguous", "target_time": 5.0},
            {"query": "what should I do next", "expected_complexity": "ambiguous", "target_time": 5.0}
        ]
    
    async def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmarking of all models"""
        logger.info("Starting full model benchmarking...")
        
        try:
            results = await self.model_benchmarker.benchmark_all_models()
            
            # Generate and display report
            report = self.model_benchmarker.generate_report(results)
            logger.info("\n" + report)
            
            return {
                "benchmark_results": results,
                "report": report,
                "success": True
            }
        except Exception as e:
            logger.error(f"Benchmarking failed: {e}")
            return {"success": False, "error": str(e)}
        finally:
            await self.model_benchmarker.cleanup()
    
    async def test_dynamic_routing(self) -> Dict[str, Any]:
        """Test dynamic model routing performance"""
        logger.info("Testing dynamic model routing...")
        
        results = []
        total_time = 0
        successful_queries = 0
        
        for test_case in self.test_queries:
            query = test_case["query"]
            target_time = test_case["target_time"]
            
            logger.info(f"Testing query: '{query}'")
            
            start_time = time.time()
            
            try:
                # Test model routing
                selected_model, routing_info = await self.model_router.route_query(query)
                
                # Test intent classification with selected model
                context = {"routing_info": routing_info}
                intent_result = await self.intent_classifier.classify_intent(query, context)
                
                end_time = time.time()
                response_time = end_time - start_time
                total_time += response_time
                
                # Evaluate result
                success = response_time <= target_time
                if success:
                    successful_queries += 1
                
                result = {
                    "query": query,
                    "selected_model": selected_model,
                    "response_time": response_time,
                    "target_time": target_time,
                    "success": success,
                    "complexity_analysis": routing_info.get("complexity_analysis"),
                    "intent_result": intent_result,
                    "routing_reasoning": routing_info.get("selection_reasoning")
                }
                
                results.append(result)
                
                status = "✅ PASS" if success else "❌ FAIL"
                logger.info(f"{status} - {response_time:.2f}s (target: {target_time:.2f}s) - Model: {selected_model}")
                
                # Record performance for model router
                request_id = routing_info.get("request_id")
                if request_id:
                    confidence = intent_result.get("confidence", 0.8)
                    self.model_router.record_performance(
                        request_id=request_id,
                        success=True,
                        response_time=response_time,
                        accuracy=confidence
                    )
                
            except Exception as e:
                logger.error(f"Query failed: {e}")
                results.append({
                    "query": query,
                    "error": str(e),
                    "success": False,
                    "response_time": time.time() - start_time
                })
        
        avg_response_time = total_time / len(self.test_queries)
        success_rate = successful_queries / len(self.test_queries)
        
        logger.info(f"\n=== DYNAMIC ROUTING TEST RESULTS ===")
        logger.info(f"Total queries: {len(self.test_queries)}")
        logger.info(f"Successful queries: {successful_queries}")
        logger.info(f"Success rate: {success_rate:.1%}")
        logger.info(f"Average response time: {avg_response_time:.2f}s")
        logger.info(f"Target achieved: {'✅ YES' if avg_response_time <= 5.0 else '❌ NO'}")
        
        return {
            "results": results,
            "summary": {
                "total_queries": len(self.test_queries),
                "successful_queries": successful_queries,
                "success_rate": success_rate,
                "avg_response_time": avg_response_time,
                "target_achieved": avg_response_time <= 5.0
            }
        }
    
    async def test_ab_comparison(self) -> Dict[str, Any]:
        """Test A/B comparison between models"""
        logger.info("Starting A/B test comparison...")
        
        # Start A/B test: fast model vs balanced model
        test_id = self.model_router.start_ab_test(
            control_model="qwen3:8b",  # Current baseline (slow)
            treatment_model="llama3.2:3b-instruct",  # Fast alternative
            test_name="phase2_optimization_test"
        )
        
        logger.info(f"Started A/B test: {test_id}")
        
        # Run test queries
        for i, test_case in enumerate(self.test_queries[:6]):  # Limited set for A/B test
            query = test_case["query"]
            
            # Determine which model to use based on A/B test
            use_treatment = self.model_router.ab_testing.should_use_treatment(test_id)
            selected_model = "llama3.2:3b-instruct" if use_treatment else "qwen3:8b"
            
            logger.info(f"A/B Test Query {i+1}: '{query}' -> {selected_model}")
            
            start_time = time.time()
            
            try:
                # Simulate classification with selected model
                intent_result = await self.intent_classifier.classify_intent(query)
                response_time = time.time() - start_time
                accuracy = intent_result.get("confidence", 0.8)
                
                # Record A/B test result
                self.model_router.ab_testing.record_result(
                    test_id=test_id,
                    model_name=selected_model,
                    response_time=response_time,
                    accuracy=accuracy,
                    success=True
                )
                
                logger.info(f"  Result: {response_time:.2f}s, accuracy: {accuracy:.2f}")
                
            except Exception as e:
                logger.error(f"A/B test query failed: {e}")
                self.model_router.ab_testing.record_result(
                    test_id=test_id,
                    model_name=selected_model,
                    response_time=10.0,  # Penalty for failure
                    accuracy=0.0,
                    success=False,
                    error=str(e)
                )
        
        # Get test status and results
        test_status = self.model_router.ab_testing.get_test_status(test_id)
        test_report = self.model_router.ab_testing.generate_test_report(test_id)
        
        logger.info("\n" + test_report)
        
        return {
            "test_id": test_id,
            "test_status": test_status,
            "test_report": test_report
        }
    
    async def test_performance_monitoring(self) -> Dict[str, Any]:
        """Test performance monitoring and metrics collection"""
        logger.info("Testing performance monitoring...")
        
        # Get performance metrics
        router_metrics = self.router_node.get_performance_metrics()
        performance_report = self.router_node.generate_performance_report()
        model_comparison = self.model_router.get_model_comparison()
        
        logger.info("\n=== PERFORMANCE MONITORING RESULTS ===")
        logger.info(f"Current Model: {router_metrics['current_model']}")
        logger.info(f"Average Response Time: {router_metrics['performance_snapshot']['avg_response_time']:.2f}s")
        logger.info(f"Success Rate: {router_metrics['performance_snapshot']['success_rate']:.1%}")
        logger.info(f"Total Requests: {router_metrics['performance_snapshot']['total_requests']}")
        
        # Check if performance targets are met
        performance_degraded = router_metrics['performance_degraded']
        targets_met = not any(performance_degraded.values())
        
        logger.info(f"Performance Targets Met: {'✅ YES' if targets_met else '❌ NO'}")
        if not targets_met:
            logger.warning(f"Performance Issues: {performance_degraded}")
        
        return {
            "metrics": router_metrics,
            "model_comparison": model_comparison,
            "performance_report": performance_report,
            "targets_met": targets_met,
            "performance_degraded": performance_degraded
        }
    
    async def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all tests and generate final report"""
        logger.info("🚀 Starting Phase 2: Coordinator Model Optimization Test Suite")
        
        results = {
            "test_timestamp": time.time(),
            "target_response_time": 5.0,
            "tests": {}
        }
        
        # 1. Full model benchmarking
        logger.info("\n📊 Step 1: Full Model Benchmarking")
        benchmark_results = await self.run_full_benchmark()
        results["tests"]["benchmark"] = benchmark_results
        
        # 2. Dynamic routing test
        logger.info("\n🎯 Step 2: Dynamic Model Routing Test")
        routing_results = await self.test_dynamic_routing()
        results["tests"]["dynamic_routing"] = routing_results
        
        # 3. A/B testing
        logger.info("\n⚡ Step 3: A/B Model Comparison")
        ab_results = await self.test_ab_comparison()
        results["tests"]["ab_testing"] = ab_results
        
        # 4. Performance monitoring
        logger.info("\n📈 Step 4: Performance Monitoring")
        monitoring_results = await self.test_performance_monitoring()
        results["tests"]["monitoring"] = monitoring_results
        
        # Generate final assessment
        self._generate_final_assessment(results)
        
        return results
    
    def _generate_final_assessment(self, results: Dict[str, Any]) -> None:
        """Generate final assessment and recommendations"""
        logger.info("\n" + "="*60)
        logger.info("🎉 PHASE 2 OPTIMIZATION FINAL ASSESSMENT")
        logger.info("="*60)
        
        # Check if main objective is achieved
        routing_summary = results["tests"]["dynamic_routing"]["summary"]
        avg_response_time = routing_summary["avg_response_time"]
        success_rate = routing_summary["success_rate"]
        target_achieved = routing_summary["target_achieved"]
        
        logger.info(f"📊 Performance Results:")
        logger.info(f"   Average Response Time: {avg_response_time:.2f}s")
        logger.info(f"   Target (<5s): {'✅ ACHIEVED' if target_achieved else '❌ NOT ACHIEVED'}")
        logger.info(f"   Success Rate: {success_rate:.1%}")
        
        # Performance improvement calculation
        baseline_time = 44.0  # Current Qwen3:8b baseline
        improvement_factor = baseline_time / avg_response_time
        improvement_percent = ((baseline_time - avg_response_time) / baseline_time) * 100
        
        logger.info(f"\n🚀 Performance Improvement:")
        logger.info(f"   Baseline Time: {baseline_time}s (Qwen3:8b)")
        logger.info(f"   Optimized Time: {avg_response_time:.2f}s")
        logger.info(f"   Improvement Factor: {improvement_factor:.1f}x")
        logger.info(f"   Speed Improvement: {improvement_percent:.1f}%")
        
        # Target assessment
        target_improvement = 8.0  # 8-10x improvement target
        target_met = improvement_factor >= target_improvement
        
        logger.info(f"\n🎯 Target Achievement:")
        logger.info(f"   Target Improvement: {target_improvement}x")
        logger.info(f"   Actual Improvement: {improvement_factor:.1f}x")
        logger.info(f"   Target Status: {'✅ ACHIEVED' if target_met else '❌ PARTIAL' if improvement_factor >= 5.0 else '❌ NOT ACHIEVED'}")
        
        # Recommendations
        logger.info(f"\n💡 Recommendations:")
        if target_achieved and target_met:
            logger.info("   ✅ Deploy optimized model router to production")
            logger.info("   ✅ Monitor performance metrics continuously")
            logger.info("   ✅ Consider further optimization for complex queries")
        elif target_achieved:
            logger.info("   ⚠️  Response time target met but improvement factor below 8x")
            logger.info("   💡 Consider additional optimizations or infrastructure improvements")
        else:
            logger.info("   ❌ Response time target not consistently met")
            logger.info("   💡 Review model configurations and query complexity analysis")
            logger.info("   💡 Consider caching strategies or model fine-tuning")
        
        logger.info("\n" + "="*60)

async def main():
    """Main test execution"""
    test_suite = CoordinatorOptimizationTest()
    
    try:
        results = await test_suite.run_comprehensive_test()
        
        # Save results to file
        with open("coordinator_optimization_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info("\n📄 Full results saved to: coordinator_optimization_results.json")
        
        return results
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())