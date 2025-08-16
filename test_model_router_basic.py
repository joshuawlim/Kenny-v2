#!/usr/bin/env python3
"""
Basic test for the Model Router optimization system
Tests complexity analysis and model selection logic without requiring Ollama
"""

import asyncio
import time
import sys
import os

# Add the services directory to the Python path
coordinator_src = os.path.join(os.path.dirname(__file__), 'services', 'coordinator', 'src')
sys.path.append(coordinator_src)
sys.path.append(os.path.join(coordinator_src, 'benchmarking'))

# Fix relative imports by setting up the package path
import importlib.util

# Load the model router module manually to handle relative imports
model_router_path = os.path.join(coordinator_src, 'model_router.py')
spec = importlib.util.spec_from_file_location("model_router", model_router_path)
model_router_module = importlib.util.module_from_spec(spec)

# Load dependencies first
performance_metrics_path = os.path.join(coordinator_src, 'benchmarking', 'performance_metrics.py')
perf_spec = importlib.util.spec_from_file_location("performance_metrics", performance_metrics_path)
perf_module = importlib.util.module_from_spec(perf_spec)
perf_spec.loader.exec_module(perf_module)

ab_testing_path = os.path.join(coordinator_src, 'benchmarking', 'ab_testing.py')
ab_spec = importlib.util.spec_from_file_location("ab_testing", ab_testing_path)
ab_module = importlib.util.module_from_spec(ab_spec)
ab_spec.loader.exec_module(ab_module)

# Inject dependencies into sys.modules
sys.modules['benchmarking.performance_metrics'] = perf_module
sys.modules['benchmarking.ab_testing'] = ab_module

# Now load the model router
spec.loader.exec_module(model_router_module)

ModelRouter = model_router_module.ModelRouter
QueryComplexity = model_router_module.QueryComplexity

async def test_query_complexity_analysis():
    """Test query complexity analysis without LLM calls"""
    print("🧠 Testing Query Complexity Analysis...")
    
    router = ModelRouter()
    
    test_cases = [
        # Simple queries
        {"query": "check email", "expected": QueryComplexity.SIMPLE},
        {"query": "show calendar", "expected": QueryComplexity.SIMPLE},
        {"query": "find contacts", "expected": QueryComplexity.SIMPLE},
        
        # Moderate queries
        {"query": "find emails from Sarah about project", "expected": QueryComplexity.MODERATE},
        {"query": "search messages containing meeting", "expected": QueryComplexity.MODERATE},
        
        # Complex queries
        {"query": "find emails from John about project X and schedule a meeting", "expected": QueryComplexity.COMPLEX},
        {"query": "analyze my calendar and suggest optimal meeting times", "expected": QueryComplexity.COMPLEX},
        
        # Ambiguous queries
        {"query": "help me with something", "expected": QueryComplexity.AMBIGUOUS},
        {"query": "find the thing from yesterday maybe", "expected": QueryComplexity.AMBIGUOUS}
    ]
    
    results = []
    for test_case in test_cases:
        query = test_case["query"]
        expected = test_case["expected"]
        
        analysis = await router._analyze_query_complexity(query, {})
        actual = analysis["complexity"]
        confidence = analysis["confidence"]
        reasoning = analysis["reasoning"]
        
        success = actual == expected
        results.append({
            "query": query,
            "expected": expected.value,
            "actual": actual.value,
            "confidence": confidence,
            "success": success,
            "reasoning": reasoning
        })
        
        status = "✅" if success else "❌"
        print(f"  {status} '{query}' -> {actual.value} (expected: {expected.value}, confidence: {confidence:.2f})")
        if not success:
            print(f"    Reasoning: {reasoning}")
    
    accuracy = sum(r["success"] for r in results) / len(results)
    print(f"\n🎯 Complexity Analysis Accuracy: {accuracy:.1%}")
    
    return results

async def test_model_selection_logic():
    """Test model selection logic based on complexity"""
    print("\n⚡ Testing Model Selection Logic...")
    
    router = ModelRouter()
    
    test_scenarios = [
        # Simple query -> fastest model
        {
            "complexity": QueryComplexity.SIMPLE,
            "expected_model": "llama3.2:3b-instruct",
            "reason": "Simple queries should use fastest model"
        },
        # Moderate query -> balanced model
        {
            "complexity": QueryComplexity.MODERATE,
            "expected_model": "qwen2.5:3b-instruct",
            "reason": "Moderate queries should use balanced model"
        },
        # Complex query with good performance -> accurate model
        {
            "complexity": QueryComplexity.COMPLEX,
            "expected_model": "qwen2.5:3b-instruct",  # Fallback due to performance constraints
            "reason": "Complex queries use balanced model when performance is constrained"
        }
    ]
    
    results = []
    for scenario in test_scenarios:
        complexity = scenario["complexity"]
        expected_model = scenario["expected_model"]
        
        # Create mock complexity analysis
        complexity_analysis = {
            "complexity": complexity,
            "confidence": 0.8,
            "reasoning": f"Test scenario for {complexity.value} complexity"
        }
        
        selected_model, reasoning = await router._select_optimal_model(complexity_analysis, {})
        
        success = selected_model == expected_model
        results.append({
            "complexity": complexity.value,
            "expected_model": expected_model,
            "selected_model": selected_model,
            "success": success,
            "reasoning": reasoning
        })
        
        status = "✅" if success else "❌"
        print(f"  {status} {complexity.value} -> {selected_model} (expected: {expected_model})")
        print(f"    Strategy: {reasoning.get('strategy', 'unknown')}")
        print(f"    Reason: {reasoning.get('reason', 'no reason provided')}")
    
    accuracy = sum(r["success"] for r in results) / len(results)
    print(f"\n🎯 Model Selection Accuracy: {accuracy:.1%}")
    
    return results

