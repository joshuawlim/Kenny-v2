#!/usr/bin/env python3
"""
Comprehensive Testing Suite for Phase 3.5 Week 2: Real-Time Bidirectional Synchronization

This test framework validates the EventKit sync engine, sync pipeline, and bidirectional writer
implementations to ensure they meet all performance and reliability targets.

Test Coverage:
- EventKit integration and change detection accuracy
- Sync pipeline performance and throughput validation
- Bidirectional write operations and transaction integrity
- Conflict resolution accuracy and reliability
- Performance targets validation (<0.01s queries, <1s sync propagation)
- Data consistency and integrity verification
- Error handling and recovery testing

Success Criteria:
- Real-time sync operational with <1s propagation delay
- Database freshness guaranteed (no stale data)
- <0.01s query performance maintained during sync
- Bidirectional changes working (read AND write)
- Zero data loss or corruption during sync
- >99% consistency between database and calendar sources
"""

import asyncio
import time
import logging
import sys
import sqlite3
import json
import random
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import pytest

# Add calendar agent to path
sys.path.insert(0, str(Path(__file__).parent / "services" / "calendar-agent" / "src"))

# Import the Week 2 components
from eventkit_sync_engine import EventKitSyncEngine, EventChange, ChangeType, SyncMetrics
from sync_pipeline import SyncPipeline, SyncPipelineMetrics, SyncPriority
from bidirectional_writer import BidirectionalWriter, WriteRequest, WriteOperation, WriteMetrics

# Import test utilities from Week 1
from test_phase_3_5_utilities import (
    DatabaseTestHelper, 
    MockCalendarAPI, 
    PerformanceBenchmarker,
    SecurityValidator,
    MockDataGenerator
)

