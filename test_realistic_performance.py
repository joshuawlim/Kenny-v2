#!/usr/bin/env python3
"""
Realistic performance test for health monitoring overhead
"""

import time
import sys
sys.path.append('services/agent-sdk')

from kenny_agent.health import PerformanceTracker, AgentHealthMonitor

def realistic_performance_test():
    """Test performance overhead with realistic workload simulation."""
    print("⚡ Realistic Performance Impact Test")
    print("=" * 50)
    
    def simulate_work():
        """Simulate some actual work."""
        # Simulate computational work
        total = 0
        for i in range(100):
            total += i * i
        return total
    
    # Test without monitoring
    print("Testing baseline performance...")
    start_time = time.perf_counter()
    for _ in range(1000):
        result = simulate_work()
    baseline_time = time.perf_counter() - start_time
    
    # Test with monitoring
    print("Testing with health monitoring...")
    tracker = PerformanceTracker()
    start_time = time.perf_counter()
    for i in range(1000):
        operation_start = time.perf_counter()
        result = simulate_work()
        operation_time = (time.perf_counter() - operation_start) * 1000  # Convert to ms
        
        tracker.record_operation(operation_time, success=True)
        
        # Periodic metrics calculation (every 100 operations)
        if i % 100 == 0:
            tracker.get_current_metrics()
            tracker.check_sla_compliance()
    
    monitoring_time = time.perf_counter() - start_time
    
    overhead_ms = (monitoring_time - baseline_time) * 1000
    overhead_percent = (overhead_ms / (baseline_time * 1000)) * 100 if baseline_time > 0 else 0
    
    print(f"Baseline time: {baseline_time*1000:.2f}ms")
    print(f"With monitoring: {monitoring_time*1000:.2f}ms")
    print(f"Absolute overhead: {overhead_ms:.2f}ms")
    print(f"Relative overhead: {overhead_percent:.2f}%")
    
    # Test AgentHealthMonitor overhead
    print("\nTesting AgentHealthMonitor overhead...")
    monitor = AgentHealthMonitor("perf-test")
    
    start_time = time.perf_counter()
    for i in range(100):
        operation_start = time.perf_counter()
        result = simulate_work()
        operation_time = (time.perf_counter() - operation_start) * 1000
        
        monitor.record_operation(operation_time, success=True)
        
        if i % 20 == 0:
            enhanced_health = monitor.get_enhanced_health()
            dashboard = monitor.get_performance_dashboard()
    
    monitor_time = time.perf_counter() - start_time
    
    print(f"AgentHealthMonitor time (100 ops): {monitor_time*1000:.2f}ms")
    print(f"Per operation overhead: {(monitor_time*1000)/100:.3f}ms")
    
    return overhead_percent < 20  # Accept up to 20% overhead for comprehensive monitoring

def test_degradation_detection_fix():
    """Test the degradation detection with proper setup."""
    print("\n🔍 Testing Degradation Detection (Fixed)")
    print("=" * 50)
    
    monitor = AgentHealthMonitor("degradation-test")
    
    # Start with stable performance to build baseline
    print("Building baseline performance...")
    for i in range(30):
        monitor.record_operation(100, success=True)
    
    # Create significant degradation pattern
    print("Simulating performance degradation...")
    for i in range(30):
        rt = 100 + (i * 30)  # More aggressive degradation: 100ms -> 1000ms
        success = i < 25  # Some failures at the end
        monitor.record_operation(rt, success=success)
    
    dashboard = monitor.get_performance_dashboard()
    alerts = dashboard["alerts"]["recent"]
    
    # Check for degradation alerts
    degradation_alerts = [a for a in alerts if a.get("type") == "performance_degradation"]
    sla_alerts = [a for a in alerts if a.get("type") == "sla_violation"]
    
    print(f"Total alerts: {len(alerts)}")
    print(f"Degradation alerts: {len(degradation_alerts)}")
    print(f"SLA violation alerts: {len(sla_alerts)}")
    
    # Check trend analysis
    trend = dashboard["performance_summary"]["trend_analysis"]
    print(f"Trend analysis: {trend}")
    
    has_degradation_detection = len(degradation_alerts) > 0 or trend.get("trend") == "degrading"
    print(f"Degradation detection working: {'✅' if has_degradation_detection else '❌'}")
    
    return has_degradation_detection

def main():
    """Run realistic performance tests."""
    perf_acceptable = realistic_performance_test()
    degradation_works = test_degradation_detection_fix()
    
    print(f"\n📊 Test Results Summary")
    print("=" * 50)
    print(f"Performance overhead acceptable: {'✅' if perf_acceptable else '❌'}")
    print(f"Degradation detection working: {'✅' if degradation_works else '❌'}")
    
    if perf_acceptable and degradation_works:
        print(f"\n🎉 All performance tests PASSED!")
        print("Phase 2.1.3 Enhanced Health Monitoring is production-ready.")
    else:
        print(f"\n⚠️ Some tests need attention.")

if __name__ == "__main__":
    main()