async def test_performance_estimation():
    """Test performance estimation and routing decisions"""
    print("\n📈 Testing Performance Estimation...")
    
    router = ModelRouter()
    
    # Test response time estimates
    test_queries = [
        "check email",
        "find emails from Sarah about project updates",
        "analyze my calendar and suggest optimal meeting times for next week"
    ]
    
    total_estimated_time = 0
    results = []
    
    for query in test_queries:
        start_time = time.time()
        
        # Route query (this will select model and provide estimates)
        selected_model, routing_info = await router.route_query(query)
        
        processing_time = time.time() - start_time
        estimated_response_time = routing_info.get("estimated_response_time", 0)
        complexity = routing_info.get("complexity_analysis", {}).get("complexity", "unknown")
        
        total_estimated_time += estimated_response_time
        
        results.append({
            "query": query,
            "selected_model": selected_model,
            "estimated_response_time": estimated_response_time,
            "routing_time": processing_time,
            "complexity": complexity.value if hasattr(complexity, 'value') else str(complexity)
        })
        
        print(f"  Query: '{query}'")
        print(f"    Model: {selected_model}")
        print(f"    Estimated Response Time: {estimated_response_time:.2f}s")
        print(f"    Routing Time: {processing_time:.3f}s")
        print(f"    Complexity: {complexity.value if hasattr(complexity, 'value') else complexity}")
        print()
    
    avg_estimated_time = total_estimated_time / len(test_queries)
    target_met = avg_estimated_time <= 5.0
    
    print(f"🎯 Performance Targets:")
    print(f"  Average Estimated Response Time: {avg_estimated_time:.2f}s")
    print(f"  Target (<5s): {'✅ MET' if target_met else '❌ NOT MET'}")
    
    return {
        "results": results,
        "avg_estimated_time": avg_estimated_time,
        "target_met": target_met
    }

async def test_integration():
    """Test full integration without external dependencies"""
    print("\n🔗 Testing Full Integration...")
    
    # Import the enhanced router components
    from nodes.router import IntentClassifier
    
    # Create classifier with model router integration
    classifier = IntentClassifier()
    
    # Test queries that should be routed to different models
    test_queries = [
        "check my email",  # Simple -> fast model
        "find emails from John about the quarterly review and check his calendar availability",  # Complex
        "help me with something"  # Ambiguous
    ]
    
    results = []
    for query in test_queries:
        print(f"\n  Testing: '{query}'")
        
        try:
            # Test the routing decision
            start_time = time.time()
            
            # This will trigger model routing and complexity analysis
            selected_model, routing_info = await classifier.model_router.route_query(query)
            
            routing_time = time.time() - start_time
            
            complexity = routing_info.get("complexity_analysis", {}).get("complexity", "unknown")
            estimated_time = routing_info.get("estimated_response_time", 0)
            
            result = {
                "query": query,
                "selected_model": selected_model,
                "complexity": complexity.value if hasattr(complexity, 'value') else str(complexity),
                "estimated_response_time": estimated_time,
                "routing_time": routing_time,
                "success": True
            }
            
            print(f"    ✅ Routed to: {selected_model}")
            print(f"    Complexity: {result['complexity']}")
            print(f"    Estimated time: {estimated_time:.2f}s")
            print(f"    Routing overhead: {routing_time:.3f}s")
            
        except Exception as e:
            result = {
                "query": query,
                "error": str(e),
                "success": False
            }
            print(f"    ❌ Error: {e}")
        
        results.append(result)
    
    success_rate = sum(r["success"] for r in results) / len(results)
    print(f"\n🎯 Integration Success Rate: {success_rate:.1%}")
    
    return results

async def main():
    """Run all basic tests"""
    print("🚀 Model Router Optimization - Basic Tests")
    print("="*50)
    
    results = {}
    
    # Test 1: Complexity analysis
    results["complexity_analysis"] = await test_query_complexity_analysis()
    
    # Test 2: Model selection logic
    results["model_selection"] = await test_model_selection_logic()
    
    # Test 3: Performance estimation
    results["performance_estimation"] = await test_performance_estimation()
    
    # Test 4: Integration test
    results["integration"] = await test_integration()
    
    # Summary
    print("\n" + "="*50)
    print("🎉 TEST SUMMARY")
    print("="*50)
    
    complexity_accuracy = sum(r["success"] for r in results["complexity_analysis"]) / len(results["complexity_analysis"])
    selection_accuracy = sum(r["success"] for r in results["model_selection"]) / len(results["model_selection"])
    performance_target_met = results["performance_estimation"]["target_met"]
    integration_success = sum(r["success"] for r in results["integration"]) / len(results["integration"])
    
    print(f"Complexity Analysis Accuracy: {complexity_accuracy:.1%}")
    print(f"Model Selection Accuracy: {selection_accuracy:.1%}")
    print(f"Performance Target Met: {'✅ YES' if performance_target_met else '❌ NO'}")
    print(f"Integration Success Rate: {integration_success:.1%}")
    
    overall_success = (
        complexity_accuracy >= 0.7 and
        selection_accuracy >= 0.6 and
        performance_target_met and
        integration_success >= 0.8
    )
    
    print(f"\nOverall Assessment: {'✅ PASS' if overall_success else '❌ NEEDS WORK'}")
    
    if overall_success:
        print("\n✅ Model Router optimization is working correctly!")
        print("Ready for integration with coordinator and performance testing.")
    else:
        print("\n❌ Some issues detected. Review the test results above.")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())