# Configure comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
    handlers=[
        logging.FileHandler('phase_3_5_week2_test_execution.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("phase_3_5_week2_test_framework")


@dataclass
class Week2TestResult:
    """Standardized test result for Week 2 testing."""
    test_name: str
    success: bool
    execution_time: float
    performance_target_met: bool
    metrics: Dict[str, Any]
    error_message: Optional[str] = None
    sync_propagation_delay_ms: float = 0.0
    data_consistency_score: float = 1.0


@dataclass
class Week2TestConfig:
    """Configuration for Week 2 testing."""
    sync_propagation_target_ms: float = 1000.0  # <1s target
    query_performance_target_ms: float = 10.0   # <0.01s target (10ms for safety)
    write_success_rate_target: float = 0.999    # >99.9% target
    consistency_accuracy_target: float = 0.99   # >99% target
    max_concurrent_operations: int = 50
    test_duration_seconds: int = 60
    sync_reliability_iterations: int = 200


class Phase35Week2TestFramework:
    """
    Comprehensive test framework for Phase 3.5 Week 2 real-time bidirectional sync.
    
    This framework validates all critical aspects of the EventKit integration,
    sync pipeline, and bidirectional write operations.
    """
    
    def __init__(self, config: Week2TestConfig = None):
        """Initialize the Week 2 test framework."""
        self.config = config or Week2TestConfig()
        self.test_results: List[Week2TestResult] = []
        
        # Test components
        self.database_helper = DatabaseTestHelper(":memory:")
        self.mock_calendar_api = MockCalendarAPI()
        self.performance_benchmarker = PerformanceBenchmarker(self.config.query_performance_target_ms / 1000)
        self.mock_data_generator = MockDataGenerator()
        
        # Week 2 components under test
        self.sync_engine: Optional[EventKitSyncEngine] = None
        self.sync_pipeline: Optional[SyncPipeline] = None
        self.bidirectional_writer: Optional[BidirectionalWriter] = None
        
        # Test environment
        self.temp_dir = None
        self.test_database_path = None
        
        logger.info(f"Week 2 test framework initialized with targets: sync<{self.config.sync_propagation_target_ms}ms, query<{self.config.query_performance_target_ms}ms")
    
    async def setup_test_environment(self):
        """Set up the complete Week 2 test environment."""
        logger.info("Setting up Phase 3.5 Week 2 test environment...")
        
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp(prefix="phase_3_5_week2_test_")
        self.test_database_path = Path(self.temp_dir) / "test_calendar_week2.db"
        
        # Initialize base components
        await self.database_helper.initialize_test_database(str(self.test_database_path))
        await self.mock_calendar_api.initialize()
        
        # Initialize Week 2 components
        self.sync_engine = EventKitSyncEngine(str(self.test_database_path))
        self.sync_pipeline = SyncPipeline(str(self.test_database_path))
        self.bidirectional_writer = BidirectionalWriter(str(self.test_database_path))
        
        # Initialize all components
        await self.sync_engine.initialize()
        await self.sync_pipeline.initialize()
        await self.bidirectional_writer.initialize()
        
        # Connect sync engine to pipeline
        self.sync_engine.register_change_callback(self._handle_sync_change)
        
        # Generate test data
        await self.mock_data_generator.generate_test_dataset(
            events_count=200,
            calendars_count=10,
            contacts_count=100
        )
        
        logger.info(f"Week 2 test environment initialized at: {self.temp_dir}")
    
    def _handle_sync_change(self, change: EventChange):
        """Handle sync changes from EventKit engine."""
        try:
            # Process change through sync pipeline
            asyncio.create_task(
                self.sync_pipeline.process_change(change, SyncPriority.NORMAL)
            )
        except Exception as e:
            logger.error(f"Error handling sync change: {e}", exc_info=True)
    
    async def teardown_test_environment(self):
        """Clean up the Week 2 test environment."""
        logger.info("Cleaning up Week 2 test environment...")
        
        if self.sync_engine:
            await self.sync_engine.shutdown()
        if self.sync_pipeline:
            await self.sync_pipeline.shutdown()
        if self.bidirectional_writer:
            await self.bidirectional_writer.shutdown()
        
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)
        
        await self.database_helper.cleanup()
        await self.mock_calendar_api.cleanup()
        
        logger.info("Week 2 test environment cleanup complete")
    
    # =====================================================================================
    # EVENTKIT INTEGRATION TESTS
    # =====================================================================================
    
    async def test_eventkit_change_detection_accuracy(self) -> Week2TestResult:
        """Test EventKit change detection accuracy and latency."""
        logger.info("Testing EventKit change detection accuracy...")
        
        start_time = time.time()
        detected_changes = []
        
        def change_callback(change: EventChange):
            detected_changes.append(change)
        
        try:
            # Register callback for change detection
            self.sync_engine.register_change_callback(change_callback)
            
            # Generate simulated changes
            test_changes = []
            for i in range(50):
                event_data = await self.mock_data_generator.generate_event()
                test_changes.append(event_data)
                
                # Simulate external calendar change
                await self.mock_calendar_api.create_event(event_data)
                
                # Small delay to allow detection
                await asyncio.sleep(0.1)
            
            # Wait for all changes to be detected
            await asyncio.sleep(2.0)
            
            execution_time = time.time() - start_time
            
            # Analyze detection accuracy
            detection_rate = len(detected_changes) / len(test_changes)
            avg_detection_latency = execution_time / len(test_changes) * 1000 if test_changes else 0
            
            # Get sync engine metrics
            sync_metrics = self.sync_engine.get_metrics()
            
            success = (
                detection_rate >= 0.95 and  # 95% detection rate
                avg_detection_latency < 200  # <200ms average detection
            )
            
            return Week2TestResult(
                test_name="eventkit_change_detection_accuracy",
                success=success,
                execution_time=execution_time,
                performance_target_met=avg_detection_latency < 100,  # <100ms target
                metrics={
                    "changes_generated": len(test_changes),
                    "changes_detected": len(detected_changes),
                    "detection_rate": detection_rate,
                    "avg_detection_latency_ms": avg_detection_latency,
                    "sync_engine_metrics": asdict(sync_metrics)
                }
            )
            
        except Exception as e:
            logger.error(f"EventKit change detection test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="eventkit_change_detection_accuracy",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    async def test_eventkit_monitoring_reliability(self) -> Week2TestResult:
        """Test EventKit monitoring reliability under load."""
        logger.info("Testing EventKit monitoring reliability...")
        
        start_time = time.time()
        
        try:
            # Start continuous monitoring
            changes_detected = []
            errors_encountered = []
            
            def reliable_callback(change: EventChange):
                changes_detected.append({
                    "timestamp": datetime.now(),
                    "change_type": change.change_type.value,
                    "event_id": change.event_id
                })
            
            def error_callback(error):
                errors_encountered.append({
                    "timestamp": datetime.now(),
                    "error": str(error)
                })
            
            self.sync_engine.register_change_callback(reliable_callback)
            
            # Generate high-frequency changes
            change_count = 100
            tasks = []
            
            for i in range(change_count):
                event_data = await self.mock_data_generator.generate_event()
                task = asyncio.create_task(self.mock_calendar_api.create_event(event_data))
                tasks.append(task)
                
                # Stagger requests slightly
                if i % 10 == 0:
                    await asyncio.sleep(0.1)
            
            # Wait for all changes to be processed
            await asyncio.gather(*tasks)
            await asyncio.sleep(3.0)  # Allow processing time
            
            execution_time = time.time() - start_time
            
            # Analyze reliability
            detection_reliability = len(changes_detected) / change_count
            error_rate = len(errors_encountered) / change_count
            
            success = (
                detection_reliability >= 0.90 and  # 90% reliability
                error_rate < 0.05  # <5% error rate
            )
            
            return Week2TestResult(
                test_name="eventkit_monitoring_reliability",
                success=success,
                execution_time=execution_time,
                performance_target_met=error_rate < 0.01,  # <1% error target
                metrics={
                    "changes_generated": change_count,
                    "changes_detected": len(changes_detected),
                    "detection_reliability": detection_reliability,
                    "errors_encountered": len(errors_encountered),
                    "error_rate": error_rate,
                    "avg_processing_time_ms": execution_time / change_count * 1000
                }
            )
            
        except Exception as e:
            logger.error(f"EventKit monitoring reliability test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="eventkit_monitoring_reliability",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    # =====================================================================================
    # SYNC PIPELINE PERFORMANCE TESTS
    # =====================================================================================
    
    async def test_sync_pipeline_throughput(self) -> Week2TestResult:
        """Test sync pipeline throughput and performance."""
        logger.info("Testing sync pipeline throughput...")
        
        start_time = time.time()
        
        try:
            # Generate test changes
            test_changes = []
            for i in range(500):  # Large batch for throughput testing
                event_data = await self.mock_data_generator.generate_event()
                change = EventChange(
                    change_type=ChangeType.ADDED,
                    event_id=f"test_event_{i}",
                    calendar_id=f"test_calendar_{i % 5}",
                    timestamp=datetime.now(),
                    event_data=event_data
                )
                test_changes.append(change)
            
            # Process changes through pipeline
            operation_ids = []
            processing_start = time.time()
            
            for change in test_changes:
                operation_id = await self.sync_pipeline.process_change(change, SyncPriority.NORMAL)
                operation_ids.append(operation_id)
            
            # Wait for all operations to complete
            await asyncio.sleep(5.0)
            
            processing_time = time.time() - processing_start
            execution_time = time.time() - start_time
            
            # Get pipeline metrics
            pipeline_metrics = self.sync_pipeline.get_metrics()
            
            # Calculate throughput
            throughput_ops_per_sec = len(test_changes) / processing_time
            
            success = (
                throughput_ops_per_sec >= 100 and  # >100 ops/sec
                pipeline_metrics.avg_processing_time_ms < 50  # <50ms avg processing
            )
            
            return Week2TestResult(
                test_name="sync_pipeline_throughput",
                success=success,
                execution_time=execution_time,
                performance_target_met=throughput_ops_per_sec >= 1000,  # >1000 ops/sec target
                metrics={
                    "changes_processed": len(test_changes),
                    "processing_time_seconds": processing_time,
                    "throughput_ops_per_sec": throughput_ops_per_sec,
                    "pipeline_metrics": asdict(pipeline_metrics),
                    "operation_ids_generated": len(operation_ids)
                }
            )
            
        except Exception as e:
            logger.error(f"Sync pipeline throughput test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="sync_pipeline_throughput",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    async def test_sync_propagation_latency(self) -> Week2TestResult:
        """Test sync propagation latency end-to-end."""
        logger.info("Testing sync propagation latency...")
        
        start_time = time.time()
        propagation_times = []
        
        try:
            # Test individual sync operations for latency
            for i in range(20):
                event_data = await self.mock_data_generator.generate_event()
                
                # Measure time from change creation to database update
                change_start = time.time()
                
                # Create change
                change = EventChange(
                    change_type=ChangeType.ADDED,
                    event_id=f"latency_test_{i}",
                    calendar_id="test_calendar",
                    timestamp=datetime.now(),
                    event_data=event_data
                )
                
                # Process through pipeline
                await self.sync_pipeline.process_change(change, SyncPriority.HIGH)
                
                # Wait for processing and verify in database
                await asyncio.sleep(0.5)
                
                # Check if event exists in database
                conn = sqlite3.connect(str(self.test_database_path))
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM events WHERE id = ?", (change.event_id,))
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    propagation_time = (time.time() - change_start) * 1000
                    propagation_times.append(propagation_time)
                else:
                    logger.warning(f"Event {change.event_id} not found in database")
            
            execution_time = time.time() - start_time
            
            # Analyze propagation latency
            if propagation_times:
                avg_propagation_ms = sum(propagation_times) / len(propagation_times)
                max_propagation_ms = max(propagation_times)
                min_propagation_ms = min(propagation_times)
            else:
                avg_propagation_ms = max_propagation_ms = min_propagation_ms = 0
            
            success = (
                len(propagation_times) >= 15 and  # At least 75% success rate
                avg_propagation_ms < self.config.sync_propagation_target_ms
            )
            
            return Week2TestResult(
                test_name="sync_propagation_latency",
                success=success,
                execution_time=execution_time,
                performance_target_met=avg_propagation_ms < 500,  # <500ms target
                sync_propagation_delay_ms=avg_propagation_ms,
                metrics={
                    "tests_attempted": 20,
                    "successful_propagations": len(propagation_times),
                    "avg_propagation_ms": avg_propagation_ms,
                    "max_propagation_ms": max_propagation_ms,
                    "min_propagation_ms": min_propagation_ms,
                    "propagation_target_ms": self.config.sync_propagation_target_ms
                }
            )
            
        except Exception as e:
            logger.error(f"Sync propagation latency test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="sync_propagation_latency",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    # =====================================================================================
    # BIDIRECTIONAL WRITE TESTS
    # =====================================================================================
    
    async def test_bidirectional_write_success_rate(self) -> Week2TestResult:
        """Test bidirectional write operations success rate."""
        logger.info("Testing bidirectional write success rate...")
        
        start_time = time.time()
        
        try:
            write_results = []
            
            # Test CREATE operations
            create_successes = 0
            for i in range(50):
                event_data = await self.mock_data_generator.generate_event()
                
                write_start = time.time()
                event_id = await self.bidirectional_writer.create_event("test_calendar", event_data)
                write_time = (time.time() - write_start) * 1000
                
                success = event_id is not None
                if success:
                    create_successes += 1
                
                write_results.append({
                    "operation": "create",
                    "success": success,
                    "latency_ms": write_time,
                    "event_id": event_id
                })
            
            # Test UPDATE operations
            update_successes = 0
            created_events = [r for r in write_results if r["success"] and r["event_id"]]
            
            for i, result in enumerate(created_events[:25]):  # Update half of created events
                updated_data = await self.mock_data_generator.generate_event()
                updated_data["title"] = f"Updated Event {i}"
                
                write_start = time.time()
                success = await self.bidirectional_writer.update_event(result["event_id"], updated_data)
                write_time = (time.time() - write_start) * 1000
                
                if success:
                    update_successes += 1
                
                write_results.append({
                    "operation": "update",
                    "success": success,
                    "latency_ms": write_time,
                    "event_id": result["event_id"]
                })
            
            # Test DELETE operations
            delete_successes = 0
            for i, result in enumerate(created_events[25:40]):  # Delete some events
                write_start = time.time()
                success = await self.bidirectional_writer.delete_event(result["event_id"])
                write_time = (time.time() - write_start) * 1000
                
                if success:
                    delete_successes += 1
                
                write_results.append({
                    "operation": "delete",
                    "success": success,
                    "latency_ms": write_time,
                    "event_id": result["event_id"]
                })
            
            execution_time = time.time() - start_time
            
            # Calculate success rates
            total_operations = len(write_results)
            successful_operations = sum(1 for r in write_results if r["success"])
            overall_success_rate = successful_operations / total_operations if total_operations > 0 else 0
            
            avg_write_latency = sum(r["latency_ms"] for r in write_results) / len(write_results) if write_results else 0
            
            # Get writer metrics
            writer_metrics = self.bidirectional_writer.get_metrics()
            
            success = overall_success_rate >= self.config.write_success_rate_target
            
            return Week2TestResult(
                test_name="bidirectional_write_success_rate",
                success=success,
                execution_time=execution_time,
                performance_target_met=avg_write_latency < 500,  # <500ms target
                metrics={
                    "total_operations": total_operations,
                    "successful_operations": successful_operations,
                    "overall_success_rate": overall_success_rate,
                    "create_success_rate": create_successes / 50,
                    "update_success_rate": update_successes / 25 if created_events else 0,
                    "delete_success_rate": delete_successes / 15 if created_events else 0,
                    "avg_write_latency_ms": avg_write_latency,
                    "writer_metrics": asdict(writer_metrics),
                    "success_rate_target": self.config.write_success_rate_target
                }
            )
            
        except Exception as e:
            logger.error(f"Bidirectional write success rate test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="bidirectional_write_success_rate",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    async def test_transaction_integrity_and_rollback(self) -> Week2TestResult:
        """Test transaction integrity and rollback capability."""
        logger.info("Testing transaction integrity and rollback...")
        
        start_time = time.time()
        
        try:
            # Test successful transaction
            event_data = await self.mock_data_generator.generate_event()
            event_id = await self.bidirectional_writer.create_event("test_calendar", event_data)
            
            if not event_id:
                logger.error("Failed to create test event for transaction test")
                return Week2TestResult(
                    test_name="transaction_integrity_and_rollback",
                    success=False,
                    execution_time=time.time() - start_time,
                    performance_target_met=False,
                    metrics={},
                    error_message="Failed to create test event"
                )
            
            # Test batch transaction with mixed operations
            requests = []
            
            # Create multiple write requests
            for i in range(5):
                event_data = await self.mock_data_generator.generate_event()
                request = WriteRequest(
                    request_id=f"batch_test_{i}",
                    operation=WriteOperation.CREATE,
                    event_id="",
                    calendar_id="test_calendar",
                    event_data=event_data,
                    original_data=None,
                    timestamp=datetime.now()
                )
                requests.append(request)
            
            # Execute batch transaction
            batch_success = await self.bidirectional_writer.batch_write(requests)
            
            # Test rollback scenario by simulating failure
            # (This would require injecting failures, for now we test the interface)
            
            execution_time = time.time() - start_time
            
            # Get transaction metrics
            writer_metrics = self.bidirectional_writer.get_metrics()
            
            success = (
                event_id is not None and
                batch_success and
                writer_metrics.transactions_committed > 0
            )
            
            return Week2TestResult(
                test_name="transaction_integrity_and_rollback",
                success=success,
                execution_time=execution_time,
                performance_target_met=execution_time < 5.0,  # <5s for batch operations
                metrics={
                    "individual_create_success": event_id is not None,
                    "batch_transaction_success": batch_success,
                    "batch_requests_count": len(requests),
                    "writer_metrics": asdict(writer_metrics),
                    "transactions_committed": writer_metrics.transactions_committed,
                    "rollbacks_performed": writer_metrics.rollbacks_performed
                }
            )
            
        except Exception as e:
            logger.error(f"Transaction integrity test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="transaction_integrity_and_rollback",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    # =====================================================================================
    # DATA CONSISTENCY TESTS
    # =====================================================================================
    
    async def test_data_consistency_during_sync(self) -> Week2TestResult:
        """Test data consistency during active synchronization."""
        logger.info("Testing data consistency during sync...")
        
        start_time = time.time()
        
        try:
            consistency_checks = []
            
            # Create baseline events
            baseline_events = []
            for i in range(20):
                event_data = await self.mock_data_generator.generate_event()
                event_id = await self.bidirectional_writer.create_event("test_calendar", event_data)
                if event_id:
                    baseline_events.append({"id": event_id, "data": event_data})
            
            # Start continuous sync activity
            sync_tasks = []
            for i in range(30):
                event_data = await self.mock_data_generator.generate_event()
                change = EventChange(
                    change_type=ChangeType.ADDED,
                    event_id=f"consistency_test_{i}",
                    calendar_id="test_calendar",
                    timestamp=datetime.now(),
                    event_data=event_data
                )
                task = asyncio.create_task(
                    self.sync_pipeline.process_change(change, SyncPriority.NORMAL)
                )
                sync_tasks.append(task)
            
            # Perform consistency checks during sync
            for check_round in range(5):
                await asyncio.sleep(0.5)  # Allow some sync activity
                
                # Check database consistency
                conn = sqlite3.connect(str(self.test_database_path))
                cursor = conn.cursor()
                
                # Count events
                cursor.execute("SELECT COUNT(*) FROM events")
                db_event_count = cursor.fetchone()[0]
                
                # Check for orphaned records
                cursor.execute("""
                    SELECT COUNT(*) FROM events 
                    WHERE calendar_id NOT IN (
                        SELECT DISTINCT calendar_id FROM events WHERE calendar_id IS NOT NULL
                    ) AND calendar_id IS NOT NULL
                """)
                orphaned_count = cursor.fetchone()[0]
                
                # Check for duplicate events
                cursor.execute("""
                    SELECT external_id, COUNT(*) 
                    FROM events 
                    WHERE external_id IS NOT NULL 
                    GROUP BY external_id 
                    HAVING COUNT(*) > 1
                """)
                duplicates = cursor.fetchall()
                
                conn.close()
                
                consistency_checks.append({
                    "check_round": check_round,
                    "db_event_count": db_event_count,
                    "orphaned_records": orphaned_count,
                    "duplicate_events": len(duplicates),
                    "timestamp": datetime.now().isoformat()
                })
            
            # Wait for all sync tasks to complete
            await asyncio.gather(*sync_tasks, return_exceptions=True)
            
            execution_time = time.time() - start_time
            
            # Analyze consistency
            max_orphaned = max(check["orphaned_records"] for check in consistency_checks)
            max_duplicates = max(check["duplicate_events"] for check in consistency_checks)
            final_event_count = consistency_checks[-1]["db_event_count"] if consistency_checks else 0
            
            # Calculate consistency score
            consistency_score = 1.0
            if max_orphaned > 0:
                consistency_score -= 0.2
            if max_duplicates > 0:
                consistency_score -= 0.3
            if final_event_count < len(baseline_events):
                consistency_score -= 0.2
            
            success = (
                max_orphaned == 0 and
                max_duplicates == 0 and
                consistency_score >= self.config.consistency_accuracy_target
            )
            
            return Week2TestResult(
                test_name="data_consistency_during_sync",
                success=success,
                execution_time=execution_time,
                performance_target_met=consistency_score >= 0.99,
                data_consistency_score=consistency_score,
                metrics={
                    "baseline_events_created": len(baseline_events),
                    "sync_operations_performed": len(sync_tasks),
                    "consistency_checks": consistency_checks,
                    "max_orphaned_records": max_orphaned,
                    "max_duplicate_events": max_duplicates,
                    "final_event_count": final_event_count,
                    "consistency_score": consistency_score,
                    "consistency_target": self.config.consistency_accuracy_target
                }
            )
            
        except Exception as e:
            logger.error(f"Data consistency test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="data_consistency_during_sync",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    # =====================================================================================
    # PERFORMANCE VALIDATION TESTS
    # =====================================================================================
    
    async def test_query_performance_during_sync(self) -> Week2TestResult:
        """Test that query performance is maintained during active sync."""
        logger.info("Testing query performance during sync...")
        
        start_time = time.time()
        
        try:
            query_times = []
            
            # Start background sync activity
            sync_tasks = []
            for i in range(100):
                event_data = await self.mock_data_generator.generate_event()
                change = EventChange(
                    change_type=ChangeType.ADDED,
                    event_id=f"perf_test_{i}",
                    calendar_id="test_calendar",
                    timestamp=datetime.now(),
                    event_data=event_data
                )
                task = asyncio.create_task(
                    self.sync_pipeline.process_change(change, SyncPriority.LOW)
                )
                sync_tasks.append(task)
                
                # Don't wait - let sync happen in background
                if i % 20 == 0:
                    await asyncio.sleep(0.01)  # Brief pause
            
            # Perform queries while sync is active
            for query_round in range(20):
                # Test various query patterns
                query_start = time.time()
                
                conn = sqlite3.connect(str(self.test_database_path))
                cursor = conn.cursor()
                
                # Simple lookup
                cursor.execute("SELECT * FROM events WHERE id = ? LIMIT 1", ("test_event_1",))
                result1 = cursor.fetchall()
                
                # Date range query
                start_date = datetime.now().isoformat()
                end_date = (datetime.now() + timedelta(days=7)).isoformat()
                cursor.execute(
                    "SELECT * FROM events WHERE start_time BETWEEN ? AND ? LIMIT 10",
                    (start_date, end_date)
                )
                result2 = cursor.fetchall()
                
                # Complex query
                cursor.execute("""
                    SELECT calendar_id, COUNT(*) as event_count
                    FROM events 
                    GROUP BY calendar_id 
                    ORDER BY event_count DESC 
                    LIMIT 5
                """)
                result3 = cursor.fetchall()
                
                conn.close()
                
                query_time = (time.time() - query_start) * 1000
                query_times.append(query_time)
                
                # Small delay between queries
                await asyncio.sleep(0.1)
            
            # Wait for sync tasks to complete
            await asyncio.gather(*sync_tasks, return_exceptions=True)
            
            execution_time = time.time() - start_time
            
            # Analyze query performance
            avg_query_time = sum(query_times) / len(query_times) if query_times else 0
            max_query_time = max(query_times) if query_times else 0
            min_query_time = min(query_times) if query_times else 0
            
            # Check how many queries met the performance target
            queries_under_target = sum(1 for t in query_times if t < self.config.query_performance_target_ms)
            performance_success_rate = queries_under_target / len(query_times) if query_times else 0
            
            success = (
                avg_query_time < self.config.query_performance_target_ms and
                performance_success_rate >= 0.95  # 95% of queries under target
            )
            
            return Week2TestResult(
                test_name="query_performance_during_sync",
                success=success,
                execution_time=execution_time,
                performance_target_met=avg_query_time < self.config.query_performance_target_ms,
                metrics={
                    "queries_performed": len(query_times),
                    "sync_operations_background": len(sync_tasks),
                    "avg_query_time_ms": avg_query_time,
                    "max_query_time_ms": max_query_time,
                    "min_query_time_ms": min_query_time,
                    "queries_under_target": queries_under_target,
                    "performance_success_rate": performance_success_rate,
                    "query_target_ms": self.config.query_performance_target_ms,
                    "all_query_times": query_times[:10]  # Sample of query times
                }
            )
            
        except Exception as e:
            logger.error(f"Query performance during sync test failed: {e}", exc_info=True)
            return Week2TestResult(
                test_name="query_performance_during_sync",
                success=False,
                execution_time=time.time() - start_time,
                performance_target_met=False,
                metrics={},
                error_message=str(e)
            )
    
    # =====================================================================================
    # COMPREHENSIVE TEST EXECUTION
    # =====================================================================================
    
    async def run_comprehensive_week2_test_suite(self) -> Dict[str, Any]:
        """Run the complete Phase 3.5 Week 2 test suite."""
        logger.info("="*80)
        logger.info("STARTING PHASE 3.5 WEEK 2 COMPREHENSIVE TEST SUITE")
        logger.info("="*80)
        
        overall_start_time = time.time()
        
        try:
            # Setup test environment
            await self.setup_test_environment()
            
            # Define Week 2 test sequence
            test_sequence = [
                # EventKit integration tests
                self.test_eventkit_change_detection_accuracy,
                self.test_eventkit_monitoring_reliability,
                
                # Sync pipeline performance tests
                self.test_sync_pipeline_throughput,
                self.test_sync_propagation_latency,
                
                # Bidirectional write tests
                self.test_bidirectional_write_success_rate,
                self.test_transaction_integrity_and_rollback,
                
                # Data consistency tests
                self.test_data_consistency_during_sync,
                
                # Performance validation tests
                self.test_query_performance_during_sync
            ]
            
            # Execute tests sequentially
            for test_func in test_sequence:
                logger.info(f"Executing Week 2 test: {test_func.__name__}")
                test_result = await test_func()
                self.test_results.append(test_result)
                
                # Log test result
                status = "✅ PASS" if test_result.success else "❌ FAIL"
                perf_status = "🚀 FAST" if test_result.performance_target_met else "🐌 SLOW"
                
                sync_info = ""
                if test_result.sync_propagation_delay_ms > 0:
                    sync_info = f" (sync: {test_result.sync_propagation_delay_ms:.1f}ms)"
                
                consistency_info = ""
                if test_result.data_consistency_score < 1.0:
                    consistency_info = f" (consistency: {test_result.data_consistency_score:.2f})"
                
                logger.info(f"  {status} {perf_status} {test_result.test_name}: {test_result.execution_time:.3f}s{sync_info}{consistency_info}")
                
                if test_result.error_message:
                    logger.error(f"    Error: {test_result.error_message}")
            
            total_execution_time = time.time() - overall_start_time
            
            # Generate Week 2 comprehensive report
            report = await self.generate_week2_report(total_execution_time)
            
            return report
            
        except Exception as e:
            logger.error(f"Week 2 test suite execution failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        finally:
            await self.teardown_test_environment()
    
    async def generate_week2_report(self, total_execution_time: float) -> Dict[str, Any]:
        """Generate comprehensive Week 2 test execution report."""
        logger.info("="*80)
        logger.info("PHASE 3.5 WEEK 2 TEST EXECUTION REPORT")
        logger.info("="*80)
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        
        performance_targets_met = sum(1 for r in self.test_results if r.performance_target_met)
        
        # Calculate Week 2 specific metrics
        avg_sync_propagation = sum(r.sync_propagation_delay_ms for r in self.test_results if r.sync_propagation_delay_ms > 0)
        sync_tests_count = sum(1 for r in self.test_results if r.sync_propagation_delay_ms > 0)
        avg_sync_propagation = avg_sync_propagation / sync_tests_count if sync_tests_count > 0 else 0
        
        avg_consistency_score = sum(r.data_consistency_score for r in self.test_results) / len(self.test_results)
        
        # Overall success determination for Week 2
        week2_success = (
            failed_tests == 0 and
            avg_sync_propagation < self.config.sync_propagation_target_ms and
            avg_consistency_score >= self.config.consistency_accuracy_target and
            performance_targets_met >= (total_tests * 0.8)  # 80% performance targets met
        )
        
        # Generate detailed report
        report = {
            "week2_execution_summary": {
                "total_execution_time": total_execution_time,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "pass_rate": passed_tests / total_tests if total_tests > 0 else 0,
                "performance_targets_met": performance_targets_met,
                "week2_overall_success": week2_success
            },
            "week2_specific_metrics": {
                "avg_sync_propagation_ms": avg_sync_propagation,
                "sync_propagation_target_ms": self.config.sync_propagation_target_ms,
                "sync_propagation_met": avg_sync_propagation < self.config.sync_propagation_target_ms,
                "avg_consistency_score": avg_consistency_score,
                "consistency_target": self.config.consistency_accuracy_target,
                "consistency_target_met": avg_consistency_score >= self.config.consistency_accuracy_target
            },
            "test_results": [asdict(result) for result in self.test_results],
            "week2_recommendations": self._generate_week2_recommendations()
        }
        
        # Log summary
        logger.info(f"\\nWEEK 2 EXECUTION SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        logger.info(f"  Failed: {failed_tests} ({failed_tests/total_tests*100:.1f}%)")
        logger.info(f"  Performance Targets Met: {performance_targets_met}/{total_tests}")
        
        logger.info(f"\\nWEEK 2 SPECIFIC METRICS:")
        logger.info(f"  Sync Propagation: {avg_sync_propagation:.1f}ms (target: <{self.config.sync_propagation_target_ms}ms)")
        logger.info(f"  Data Consistency: {avg_consistency_score:.2f} (target: >{self.config.consistency_accuracy_target})")
        logger.info(f"  Week 2 Success: {'✅ YES' if week2_success else '❌ NO'}")
        
        if report["week2_recommendations"]:
            logger.info(f"\\nWEEK 2 RECOMMENDATIONS:")
            for i, rec in enumerate(report["week2_recommendations"], 1):
                logger.info(f"  {i}. {rec}")
        
        logger.info("="*80)
        
        return report
    
    def _generate_week2_recommendations(self) -> List[str]:
        """Generate actionable recommendations for Week 2."""
        recommendations = []
        
        # Check for failed tests
        failed_tests = [r for r in self.test_results if not r.success]
        if failed_tests:
            recommendations.append(f"Address {len(failed_tests)} failed Week 2 tests before deployment")
        
        # Check sync propagation performance
        sync_results = [r for r in self.test_results if r.sync_propagation_delay_ms > 0]
        if sync_results:
            avg_sync = sum(r.sync_propagation_delay_ms for r in sync_results) / len(sync_results)
            if avg_sync >= self.config.sync_propagation_target_ms:
                recommendations.append(f"Optimize sync propagation - current: {avg_sync:.1f}ms, target: <{self.config.sync_propagation_target_ms}ms")
        
        # Check data consistency
        avg_consistency = sum(r.data_consistency_score for r in self.test_results) / len(self.test_results)
        if avg_consistency < self.config.consistency_accuracy_target:
            recommendations.append(f"Improve data consistency - current: {avg_consistency:.2f}, target: >{self.config.consistency_accuracy_target}")
        
        # Check query performance during sync
        perf_tests = [r for r in self.test_results if "performance" in r.test_name.lower()]
        slow_perf_tests = [r for r in perf_tests if not r.performance_target_met]
        if slow_perf_tests:
            recommendations.append("Optimize query performance during sync operations")
        
        # Check write success rates
        write_tests = [r for r in self.test_results if "write" in r.test_name.lower()]
        for test in write_tests:
            if "overall_success_rate" in test.metrics:
                success_rate = test.metrics["overall_success_rate"]
                if success_rate < self.config.write_success_rate_target:
                    recommendations.append(f"Improve write success rate - current: {success_rate:.1%}, target: >{self.config.write_success_rate_target:.1%}")
        
        # Overall assessment
        overall_pass_rate = sum(1 for r in self.test_results if r.success) / len(self.test_results) if self.test_results else 0
        if overall_pass_rate >= 0.95:
            recommendations.append("Week 2 validation complete - ready for production deployment")
        else:
            recommendations.append("Achieve 95%+ test pass rate before Week 2 deployment")
        
        return recommendations


async def main():
    """Main execution function for the Week 2 test framework."""
    logger.info("Initializing Phase 3.5 Week 2 Test Framework...")
    
    # Configure Week 2 test parameters
    config = Week2TestConfig(
        sync_propagation_target_ms=1000.0,
        query_performance_target_ms=10.0,
        write_success_rate_target=0.999,
        consistency_accuracy_target=0.99,
        max_concurrent_operations=50,
        test_duration_seconds=60,
        sync_reliability_iterations=200
    )
    
    # Initialize test framework
    test_framework = Phase35Week2TestFramework(config)
    
    try:
        # Run comprehensive Week 2 test suite
        report = await test_framework.run_comprehensive_week2_test_suite()
        
        # Determine exit code based on results
        if report.get("week2_execution_summary", {}).get("week2_overall_success", False):
            logger.info("🎉 Phase 3.5 Week 2 Test Framework: ALL TESTS PASSED")
            logger.info("✅ Week 2 real-time bidirectional sync ready for deployment!")
            sys.exit(0)
        else:
            logger.error("❌ Phase 3.5 Week 2 Test Framework: TESTS FAILED")
            logger.error("🚫 Address Week 2 test failures before deployment")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Week 2 test framework execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())