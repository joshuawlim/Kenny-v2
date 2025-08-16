#!/usr/bin/env python3
"""
Basic Phase 3.5 Implementation Test

Validates the core functionality of our Phase 3.5 Calendar Database implementation
without external dependencies, focusing on performance targets and basic operations.
"""

import asyncio
import sys
import time
import logging
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Add calendar agent to path
sys.path.insert(0, str(Path(__file__).parent / "services" / "calendar-agent" / "src"))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("phase_3_5_basic_test")

try:
    from calendar_database import CalendarDatabase, DatabaseConfig, CalendarEvent
    from database_migration import DatabaseMigrationManager
    from database_integration import DatabaseCacheIntegration, IntegrationConfig
except ImportError as e:
    logger.error(f"Failed to import Phase 3.5 components: {e}")
    sys.exit(1)


class MockSemanticCache:
    """Mock semantic cache for testing."""
    
    def __init__(self):
        self.cache = {}
    
    async def get(self, key: str):
        return self.cache.get(key)
    
    async def set(self, key: str, value: Any, ttl: int = None):
        self.cache[key] = value
    
    async def delete(self, key: str):
        self.cache.pop(key, None)
    
    async def delete_pattern(self, pattern: str):
        # Simple pattern matching for testing
        keys_to_delete = [k for k in self.cache.keys() if pattern.replace('*', '') in k]
        for key in keys_to_delete:
            del self.cache[key]


