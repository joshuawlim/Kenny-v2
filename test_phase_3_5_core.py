#!/usr/bin/env python3
"""
Core Phase 3.5 Database Test

Tests the core SQLite database functionality without external dependencies,
focusing on performance targets and database operations.
"""

import asyncio
import sys
import time
import logging
import tempfile
import sqlite3
import aiosqlite
import json
import hashlib
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("phase_3_5_core_test")


@dataclass
class CalendarEvent:
    """Calendar event data model."""
    id: str
    calendar_id: str
    title: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime = None
    end_time: datetime = None
    all_day: bool = False
    recurrence_rule: Optional[str] = None
    status: str = "confirmed"
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    sync_token: Optional[str] = None
    last_sync: Optional[datetime] = None
    api_event_id: Optional[str] = None
    checksum: Optional[str] = None


class CoreCalendarDatabase:
    """Core calendar database for testing."""
    
    def __init__(self, database_path: str):
        """Initialize database."""
        self.database_path = database_path
        self.connection = None
        self.is_initialized = False
        
    async def initialize(self) -> bool:
        """Initialize database with schema."""
        try:
            self.connection = await aiosqlite.connect(self.database_path)
            await self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Create schema
            await self._create_schema()
            await self._create_indexes()
            await self._set_pragmas()
            
            self.is_initialized = True
            logger.info("Core database initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False
    
    async def _create_schema(self):
        """Create database schema."""
        schema_sql = [
            """
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                calendar_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                location TEXT,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP NOT NULL,
                all_day BOOLEAN DEFAULT 0,
                recurrence_rule TEXT,
                status TEXT DEFAULT 'confirmed',
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_token TEXT,
                last_sync TIMESTAMP,
                api_event_id TEXT,
                checksum TEXT
            )
            """
        ]
        
        for sql in schema_sql:
            await self.connection.execute(sql)
        
        await self.connection.commit()
    
    async def _create_indexes(self):
        """Create performance indexes."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_events_calendar_id ON events (calendar_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_start_time ON events (start_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_title ON events (title)"
        ]
        
        for index_sql in indexes:
            await self.connection.execute(index_sql)
        
        await self.connection.commit()
    
    async def _set_pragmas(self):
        """Set performance pragmas."""
        pragmas = [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = -64000"
        ]
        
        for pragma in pragmas:
            await self.connection.execute(pragma)
    
    async def create_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Create event."""
        try:
            event_id = event_data.get("id", str(uuid.uuid4()))
            checksum = self._calculate_checksum(event_data)
            
            now = datetime.now(timezone.utc)
            
            await self.connection.execute("""
                INSERT INTO events (
                    id, calendar_id, title, description, location,
                    start_time, end_time, all_day, status, checksum,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                event_data.get("calendar_id"),
                event_data.get("title"),
                event_data.get("description"),
                event_data.get("location"),
                event_data.get("start_time"),
                event_data.get("end_time"),
                event_data.get("all_day", False),
                event_data.get("status", "confirmed"),
                checksum,
                now.isoformat(),
                now.isoformat()
            ))
            
            await self.connection.commit()
            return await self.get_event(event_id)
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}")
            return None
    
    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Get event by ID."""
        try:
            cursor = await self.connection.execute(
                "SELECT * FROM events WHERE id = ?", (event_id,)
            )
            row = await cursor.fetchone()
            
            if row:
                columns = [desc[0] for desc in cursor.description]
                event_data = dict(zip(columns, row))
                return CalendarEvent(**self._normalize_event_data(event_data))
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get event: {e}")
            return None
    
    async def list_events(self, calendar_id: Optional[str] = None, limit: int = 100) -> List[CalendarEvent]:
        """List events."""
        try:
            sql = "SELECT * FROM events"
            params = []
            
            if calendar_id:
                sql += " WHERE calendar_id = ?"
                params.append(calendar_id)
            
            sql += " ORDER BY start_time ASC LIMIT ?"
            params.append(limit)
            
            cursor = await self.connection.execute(sql, params)
            rows = await cursor.fetchall()
            
            events = []
            if rows:
                columns = [desc[0] for desc in cursor.description]
                for row in rows:
                    event_data = dict(zip(columns, row))
                    events.append(CalendarEvent(**self._normalize_event_data(event_data)))
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to list events: {e}")
            return []
    
    async def update_event(self, event_id: str, update_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Update event."""
        try:
            # Build update query
            set_clauses = []
            params = []
            
            for key, value in update_data.items():
                if key != "id":
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            set_clauses.append("updated_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())
            params.append(event_id)
            
            await self.connection.execute(
                f"UPDATE events SET {', '.join(set_clauses)} WHERE id = ?",
                params
            )
            await self.connection.commit()
            
            return await self.get_event(event_id)
            
        except Exception as e:
            logger.error(f"Failed to update event: {e}")
            return None
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete event."""
        try:
            cursor = await self.connection.execute(
                "DELETE FROM events WHERE id = ?", (event_id,)
            )
            await self.connection.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            logger.error(f"Failed to delete event: {e}")
            return False
    
    def _calculate_checksum(self, event_data: Dict[str, Any]) -> str:
        """Calculate event checksum."""
        normalized_data = {
            "title": event_data.get("title", ""),
            "description": event_data.get("description", ""),
            "start_time": str(event_data.get("start_time", "")),
            "end_time": str(event_data.get("end_time", ""))
        }
        
        data_string = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _normalize_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event data."""
        normalized = {}
        
        for key, value in event_data.items():
            if key in ["start_time", "end_time", "created_at", "updated_at", "last_sync"]:
                if value and isinstance(value, str):
                    try:
                        normalized[key] = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except:
                        normalized[key] = value
                else:
                    normalized[key] = value
            else:
                normalized[key] = value
        
        return normalized
    
    async def cleanup(self):
        """Cleanup database."""
        if self.connection:
            await self.connection.close()


class CorePhase35Test:
    """Core Phase 3.5 database test."""
    
    def __init__(self):
        self.temp_dir = None
        self.db_path = None
        self.database = None
        self.test_results = []
        
    async def setup(self):
        """Setup test environment."""
        logger.info("Setting up core test environment...")
        
        self.temp_dir = tempfile.mkdtemp(prefix="phase_3_5_core_")
        self.db_path = Path(self.temp_dir) / "test_calendar.db"
        
        self.database = CoreCalendarDatabase(str(self.db_path))
        
        logger.info(f"Test database: {self.db_path}")
    
    async def teardown(self):
        """Teardown test environment."""
        logger.info("Cleaning up core test environment...")
        
        if self.database:
            await self.database.cleanup()
        
        if self.temp_dir:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    async def test_database_initialization(self) -> Dict[str, Any]:
        """Test database initialization."""
        logger.info("Testing database initialization...")
        start_time = time.time()
        
        try:
            success = await self.database.initialize()
            execution_time = time.time() - start_time
            
            return {
                "test": "database_initialization",
                "success": success,
                "execution_time": execution_time,
                "performance_target_met": execution_time < 5.0
            }
            
        except Exception as e:
            return {
                "test": "database_initialization",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_crud_performance(self) -> Dict[str, Any]:
        """Test CRUD operations performance."""
        logger.info("Testing CRUD performance...")
        start_time = time.time()
        
        try:
            operation_times = {}
            
            # CREATE
            create_start = time.time()
            event_data = {
                "calendar_id": "test-calendar",
                "title": "Performance Test Event",
                "description": "Testing CRUD performance",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            }
            
            created_event = await self.database.create_event(event_data)
            operation_times["create"] = time.time() - create_start
            
            if not created_event:
                return {"test": "crud_performance", "success": False, "error": "Create failed"}
            
            event_id = created_event.id
            
            # READ
            read_start = time.time()
            retrieved_event = await self.database.get_event(event_id)
            operation_times["read"] = time.time() - read_start
            
            if not retrieved_event:
                return {"test": "crud_performance", "success": False, "error": "Read failed"}
            
            # UPDATE
            update_start = time.time()
            updated_event = await self.database.update_event(event_id, {"title": "Updated Event"})
            operation_times["update"] = time.time() - update_start
            
            if not updated_event:
                return {"test": "crud_performance", "success": False, "error": "Update failed"}
            
            # DELETE
            delete_start = time.time()
            deleted = await self.database.delete_event(event_id)
            operation_times["delete"] = time.time() - delete_start
            
            if not deleted:
                return {"test": "crud_performance", "success": False, "error": "Delete failed"}
            
            execution_time = time.time() - start_time
            avg_operation_time = sum(operation_times.values()) / len(operation_times)
            
            return {
                "test": "crud_performance",
                "success": True,
                "execution_time": execution_time,
                "avg_operation_time": avg_operation_time,
                "performance_target_met": avg_operation_time < 5.0,
                "operation_breakdown": operation_times,
                "all_under_5s": all(t < 5.0 for t in operation_times.values())
            }
            
        except Exception as e:
            return {
                "test": "crud_performance",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_bulk_operations(self) -> Dict[str, Any]:
        """Test bulk operations performance."""
        logger.info("Testing bulk operations...")
        start_time = time.time()
        
        try:
            # Create multiple events
            events_to_create = 50
            created_events = []
            
            bulk_create_start = time.time()
            for i in range(events_to_create):
                event_data = {
                    "calendar_id": "bulk-test",
                    "title": f"Bulk Event {i+1}",
                    "description": f"Bulk test event {i+1}",
                    "start_time": (datetime.now(timezone.utc) + timedelta(hours=i)).isoformat(),
                    "end_time": (datetime.now(timezone.utc) + timedelta(hours=i+1)).isoformat()
                }
                
                created_event = await self.database.create_event(event_data)
                if created_event:
                    created_events.append(created_event)
            
            bulk_create_time = time.time() - bulk_create_start
            
            # Test list query performance
            list_start = time.time()
            listed_events = await self.database.list_events(calendar_id="bulk-test", limit=100)
            list_time = time.time() - list_start
            
            execution_time = time.time() - start_time
            avg_create_time = bulk_create_time / events_to_create
            
            return {
                "test": "bulk_operations",
                "success": True,
                "execution_time": execution_time,
                "events_created": len(created_events),
                "events_listed": len(listed_events),
                "bulk_create_time": bulk_create_time,
                "avg_create_time": avg_create_time,
                "list_query_time": list_time,
                "performance_target_met": list_time < 5.0 and avg_create_time < 1.0,
                "throughput_events_per_second": events_to_create / bulk_create_time
            }
            
        except Exception as e:
            return {
                "test": "bulk_operations",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def test_concurrent_access(self) -> Dict[str, Any]:
        """Test concurrent database access."""
        logger.info("Testing concurrent access...")
        start_time = time.time()
        
        try:
            # Create concurrent tasks
            concurrent_count = 10
            tasks = []
            
            for i in range(concurrent_count):
                if i % 2 == 0:
                    # Create task
                    task = self._create_concurrent_event(f"concurrent_{i}")
                else:
                    # List task
                    task = self._list_concurrent_events()
                
                tasks.append(task)
            
            # Execute concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            execution_time = time.time() - start_time
            
            # Analyze results
            successful_ops = sum(1 for r in results if not isinstance(r, Exception) and r)
            failed_ops = concurrent_count - successful_ops
            
            return {
                "test": "concurrent_access",
                "success": failed_ops == 0,
                "execution_time": execution_time,
                "concurrent_operations": concurrent_count,
                "successful_operations": successful_ops,
                "failed_operations": failed_ops,
                "avg_operation_time": execution_time / concurrent_count,
                "performance_target_met": execution_time / concurrent_count < 5.0
            }
            
        except Exception as e:
            return {
                "test": "concurrent_access",
                "success": False,
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _create_concurrent_event(self, title: str):
        """Helper for concurrent event creation."""
        try:
            event_data = {
                "calendar_id": "concurrent-test",
                "title": title,
                "description": "Concurrent test",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "end_time": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            }
            return await self.database.create_event(event_data)
        except Exception:
            return None
    
    async def _list_concurrent_events(self):
        """Helper for concurrent event listing."""
        try:
            return await self.database.list_events(limit=10)
        except Exception:
            return []
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all core tests."""
        logger.info("="*60)
        logger.info("STARTING CORE PHASE 3.5 DATABASE TESTS")
        logger.info("="*60)
        
        overall_start_time = time.time()
        
        try:
            await self.setup()
            
            # Test sequence
            tests = [
                self.test_database_initialization,
                self.test_crud_performance,
                self.test_bulk_operations,
                self.test_concurrent_access
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
            report = self._generate_report(total_execution_time)
            
            return report
            
        finally:
            await self.teardown()
    
    def _generate_report(self, total_execution_time: float) -> Dict[str, Any]:
        """Generate test report."""
        logger.info("="*60)
        logger.info("CORE PHASE 3.5 DATABASE TEST REPORT")
        logger.info("="*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        performance_targets_met = sum(1 for r in self.test_results if r.get("performance_target_met", False))
        avg_execution_time = sum(r.get("execution_time", 0) for r in self.test_results) / total_tests if total_tests > 0 else 0
        
        overall_success = failed_tests == 0 and performance_targets_met >= total_tests * 0.75
        
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
                "phase_3_5_core_ready": overall_success
            },
            "test_results": self.test_results
        }
        
        # Log summary
        logger.info(f"EXECUTION SUMMARY:")
        logger.info(f"  Total Tests: {total_tests}")
        logger.info(f"  Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
        logger.info(f"  Failed: {failed_tests}")
        logger.info(f"  Performance Targets Met: {performance_targets_met}/{total_tests} ({performance_targets_met/total_tests*100:.1f}%)")
        logger.info(f"  Average Execution Time: {avg_execution_time:.3f}s")
        logger.info(f"  Overall Success: {'✅ YES' if overall_success else '❌ NO'}")
        logger.info(f"  Phase 3.5 Core Ready: {'✅ YES' if overall_success else '❌ NO'}")
        
        logger.info("="*60)
        
        return report


async def main():
    """Main execution."""
    test_suite = CorePhase35Test()
    
    try:
        report = await test_suite.run_all_tests()
        
        if report.get("execution_summary", {}).get("overall_success", False):
            logger.info("🎉 Phase 3.5 Core Database Test: ALL TESTS PASSED")
            logger.info("✅ Core database functionality validated!")
            sys.exit(0)
        else:
            logger.error("❌ Phase 3.5 Core Database Test: TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Test execution failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())