#!/usr/bin/env python3
"""
Real-World Performance Measurement for Kenny v2.1 Phase 3.2
Tests actual performance improvement against live Kenny system.
"""

import time
import asyncio
import requests
import statistics
from datetime import datetime
from typing import List, Dict, Any

class PerformanceMeasurement:
    """Measure real-world performance of Kenny v2.1 Phase 3.2 optimizations."""
    
    def __init__(self):
        self.gateway_url = "http://localhost:9000"
        self.coordinator_url = "http://localhost:8002"
        self.calendar_agent_url = "http://localhost:8007"
        
        # Test queries for performance measurement
        self.test_queries = [
            "events today",
            "meetings today", 
            "schedule today",
            "upcoming events",
            "meetings this week",
            "events tomorrow",
            "calendar for today",
            "what meetings do I have today",
            "show me my schedule",
            "any events this afternoon"
        ]
        
        # Target performance metrics (Phase 3.2 targets)
        self.targets = {
            "baseline_time": 41.0,  # Original performance (seconds)
            "target_min": 8.0,     # Target minimum (70% improvement)
            "target_max": 12.0,    # Target maximum (80% improvement)
            "improvement_target": 70.0  # Minimum 70% improvement
        }
    
    def test_gateway_query(self, query: str) -> Dict[str, Any]:
        """Test query performance via API Gateway."""
        start_time = time.time()
        
        try:
            response = requests.post(
                f"{self.gateway_url}/query",
                json={"query": query},
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": data.get("success", True),
                    "response_time": execution_time,
                    "cached": data.get("cached", False),
                    "confidence": data.get("confidence", 0.0),
                    "agent_used": data.get("agent_id", "unknown"),
                    "result": data.get("result", "")
                }
            else:
                return {
                    "success": False,
                    "response_time": execution_time,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "cached": False
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "response_time": execution_time,
                "error": str(e),
                "cached": False
            }
    
    def test_direct_calendar_query(self, query: str) -> Dict[str, Any]:
        """Test query performance directly via Calendar Agent."""
        start_time = time.time()
        
        try:
            # Use the correct calendar agent endpoint structure
            response = requests.post(
                f"{self.calendar_agent_url}/capabilities/calendar.read",
                json={"input": {"query": query}},
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                output = data.get("output", {})
                return {
                    "success": output.get("success", True),
                    "response_time": execution_time,
                    "cached": output.get("cached", False),
                    "confidence": output.get("confidence", 0.0),
                    "cache_stats": output.get("cache_stats", {}),
                    "result": output.get("result", "")
                }
            else:
                return {
                    "success": False,
                    "response_time": execution_time,
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "cached": False
                }
                
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "response_time": execution_time,
                "error": str(e),
                "cached": False
            }
    
    def run_performance_test_suite(self) -> Dict[str, Any]:
        """Run comprehensive performance test suite."""
        print("🚀 Starting Kenny v2.1 Phase 3.2 Real-World Performance Test")
        print("=" * 70)
        
        results = {
            "test_timestamp": datetime.now().isoformat(),
            "gateway_tests": [],
            "direct_tests": [],
            "cache_warming_tests": [],
            "performance_summary": {}
        }
        
        # Test 1: Gateway Performance (Cold Start)
        print("📊 Test 1: Gateway Performance (Cold Start)")
        print("-" * 50)
        
        for i, query in enumerate(self.test_queries):
            print(f"Testing query {i+1}/10: '{query}'...")
            result = self.test_gateway_query(query)
            results["gateway_tests"].append({
                "query": query,
                "attempt": 1,
                **result
            })
            
            if result["success"]:
                cache_status = "✅ CACHED" if result["cached"] else "❌ MISS"
                print(f"  Result: {result['response_time']:.2f}s {cache_status}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
            
            # Small delay between queries
            time.sleep(1)
        
        print()
        
        # Test 2: Direct Calendar Agent Performance
        print("📊 Test 2: Direct Calendar Agent Performance")
        print("-" * 50)
        
        for i, query in enumerate(self.test_queries):
            print(f"Testing query {i+1}/10: '{query}'...")
            result = self.test_direct_calendar_query(query)
            results["direct_tests"].append({
                "query": query,
                "attempt": 1,
                **result
            })
            
            if result["success"]:
                cache_status = "✅ CACHED" if result["cached"] else "❌ MISS"
                print(f"  Result: {result['response_time']:.2f}s {cache_status}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
            
            time.sleep(1)
        
        print()
        
        # Test 3: Cache Warming Effect (Repeat queries)
        print("📊 Test 3: Cache Warming Effect (Repeat Queries)")
        print("-" * 50)
        
        # Wait for cache warming to take effect
        print("⏳ Waiting 10 seconds for cache warming...")
        time.sleep(10)
        
        for i, query in enumerate(self.test_queries[:5]):  # Test subset
            print(f"Re-testing query {i+1}/5: '{query}'...")
            result = self.test_gateway_query(query)
            results["cache_warming_tests"].append({
                "query": query,
                "attempt": 2,
                **result
            })
            
            if result["success"]:
                cache_status = "✅ CACHED" if result["cached"] else "❌ MISS"
                print(f"  Result: {result['response_time']:.2f}s {cache_status}")
            else:
                print(f"  Error: {result.get('error', 'Unknown error')}")
            
            time.sleep(0.5)
        
        # Calculate performance summary
        results["performance_summary"] = self._calculate_performance_summary(results)
        
        return results
    
    def _calculate_performance_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive performance summary."""
        
        # Gateway performance analysis
        gateway_times = [r["response_time"] for r in results["gateway_tests"] if r["success"]]
        gateway_cached = [r for r in results["gateway_tests"] if r["success"] and r["cached"]]
        
        # Direct agent performance analysis
        direct_times = [r["response_time"] for r in results["direct_tests"] if r["success"]]
        direct_cached = [r for r in results["direct_tests"] if r["success"] and r["cached"]]
        
        # Cache warming performance analysis
        warming_times = [r["response_time"] for r in results["cache_warming_tests"] if r["success"]]
        warming_cached = [r for r in results["cache_warming_tests"] if r["success"] and r["cached"]]
        
        summary = {}
        
        if gateway_times:
            avg_gateway_time = statistics.mean(gateway_times)
            summary["gateway_performance"] = {
                "avg_response_time": avg_gateway_time,
                "min_response_time": min(gateway_times),
                "max_response_time": max(gateway_times),
                "cache_hit_rate": len(gateway_cached) / len(results["gateway_tests"]),
                "success_rate": len(gateway_times) / len(results["gateway_tests"]),
                "improvement_vs_baseline": ((self.targets["baseline_time"] - avg_gateway_time) / self.targets["baseline_time"]) * 100
            }
        
        if direct_times:
            avg_direct_time = statistics.mean(direct_times)
            summary["direct_agent_performance"] = {
                "avg_response_time": avg_direct_time,
                "min_response_time": min(direct_times),
                "max_response_time": max(direct_times),
                "cache_hit_rate": len(direct_cached) / len(results["direct_tests"]),
                "success_rate": len(direct_times) / len(results["direct_tests"]),
                "improvement_vs_baseline": ((self.targets["baseline_time"] - avg_direct_time) / self.targets["baseline_time"]) * 100
            }
        
        if warming_times:
            avg_warming_time = statistics.mean(warming_times)
            summary["cache_warming_performance"] = {
                "avg_response_time": avg_warming_time,
                "min_response_time": min(warming_times),
                "max_response_time": max(warming_times),
                "cache_hit_rate": len(warming_cached) / len(results["cache_warming_tests"]),
                "success_rate": len(warming_times) / len(results["cache_warming_tests"]),
                "improvement_vs_baseline": ((self.targets["baseline_time"] - avg_warming_time) / self.targets["baseline_time"]) * 100
            }
        
        # Overall assessment
        if gateway_times and direct_times:
            best_performance = min(statistics.mean(gateway_times), statistics.mean(direct_times))
            overall_improvement = ((self.targets["baseline_time"] - best_performance) / self.targets["baseline_time"]) * 100
            
            summary["overall_assessment"] = {
                "best_avg_response_time": best_performance,
                "overall_improvement_percent": overall_improvement,
                "target_met": overall_improvement >= self.targets["improvement_target"],
                "performance_within_target_range": self.targets["target_min"] <= best_performance <= self.targets["target_max"],
                "strategic_recommendation": self._get_strategic_recommendation(overall_improvement, best_performance)
            }
        
        return summary
    
    def _get_strategic_recommendation(self, improvement_percent: float, response_time: float) -> str:
        """Get strategic recommendation based on performance results."""
        if improvement_percent >= 80 and response_time <= 12:
            return "TARGET_EXCEEDED_PHASE_3_2_SUFFICIENT"
        elif improvement_percent >= 70 and response_time <= 15:
            return "TARGET_MET_PHASE_3_2_SUFFICIENT"
        elif improvement_percent >= 50 and response_time <= 20:
            return "PARTIAL_SUCCESS_EVALUATE_PHASE_3_5"
        elif improvement_percent >= 30:
            return "MODERATE_IMPROVEMENT_PHASE_3_5_RECOMMENDED"
        else:
            return "TARGET_MISSED_DEBUG_PHASE_3_2"
    
    def print_results(self, results: Dict[str, Any]):
        """Print formatted performance test results."""
        print("\n" + "=" * 70)
        print("📊 KENNY V2.1 PHASE 3.2 PERFORMANCE TEST RESULTS")
        print("=" * 70)
        
        summary = results["performance_summary"]
        
        if "gateway_performance" in summary:
            gw = summary["gateway_performance"]
            print(f"\n🌐 Gateway Performance:")
            print(f"   Average Response Time: {gw['avg_response_time']:.2f}s")
            print(f"   Cache Hit Rate: {gw['cache_hit_rate']:.1%}")
            print(f"   Success Rate: {gw['success_rate']:.1%}")
            print(f"   Improvement vs Baseline: {gw['improvement_vs_baseline']:.1f}%")
        
        if "direct_agent_performance" in summary:
            da = summary["direct_agent_performance"]
            print(f"\n🎯 Direct Agent Performance:")
            print(f"   Average Response Time: {da['avg_response_time']:.2f}s")
            print(f"   Cache Hit Rate: {da['cache_hit_rate']:.1%}")
            print(f"   Success Rate: {da['success_rate']:.1%}")
            print(f"   Improvement vs Baseline: {da['improvement_vs_baseline']:.1f}%")
        
        if "cache_warming_performance" in summary:
            cw = summary["cache_warming_performance"]
            print(f"\n🔥 Cache Warming Performance:")
            print(f"   Average Response Time: {cw['avg_response_time']:.2f}s")
            print(f"   Cache Hit Rate: {cw['cache_hit_rate']:.1%}")
            print(f"   Success Rate: {cw['success_rate']:.1%}")
            print(f"   Improvement vs Baseline: {cw['improvement_vs_baseline']:.1f}%")
        
        if "overall_assessment" in summary:
            oa = summary["overall_assessment"]
            print(f"\n🎯 OVERALL ASSESSMENT:")
            print(f"   Best Performance: {oa['best_avg_response_time']:.2f}s")
            print(f"   Overall Improvement: {oa['overall_improvement_percent']:.1f}%")
            print(f"   Target Met (≥70%): {'✅ YES' if oa['target_met'] else '❌ NO'}")
            print(f"   Within Range (8-12s): {'✅ YES' if oa['performance_within_target_range'] else '❌ NO'}")
            print(f"   Strategic Recommendation: {oa['strategic_recommendation']}")
        
        print(f"\n📋 Test Targets:")
        print(f"   Baseline: {self.targets['baseline_time']}s")
        print(f"   Target Range: {self.targets['target_min']}-{self.targets['target_max']}s")
        print(f"   Minimum Improvement: {self.targets['improvement_target']}%")
        
        print("\n" + "=" * 70)

def main():
    """Run the performance measurement suite."""
    measurement = PerformanceMeasurement()
    
    try:
        # Check if Kenny is running
        test_response = measurement.test_gateway_query("system status")
        if not test_response["success"]:
            print("❌ Error: Kenny system not accessible. Please ensure Kenny is running.")
            print("   Run: ./kenny-launch.sh")
            return
        
        # Run performance tests
        results = measurement.run_performance_test_suite()
        
        # Print results
        measurement.print_results(results)
        
        # Return strategic recommendation
        if "overall_assessment" in results["performance_summary"]:
            recommendation = results["performance_summary"]["overall_assessment"]["strategic_recommendation"]
            print(f"\n🎯 Strategic Decision: {recommendation}")
            
            if "TARGET_MET" in recommendation or "TARGET_EXCEEDED" in recommendation:
                print("✅ Phase 3.2 optimization successful! Ready for production hardening.")
                exit_code = 0
            elif "PARTIAL_SUCCESS" in recommendation or "EVALUATE_PHASE_3_5" in recommendation:
                print("⚠️  Partial success. Consider Phase 3.5 implementation.")
                exit_code = 1
            else:
                print("❌ Performance targets not met. Debug and optimize Phase 3.2.")
                exit_code = 2
            
            return exit_code
        
        return 0
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return 1

if __name__ == "__main__":
    exit(main())