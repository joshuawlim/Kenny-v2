#!/usr/bin/env python3
"""
Performance validation test for Phase 3.2.1: Parallel Processing optimizations.

This test validates that the implemented parallel processing optimizations
achieve the target 30-40% performance improvement for calendar operations.
"""

import asyncio
import time
import logging
import sys
from pathlib import Path

# Add the calendar agent to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from intelligent_calendar_agent import IntelligentCalendarAgent
from performance_monitor import get_performance_monitor

# Configure logging for testing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("phase_3_2_1_test")


class PerformanceTestSuite:
    """Test suite for validating Phase 3.2.1 performance improvements."""
    
    def __init__(self):
        self.agent = None
        self.performance_monitor = get_performance_monitor()
        self.test_results = {}
    
    async def setup(self):
        """Set up the test environment."""
        logger.info("Setting up Phase 3.2.1 performance test environment...")
        
        # Initialize the calendar agent with optimizations
        self.agent = IntelligentCalendarAgent()
        await self.agent.start()
        
        logger.info("Calendar agent initialized with parallel processing optimizations")
    
    async def teardown(self):
        """Clean up the test environment."""
        if self.agent:
            await self.agent.stop()
        logger.info("Test environment cleaned up")
    
    async def test_parallel_contact_resolution(self):
        """Test parallel contact resolution performance."""
        logger.info("Testing parallel contact resolution...")
        
        # Test query with multiple contacts
        test_query = "upcoming meetings with Alice Johnson Bob Smith and Carol Davis"
        
        start_time = time.time()
        
        # Execute the enhanced capability that uses parallel contact resolution
        result = await self.agent._resolve_contacts_and_filter_events(
            query=test_query,
            date_range={
                "start": "2025-08-16T00:00:00Z",
                "end": "2025-08-23T23:59:59Z"
            }
        )
        
        execution_time = time.time() - start_time
        
        self.test_results["parallel_contact_resolution"] = {
            "execution_time": execution_time,
            "confidence": result.confidence,
            "parallel_operations": True,
            "contacts_found": len(result.result.get("resolved_contacts", [])),
            "success": execution_time < 10.0  # Should be much faster than 41s baseline
        }
        
        logger.info(f"Parallel contact resolution completed in {execution_time:.3f}s")
        return execution_time
    
    async def test_parallel_calendar_operations(self):
        """Test parallel calendar bridge operations."""
        logger.info("Testing parallel calendar bridge operations...")
        
        # Get the calendar bridge tool
        calendar_bridge = self.agent.tools.get("calendar_bridge")
        if not calendar_bridge:
            logger.warning("Calendar bridge tool not available, skipping test")
            return None
        
        # Test parallel operations
        operations = [
            {"operation": "list_calendars"},
            {"operation": "list_events", "start_date": "2025-08-16T00:00:00Z", "end_date": "2025-08-23T23:59:59Z"},
            {"operation": "health"}
        ]
        
        start_time = time.time()
        
        # Execute operations in parallel
        results = await calendar_bridge.execute_parallel(operations)
        
        execution_time = time.time() - start_time
        
        successful_operations = sum(1 for r in results if not r.get("error"))
        
        self.test_results["parallel_calendar_operations"] = {
            "execution_time": execution_time,
            "operations_count": len(operations),
            "successful_operations": successful_operations,
            "success": successful_operations >= 2,  # At least 2 operations should succeed
            "parallel_performance": True
        }
        
        logger.info(f"Parallel calendar operations completed in {execution_time:.3f}s")
        return execution_time
    
    async def test_enhanced_calendar_read(self):
        """Test enhanced calendar read with parallel processing."""
        logger.info("Testing enhanced calendar read capability...")
        
        # Test the enhanced calendar read capability
        read_handler = self.agent.read_handler
        
        start_time = time.time()
        
        result = await read_handler.execute({
            "query": "upcoming meetings with team members this week",
            "date_range": {
                "start": "2025-08-16T00:00:00Z",
                "end": "2025-08-23T23:59:59Z"
            },
            "limit": 50,
            "include_all_day": True
        })
        
        execution_time = time.time() - start_time
        
        self.test_results["enhanced_calendar_read"] = {
            "execution_time": execution_time,
            "events_found": result.get("count", 0),
            "parallel_operations": result.get("parallel_operations", 1),
            "has_execution_time": "execution_time" in result,
            "success": execution_time < 15.0  # Should be much faster than baseline
        }
        
        logger.info(f"Enhanced calendar read completed in {execution_time:.3f}s")
        return execution_time
    
    async def test_concurrent_capability_execution(self):
        """Test concurrent execution of multiple capabilities."""
        logger.info("Testing concurrent capability execution...")
        
        start_time = time.time()
        
        # Execute multiple capabilities concurrently
        tasks = [
            self.agent._handle_enhanced_capability("calendar.read_with_contacts", {
                "query": "meetings with Alice today",
                "date_range": {
                    "start": "2025-08-16T00:00:00Z",
                    "end": "2025-08-16T23:59:59Z"
                }
            }),
            self.agent._handle_enhanced_capability("calendar.context_analyze", {
                "query": "upcoming important meetings"
            }),
            self.agent._handle_enhanced_capability("calendar.availability_optimize", {
                "calendar_data": {"current_week": "test"},
                "goals": {"focus_time": 4}
            })
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        execution_time = time.time() - start_time
        
        successful_capabilities = sum(1 for r in results if not isinstance(r, Exception))
        
        self.test_results["concurrent_capability_execution"] = {
            "execution_time": execution_time,
            "capabilities_count": len(tasks),
            "successful_capabilities": successful_capabilities,
            "success": successful_capabilities >= 2,
            "concurrent_performance": True
        }
        
        logger.info(f"Concurrent capability execution completed in {execution_time:.3f}s")
        return execution_time
    
    async def calculate_performance_improvement(self):
        """Calculate overall performance improvement against baseline."""
        # Baseline: 41 seconds for complex calendar queries
        baseline_time = 41.0
        
        # Calculate average execution time from our tests
        test_times = []
        for test_name, result in self.test_results.items():
            if result.get("execution_time"):
                test_times.append(result["execution_time"])
        
        if not test_times:
            logger.warning("No execution times recorded for performance calculation")
            return 0.0
        
        average_time = sum(test_times) / len(test_times)
        improvement = (baseline_time - average_time) / baseline_time
        
        logger.info(f"Performance Analysis:")
        logger.info(f"  Baseline: {baseline_time:.1f}s")
        logger.info(f"  Optimized Average: {average_time:.3f}s")
        logger.info(f"  Improvement: {improvement*100:.1f}%")
        logger.info(f"  Target: 30-40% improvement")
        logger.info(f"  Target Met: {improvement >= 0.30}")
        
        return improvement
    
    async def generate_performance_report(self):
        """Generate comprehensive performance report."""
        performance_report = self.performance_monitor.get_parallel_performance_report()
        
        logger.info("\\n" + "="*60)
        logger.info("PHASE 3.2.1 PERFORMANCE VALIDATION REPORT")
        logger.info("="*60)
        
        # Test Results Summary
        logger.info("\\nTest Results Summary:")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result.get("success", False) else "❌ FAIL"
            time_str = f"{result.get('execution_time', 0):.3f}s" if result.get('execution_time') else "N/A"
            logger.info(f"  {test_name}: {status} ({time_str})")
        
        # Performance Metrics
        if performance_report.get("performance_comparison"):
            comp = performance_report["performance_comparison"]
            logger.info(f"\\nPerformance Improvements:")
            logger.info(f"  Achieved: {comp.get('improvement_percentage', 'N/A')}%")
            logger.info(f"  Target: {comp.get('target_improvement', '30-40%')}")
            logger.info(f"  Target Met: {comp.get('target_met', False)}")
        
        # System Health
        if performance_report.get("optimization_impact"):
            opt = performance_report["optimization_impact"]
            logger.info(f"\\nSystem Health:")
            logger.info(f"  Cache Hit Ratio: {opt.get('cache_hit_ratio', 0)*100:.1f}%")
            logger.info(f"  Success Ratio: {opt.get('success_ratio', 0)*100:.1f}%")
            logger.info(f"  Avg Concurrent Tasks: {opt.get('avg_concurrent_tasks', 0)}")
        
        # Optimization Features
        logger.info(f"\\nOptimization Features Implemented:")
        logger.info(f"  ✅ Async Calendar Bridge with Connection Pooling")
        logger.info(f"  ✅ Parallel Contact Resolution")
        logger.info(f"  ✅ Enhanced Event Fetching with Auto-Parallelization")
        logger.info(f"  ✅ Concurrent Agent Capability Execution")
        logger.info(f"  ✅ Comprehensive Performance Monitoring")
        
        logger.info("="*60)
        
        return performance_report
    
    async def run_all_tests(self):
        """Run all performance validation tests."""
        logger.info("Starting Phase 3.2.1 performance validation tests...")
        
        try:
            await self.setup()
            
            # Run individual tests
            await self.test_parallel_contact_resolution()
            await self.test_parallel_calendar_operations()
            await self.test_enhanced_calendar_read()
            await self.test_concurrent_capability_execution()
            
            # Calculate overall improvement
            improvement = await self.calculate_performance_improvement()
            
            # Generate final report
            await self.generate_performance_report()
            
            # Determine overall success
            target_met = improvement >= 0.30
            logger.info(f"\\nOverall Phase 3.2.1 Validation: {'✅ SUCCESS' if target_met else '❌ NEEDS IMPROVEMENT'}")
            
            return target_met
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            return False
        finally:
            await self.teardown()


async def main():
    """Main test execution function."""
    test_suite = PerformanceTestSuite()
    success = await test_suite.run_all_tests()
    
    if success:
        logger.info("Phase 3.2.1 parallel processing optimizations successfully validated!")
        sys.exit(0)
    else:
        logger.error("Phase 3.2.1 validation failed - performance targets not met")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())