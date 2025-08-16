#!/usr/bin/env python3
"""
Quick Performance Test for Kenny v2.1 Phase 3.2
Tests key performance metrics for strategic decision making.
"""

import time
import requests
import statistics
from datetime import datetime

def test_gateway_performance():
    """Test Gateway performance with calendar queries."""
    print("🚀 Quick Kenny v2.1 Phase 3.2 Performance Test")
    print("=" * 60)
    
    gateway_url = "http://localhost:9000"
    test_queries = [
        "events today",
        "meetings today", 
        "schedule today",
        "upcoming events",
        "events tomorrow"
    ]
    
    results = []
    cache_hits = 0
    
    print("📊 Testing Gateway Performance...")
    for i, query in enumerate(test_queries):
        print(f"  Testing {i+1}/5: '{query}'...")
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{gateway_url}/query",
                json={"query": query},
                timeout=30
            )
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                cached = data.get("cached", False)
                if cached:
                    cache_hits += 1
                    
                results.append({
                    "query": query,
                    "response_time": execution_time,
                    "success": True,
                    "cached": cached
                })
                
                cache_status = "✅ CACHED" if cached else "❌ MISS"
                print(f"    Result: {execution_time:.2f}s {cache_status}")
            else:
                print(f"    Error: HTTP {response.status_code}")
                results.append({
                    "query": query,
                    "response_time": execution_time,
                    "success": False,
                    "cached": False
                })
        
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"    Error: {e}")
            results.append({
                "query": query,
                "response_time": execution_time,
                "success": False,
                "cached": False
            })
        
        time.sleep(1)  # Brief pause between queries
    
    # Performance Analysis
    successful_results = [r for r in results if r["success"]]
    if successful_results:
        response_times = [r["response_time"] for r in successful_results]
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        cache_hit_rate = cache_hits / len(test_queries)
        
        print(f"\n📊 PERFORMANCE RESULTS:")
        print(f"   Average Response Time: {avg_time:.2f}s")
        print(f"   Min Response Time: {min_time:.2f}s")
        print(f"   Max Response Time: {max_time:.2f}s")
        print(f"   Cache Hit Rate: {cache_hit_rate:.1%}")
        print(f"   Success Rate: {len(successful_results)}/{len(test_queries)}")
        
        # Strategic Assessment
        baseline_time = 41.0  # Original baseline
        improvement = ((baseline_time - avg_time) / baseline_time) * 100
        
        print(f"\n🎯 STRATEGIC ASSESSMENT:")
        print(f"   Baseline Performance: {baseline_time}s")
        print(f"   Current Performance: {avg_time:.2f}s")
        print(f"   Performance Improvement: {improvement:.1f}%")
        
        if improvement >= 80:
            recommendation = "TARGET_EXCEEDED_PHASE_3_2_SUFFICIENT"
            status = "✅ EXCELLENT"
        elif improvement >= 70:
            recommendation = "TARGET_MET_PHASE_3_2_SUFFICIENT"
            status = "✅ SUCCESS"
        elif improvement >= 50:
            recommendation = "PARTIAL_SUCCESS_EVALUATE_PHASE_3_5"
            status = "⚠️ PARTIAL"
        else:
            recommendation = "TARGET_MISSED_DEBUG_PHASE_3_2"
            status = "❌ NEEDS_WORK"
        
        print(f"   Target (70% improvement): {'✅ MET' if improvement >= 70 else '❌ NOT MET'}")
        print(f"   Status: {status}")
        print(f"   Recommendation: {recommendation}")
        
        return {
            "avg_response_time": avg_time,
            "improvement_percent": improvement,
            "cache_hit_rate": cache_hit_rate,
            "recommendation": recommendation,
            "target_met": improvement >= 70
        }
    else:
        print("❌ No successful queries to analyze")
        return None

def test_cache_warming_effect():
    """Test cache warming by repeating queries."""
    print(f"\n🔥 Testing Cache Warming Effect...")
    
    gateway_url = "http://localhost:9000"
    test_query = "events today"
    
    print("  Running initial query (cold)...")
    start_time = time.time()
    response1 = requests.post(f"{gateway_url}/query", json={"query": test_query}, timeout=30)
    time1 = time.time() - start_time
    
    print("  Waiting 5 seconds for cache warming...")
    time.sleep(5)
    
    print("  Running repeat query (warm)...")
    start_time = time.time()
    response2 = requests.post(f"{gateway_url}/query", json={"query": test_query}, timeout=30)
    time2 = time.time() - start_time
    
    if response1.status_code == 200 and response2.status_code == 200:
        improvement = ((time1 - time2) / time1) * 100 if time1 > time2 else 0
        
        print(f"  Cold Query: {time1:.2f}s")
        print(f"  Warm Query: {time2:.2f}s")
        print(f"  Cache Warming Improvement: {improvement:.1f}%")
        
        return improvement
    else:
        print("  Error testing cache warming")
        return 0

if __name__ == "__main__":
    # Test Gateway Performance
    gateway_results = test_gateway_performance()
    
    # Test Cache Warming
    warming_improvement = test_cache_warming_effect()
    
    print(f"\n" + "=" * 60)
    print("🎯 FINAL STRATEGIC ASSESSMENT")
    print("=" * 60)
    
    if gateway_results:
        print(f"Phase 3.2 Performance: {gateway_results['improvement_percent']:.1f}% improvement")
        print(f"Cache Effectiveness: {gateway_results['cache_hit_rate']:.1%} hit rate")
        print(f"Cache Warming: {warming_improvement:.1f}% improvement on repeat queries")
        print(f"Strategic Recommendation: {gateway_results['recommendation']}")
        
        if gateway_results['target_met']:
            print("✅ Phase 3.2 targets achieved! Ready for production hardening.")
            exit_code = 0
        else:
            print("⚠️  Phase 3.2 targets not fully met. Consider Phase 3.5 implementation.")
            exit_code = 1
    else:
        print("❌ Unable to measure performance. System may need debugging.")
        exit_code = 2
    
    exit(exit_code)