class BasicPhase35Test:
    """Basic test suite for Phase 3.5 implementation."""
    
    def __init__(self):
        self.temp_dir = None
        self.db_path = None
        self.database = None
        self.migration_manager = None
        self.integration = None
        self.test_results = []
        
    async def setup(self):
        """Set up test environment."""
        logger.info("Setting up Phase 3.5 test environment...")
        
        # Create temporary directory and database path
        self.temp_dir = tempfile.mkdtemp(prefix="phase_3_5_test_")
        self.db_path = Path(self.temp_dir) / "test_calendar.db"
        
        logger.info(f"Test database path: {self.db_path}")
        
        # Initialize components
        config = DatabaseConfig(
            database_path=str(self.db_path),
            connection_pool_size=5,
            enable_fts=True
        )
        
        self.database = CalendarDatabase(config)
        self.migration_manager = DatabaseMigrationManager(str(self.db_path))
        
        # Mock cache for integration testing
        mock_cache = MockSemanticCache()
        integration_config = IntegrationConfig(enable_database=True)
        
        self.integration = DatabaseCacheIntegration(
            database=self.database,
            semantic_cache=mock_cache,
            cache_warming_service=None,
            cache_orchestrator=None,
            config=integration_config
        )
        
        logger.info("Test environment setup complete")
    
    async def teardown(self):
        """Clean up test environment."""
        logger.info("Cleaning up test environment...")
        
        if self.database:
            await self.database.cleanup()
        
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        logger.info("Test environment cleanup complete")
    
    async def test_database_initialization(self) -> Dict[str, Any]:
        """Test database initialization and migration."""
        logger.info("Testing database initialization...")
        start_time = time.time()
        
        try:
            # Test migration manager
            migration_result = await self.migration_manager.initialize_database()
            
            if not migration_result.success:
                return {
                    "test": "database_initialization",
                    "success": False,
                    "error": migration_result.error,
                    "execution_time": time.time() - start_time
                }
            
            # Test database initialization
            db_initialized = await self.database.initialize()
            
            if not db_initialized:
                return {
                    "test": "database_initialization",
                    "success": False,
                    "error": "Database initialization failed",
                    "execution_time": time.time() - start_time
                }
            
            execution_time = time.time() - start_time
            
            return {
                "test": "database_initialization",
                "success": True,
                "execution_time": execution_time,
                "performance_target_met": execution_time < 5.0,
                "migration_messages": migration_result.messages
            }
            
        except Exception as e:
            return {
                "test": "database_initialization",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_crud_operations(self) -> Dict[str, Any]:
        """Test basic CRUD operations performance."""
        logger.info("Testing CRUD operations...")
        start_time = time.time()
        
        try:
            operation_times = {}
            
            # Test CREATE
            create_start = time.time()
            event_data = {
                "calendar_id": "test-calendar",
                "title": "Test Event",
                "description": "Test event for CRUD operations",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "all_day": False
            }
            
            created_event = await self.database.create_event(event_data)
            create_time = time.time() - create_start
            operation_times["create"] = create_time
            
            if not created_event:
                return {
                    "test": "crud_operations",
                    "success": False,
                    "error": "Failed to create event"
                }
            
            event_id = created_event.id
            
            # Test READ
            read_start = time.time()
            retrieved_event = await self.database.get_event(event_id)
            read_time = time.time() - read_start
            operation_times["read"] = read_time
            
            if not retrieved_event:
                return {
                    "test": "crud_operations",
                    "success": False,
                    "error": "Failed to read event"
                }
            
            # Test UPDATE
            update_start = time.time()
            update_data = {"title": "Updated Test Event", "description": "Updated description"}
            updated_event = await self.database.update_event(event_id, update_data)
            update_time = time.time() - update_start
            operation_times["update"] = update_time
            
            if not updated_event:
                return {
                    "test": "crud_operations",
                    "success": False,
                    "error": "Failed to update event"
                }
            
            # Test DELETE
            delete_start = time.time()
            deleted = await self.database.delete_event(event_id)
            delete_time = time.time() - delete_start
            operation_times["delete"] = delete_time
            
            if not deleted:
                return {
                    "test": "crud_operations",
                    "success": False,
                    "error": "Failed to delete event"
                }
            
            execution_time = time.time() - start_time
            avg_operation_time = sum(operation_times.values()) / len(operation_times)
            
            return {
                "test": "crud_operations",
                "success": True,
                "execution_time": execution_time,
                "avg_operation_time": avg_operation_time,
                "performance_target_met": avg_operation_time < 5.0,
                "operation_breakdown": operation_times,
                "all_operations_under_5s": all(t < 5.0 for t in operation_times.values())
            }
            
        except Exception as e:
            return {
                "test": "crud_operations",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_list_events_performance(self) -> Dict[str, Any]:
        """Test list events query performance."""
        logger.info("Testing list events performance...")
        start_time = time.time()
        
        try:
            # Create test events
            test_events = []
            for i in range(20):  # Create 20 test events
                event_data = {
                    "calendar_id": "test-calendar",
                    "title": f"Test Event {i+1}",
                    "description": f"Test event {i+1} for performance testing",
                    "start_time": (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
                    "end_time": (datetime.now(timezone.utc) + timedelta(hours=i+1)).isoformat(),
                    "all_day": False
                }
                
                created_event = await self.database.create_event(event_data)
                if created_event:
                    test_events.append(created_event)
            
            # Test list query performance
            list_start = time.time()
            events = await self.database.list_events(
                calendar_id="test-calendar",
                limit=50
            )
            list_time = time.time() - list_start
            
            execution_time = time.time() - start_time
            
            return {
                "test": "list_events_performance",
                "success": True,
                "execution_time": execution_time,
                "list_query_time": list_time,
                "events_created": len(test_events),
                "events_retrieved": len(events),
                "performance_target_met": list_time < 5.0,
                "events_match": len(events) == len(test_events)
            }
            
        except Exception as e:
            return {
                "test": "list_events_performance",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_search_performance(self) -> Dict[str, Any]:
        """Test search functionality and performance."""
        logger.info("Testing search performance...")
        start_time = time.time()
        
        try:
            # Create events with searchable content
            search_events = [
                {"title": "Important Meeting", "description": "Quarterly review meeting"},
                {"title": "Team Standup", "description": "Daily standup meeting"},
                {"title": "Project Review", "description": "Important project milestone review"},
                {"title": "Client Call", "description": "Weekly client check-in call"}
            ]
            
            created_events = []
            for event_data in search_events:
                full_event_data = {
                    "calendar_id": "test-calendar",
                    "title": event_data["title"],
                    "description": event_data["description"],
                    "start_time": datetime.now(timezone.utc).isoformat(),
                    "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    "all_day": False
                }
                
                created_event = await self.database.create_event(full_event_data)
                if created_event:
                    created_events.append(created_event)
            
            # Test search performance
            search_start = time.time()
            search_results = await self.database.search_events("meeting")
            search_time = time.time() - search_start
            
            execution_time = time.time() - start_time
            
            return {
                "test": "search_performance",
                "success": True,
                "execution_time": execution_time,
                "search_query_time": search_time,
                "events_created": len(created_events),
                "search_results": len(search_results),
                "performance_target_met": search_time < 5.0,
                "search_accuracy": len(search_results) >= 2  # Should find at least 2 meetings
            }
            
        except Exception as e:
            return {
                "test": "search_performance",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_integration_layer(self) -> Dict[str, Any]:
        """Test database-cache integration layer."""
        logger.info("Testing integration layer...")
        start_time = time.time()
        
        try:
            # Test create through integration
            create_start = time.time()
            event_data = {
                "calendar_id": "integration-test",
                "title": "Integration Test Event",
                "description": "Test event for integration layer",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "all_day": False
            }
            
            created_event = await self.integration.create_event(event_data)
            create_time = time.time() - create_start
            
            if not created_event:
                return {
                    "test": "integration_layer",
                    "success": False,
                    "error": "Failed to create event through integration layer"
                }
            
            # Test get through integration (should hit cache)
            get_start = time.time()
            retrieved_event = await self.integration.get_event(created_event.id)
            get_time = time.time() - get_start
            
            if not retrieved_event:
                return {
                    "test": "integration_layer",
                    "success": False,
                    "error": "Failed to retrieve event through integration layer"
                }
            
            # Test list through integration
            list_start = time.time()
            events = await self.integration.list_events(calendar_id="integration-test")
            list_time = time.time() - list_start
            
            execution_time = time.time() - start_time
            avg_operation_time = (create_time + get_time + list_time) / 3
            
            # Get integration stats
            stats = self.integration.get_integration_stats()
            
            return {
                "test": "integration_layer",
                "success": True,
                "execution_time": execution_time,
                "avg_operation_time": avg_operation_time,
                "performance_target_met": avg_operation_time < 5.0,
                "create_time": create_time,
                "get_time": get_time,
                "list_time": list_time,
                "events_found": len(events),
                "integration_stats": stats
            }
            
        except Exception as e:
            return {
                "test": "integration_layer",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_concurrent_operations(self) -> Dict[str, Any]:
        """Test concurrent database operations."""
        logger.info("Testing concurrent operations...")
        start_time = time.time()
        
        try:
            # Create multiple concurrent tasks
            concurrent_tasks = []
            task_count = 10
            
            for i in range(task_count):
                if i % 3 == 0:
                    # Create operation
                    task = self._concurrent_create_operation(f"concurrent_event_{i}")
                elif i % 3 == 1:
                    # List operation
                    task = self._concurrent_list_operation()
                else:
                    # Search operation
                    task = self._concurrent_search_operation()
                
                concurrent_tasks.append(task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
            
            execution_time = time.time() - start_time
            
            # Analyze results
            successful_operations = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
            failed_operations = task_count - successful_operations
            avg_operation_time = execution_time / task_count
            
            return {
                "test": "concurrent_operations",
                "success": failed_operations == 0,
                "execution_time": execution_time,
                "avg_operation_time": avg_operation_time,
                "performance_target_met": avg_operation_time < 5.0,
                "concurrent_operations": task_count,
                "successful_operations": successful_operations,
                "failed_operations": failed_operations,
                "operations_per_second": task_count / execution_time
            }
            
        except Exception as e:
            return {
                "test": "concurrent_operations",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _concurrent_create_operation(self, title: str):
        """Helper for concurrent create operations."""
        try:
            event_data = {
                "calendar_id": "concurrent-test",
                "title": title,
                "description": "Concurrent test event",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "all_day": False
            }
            return await self.database.create_event(event_data)
        except Exception as e:
            logger.warning(f"Concurrent create failed: {e}")
            return None
    
    async def _concurrent_list_operation(self):
        """Helper for concurrent list operations."""
        try:
            return await self.database.list_events(limit=10)
        except Exception as e:
            logger.warning(f"Concurrent list failed: {e}")
            return []
    
    async def _concurrent_search_operation(self):
        """Helper for concurrent search operations."""
        try:
            return await self.database.search_events("test")
        except Exception as e:
            logger.warning(f"Concurrent search failed: {e}")
            return []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all Phase 3.5 tests."""
        logger.info("="*60)
        logger.info("STARTING BASIC PHASE 3.5 IMPLEMENTATION TESTS")
        logger.info("="*60)
        
        overall_start_time = time.time()
        
        try:
            await self.setup()
            
            # Define test sequence
            tests = [
                self.test_database_initialization,
                self.test_crud_operations,
                self.test_list_events_performance,
                self.test_search_performance,
                self.test_integration_layer,
                self.test_concurrent_operations
            ]
            
            # Execute tests
            for test_func in tests:
                logger.info(f"Running {test_func.__name__}...")
                result = await test_func()
                self.test_results.append(result)
                
                status = "✅ PASS" if result["success"] else "❌ FAIL"
                perf_status = "🚀 FAST" if result.get("performance_target_met", False) else "🐌 SLOW"
                exec_time = result.get("execution_time", 0)
                
                logger.info(f"  {status} {perf_status} {result['test']}: {exec_time:.3f}s")
                
                if result.get("error"):
                    logger.error(f"    Error: {result['error']}")
            
            total_execution_time = time.time() - overall_start_time
            
            # Generate report
            report = self._generate_test_report(total_execution_time)
            
            return report
            
        except Exception as e:
            logger.error(f"Test execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            await self.teardown()
    
    def _generate_test_report(self, total_execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive test report."""
        logger.info("="*60)
        logger.info("PHASE 3.5 IMPLEMENTATION TEST REPORT")
        logger.info("="*60)
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        performance_targets_met = sum(1 for r in self.test_results if r.get("performance_target_met", False))
        
        avg_execution_time = sum(r.get("execution_time", 0) for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        # Overall success determination
        overall_success = failed_tests == 0 and performance_targets_met >= total_tests * 0.8  # 80% performance target achievement
        
        report = {
            "execution_summary": {
                "total_execution_time": total_execution_time,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "performance_targets_met": performance_targets_met,
                "performance_success_rate": performance_targets_met / total_tests if total_tests > 0 else 0,
                "average_execution_time": avg_execution_time,
                "overall_success": overall_success,
                "phase_3_5_ready": overall_success
            },
            "test_results": self.test_results,
            "performance_analysis": {
                "under_5s_count": performance_targets_met,
                "under_5s_percentage": (performance_targets_met / total_tests) * 100 if total_tests > 0 else 0,
                "avg_test_time": avg_execution_time,
                "performance_target": 5.0,
                "target_achieved": avg_execution_time < 5.0
            },
            "recommendations": self._generate_recommendations()
        }
        
        # Log summary
        logger.info(f"EXECUTION SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        logger.info(f"  Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        logger.info(f"  Performance Targets Met: {performance_targets_met}/{total_tests} ({performance_targets_met/total_tests*100:.1f}%)")
        logger.info(f"  Average Execution Time: {avg_execution_time:.3f}s")
        logger.info(f"  Overall Success: {'✅ YES' if overall_success else '❌ NO'}")
        logger.info(f"  Phase 3.5 Ready: {'✅ YES' if overall_success else '❌ NO'}")
        
        if report["recommendations"]:
            logger.info("RECOMMENDATIONS:")
            for i, rec in enumerate(report["recommendations"], 1):
                logger.info(f"  {i}. {rec}")
        
        logger.info("="*60)
        
        return report
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on test results."""
        recommendations = []
        
        # Check for failed tests
        failed_tests = [r for r in self.test_results if not r["success"]]
        if failed_tests:
            recommendations.append(f"Address {len(failed_tests)} failed tests before Phase 3.5 deployment")
        
        # Check for performance issues
        slow_tests = [r for r in self.test_results if not r.get("performance_target_met", False)]
        if slow_tests:
            recommendations.append(f"Optimize {len(slow_tests)} operations exceeding <5s performance target")
        
        # Performance analysis
        avg_time = sum(r.get("execution_time", 0) for r in self.test_results) / len(self.test_results) if self.test_results else 0
        if avg_time > 5.0:
            recommendations.append("Overall average execution time exceeds 5s target - consider additional optimizations")
        
        # Success assessment
        pass_rate = sum(1 for r in self.test_results if r["success"]) / len(self.test_results) if self.test_results else 0
        if pass_rate < 1.0:
            recommendations.append("Achieve 100% test pass rate before Phase 3.5 implementation")
        elif avg_time < 5.0:
            recommendations.append("✅ Phase 3.5 implementation ready - all tests passed with <5s performance")
        
        return recommendations


async def main():
    """Main execution function."""
    test_suite = BasicPhase35Test()
    
    try:
        report = await test_suite.run_all_tests()
        
        # Determine exit code
        if report.get("execution_summary", {}).get("overall_success", False):
            logger.info("🎉 Phase 3.5 Basic Implementation Test: ALL TESTS PASSED")
            logger.info("✅ Ready for Phase 3.5 deployment!")
            sys.exit(0)
        else:
            logger.error("❌ Phase 3.5 Basic Implementation Test: TESTS FAILED")
            logger.error("🚫 Address failures before Phase 3.5 deployment")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())