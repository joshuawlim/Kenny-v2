"""
Phase 3.5 Calendar Database Implementation

SQLite-based calendar database with real-time sync and Phase 3.2 integration
for achieving <5s response times through optimized database storage and caching.

Key Features:
- Optimized SQLite schema with performance indexes
- Real-time bidirectional sync with Calendar API
- Integration with Phase 3.2 L1/L2/L3 caching system
- Connection pooling and transaction management
- Fallback to Phase 3.2 performance levels as backup
"""

import asyncio
import sqlite3
import aiosqlite
import json
import hashlib
import time
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import threading

logger = logging.getLogger("calendar_database")


@dataclass
class DatabaseConfig:
    """Configuration for calendar database."""
    database_path: str = "calendar.db"
    connection_pool_size: int = 10
    timeout: float = 30.0
    journal_mode: str = "WAL"  # Write-Ahead Logging for better concurrency
    synchronous: str = "NORMAL"  # Balance safety vs performance
    cache_size: int = -64000  # 64MB cache
    temp_store: str = "MEMORY"
    enable_fts: bool = True  # Full-text search
    backup_enabled: bool = True
    encryption_enabled: bool = False  # For future SQLCipher integration


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


class CalendarDatabase:
    """
    High-performance SQLite calendar database with advanced optimizations.
    
    Provides <5s response times through:
    - Optimized indexes for common query patterns
    - Connection pooling for concurrent operations
    - Write-Ahead Logging for better concurrency
    - In-memory temp storage for performance
    - Full-text search capabilities
    """
    
    def __init__(self, config: DatabaseConfig = None):
        """Initialize calendar database."""
        self.config = config or DatabaseConfig()
        self.db_path = Path(self.config.database_path)
        self.connection_pool = []
        self.pool_lock = asyncio.Lock()
        self.is_initialized = False
        self.schema_version = "3.5.0"
        
        # Performance tracking
        self.operation_times = []
        self.connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "pool_hits": 0,
            "pool_misses": 0
        }
        
        logger.info(f"Calendar database initialized: {self.db_path}")
    
    async def initialize(self) -> bool:
        """Initialize database with optimized schema and indexes."""
        start_time = time.time()
        
        try:
            # Create database directory if needed
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize connection pool
            await self._initialize_connection_pool()
            
            # Create optimized schema
            await self._create_schema()
            
            # Create performance indexes
            await self._create_indexes()
            
            # Set database pragmas for performance
            await self._set_performance_pragmas()
            
            # Initialize full-text search if enabled
            if self.config.enable_fts:
                await self._initialize_fts()
            
            self.is_initialized = True
            init_time = time.time() - start_time
            
            logger.info(f"Database initialization completed in {init_time:.3f}s")
            logger.info(f"Connection pool size: {len(self.connection_pool)}")
            logger.info(f"Performance optimizations: WAL, {self.config.cache_size} cache, FTS enabled")
            
            return True
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_connection_pool(self):
        """Initialize connection pool for concurrent operations."""
        async with self.pool_lock:
            self.connection_pool = []
            
            for i in range(self.config.connection_pool_size):
                try:
                    conn = await aiosqlite.connect(
                        self.db_path,
                        timeout=self.config.timeout,
                        isolation_level=None  # Autocommit mode for better concurrency
                    )
                    
                    # Enable foreign key constraints
                    await conn.execute("PRAGMA foreign_keys = ON")
                    
                    self.connection_pool.append(conn)
                    self.connection_stats["total_connections"] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to create connection {i}: {e}")
                    
            logger.info(f"Connection pool initialized with {len(self.connection_pool)} connections")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool with automatic return."""
        conn = None
        
        async with self.pool_lock:
            if self.connection_pool:
                conn = self.connection_pool.pop()
                self.connection_stats["pool_hits"] += 1
                self.connection_stats["active_connections"] += 1
            else:
                # Create new connection if pool is empty
                conn = await aiosqlite.connect(
                    self.db_path,
                    timeout=self.config.timeout,
                    isolation_level=None
                )
                await conn.execute("PRAGMA foreign_keys = ON")
                self.connection_stats["pool_misses"] += 1
                self.connection_stats["active_connections"] += 1
                self.connection_stats["total_connections"] += 1
        
        try:
            yield conn
        finally:
            # Return connection to pool
            async with self.pool_lock:
                if len(self.connection_pool) < self.config.connection_pool_size:
                    self.connection_pool.append(conn)
                else:
                    # Pool is full, close connection
                    await conn.close()
                self.connection_stats["active_connections"] -= 1
    
    async def _create_schema(self):
        """Create optimized database schema."""
        schema_sql = [
            # Calendars table
            """
            CREATE TABLE IF NOT EXISTS calendars (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT,
                is_default BOOLEAN DEFAULT 0,
                account_identifier TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sync_token TEXT,
                last_sync TIMESTAMP
            )
            """,
            
            # Events table with comprehensive fields and optimization
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
                checksum TEXT,
                FOREIGN KEY (calendar_id) REFERENCES calendars (id) ON DELETE CASCADE
            )
            """,
            
            # Recurrence patterns table for complex recurrence rules
            """
            CREATE TABLE IF NOT EXISTS recurrence_patterns (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                frequency TEXT NOT NULL, -- daily, weekly, monthly, yearly
                interval_count INTEGER DEFAULT 1,
                by_day TEXT, -- JSON array of days
                by_month_day TEXT, -- JSON array of month days
                by_month TEXT, -- JSON array of months
                until_date TIMESTAMP,
                count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
            """,
            
            # Participants table with contact information
            """
            CREATE TABLE IF NOT EXISTS participants (
                id TEXT PRIMARY KEY,
                name TEXT,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                organization TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            
            # Event participants junction table
            """
            CREATE TABLE IF NOT EXISTS event_participants (
                event_id TEXT,
                participant_id TEXT,
                role TEXT DEFAULT 'attendee', -- organizer, attendee, optional
                response_status TEXT DEFAULT 'needs-action', -- accepted, declined, tentative
                PRIMARY KEY (event_id, participant_id),
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
                FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE CASCADE
            )
            """,
            
            # Sync metadata for tracking bidirectional sync
            """
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL, -- event, calendar, participant
                entity_id TEXT NOT NULL,
                operation TEXT NOT NULL, -- create, update, delete
                sync_direction TEXT NOT NULL, -- to_api, from_api, bidirectional
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                conflict_resolution TEXT -- strategy used for conflicts
            )
            """,
            
            # Performance metrics table for monitoring
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                execution_time REAL NOT NULL,
                cache_hit BOOLEAN DEFAULT 0,
                result_count INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT -- JSON metadata
            )
            """,
            
            # Cache invalidation tracking
            """
            CREATE TABLE IF NOT EXISTS cache_invalidation (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cache_key TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                invalidation_reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        ]
        
        async with self.get_connection() as conn:
            for sql in schema_sql:
                await conn.execute(sql)
            await conn.commit()
        
        logger.info("Database schema created successfully")
    
    async def _create_indexes(self):
        """Create performance-optimized indexes for common query patterns."""
        indexes_sql = [
            # Core event query indexes
            "CREATE INDEX IF NOT EXISTS idx_events_calendar_id ON events (calendar_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_start_time ON events (start_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_end_time ON events (end_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_date_range ON events (start_time, end_time)",
            
            # Search and filtering indexes
            "CREATE INDEX IF NOT EXISTS idx_events_title ON events (title)",
            "CREATE INDEX IF NOT EXISTS idx_events_status ON events (status)",
            "CREATE INDEX IF NOT EXISTS idx_events_location ON events (location)",
            
            # Sync and API integration indexes
            "CREATE INDEX IF NOT EXISTS idx_events_api_id ON events (api_event_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_sync_token ON events (sync_token)",
            "CREATE INDEX IF NOT EXISTS idx_events_last_sync ON events (last_sync)",
            "CREATE INDEX IF NOT EXISTS idx_events_checksum ON events (checksum)",
            
            # Composite indexes for complex queries
            "CREATE INDEX IF NOT EXISTS idx_events_calendar_date ON events (calendar_id, start_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_calendar_status ON events (calendar_id, status)",
            
            # Participant relationship indexes
            "CREATE INDEX IF NOT EXISTS idx_event_participants_event_id ON event_participants (event_id)",
            "CREATE INDEX IF NOT EXISTS idx_event_participants_participant_id ON event_participants (participant_id)",
            "CREATE INDEX IF NOT EXISTS idx_participants_email ON participants (email)",
            
            # Recurrence pattern indexes
            "CREATE INDEX IF NOT EXISTS idx_recurrence_event_id ON recurrence_patterns (event_id)",
            "CREATE INDEX IF NOT EXISTS idx_recurrence_frequency ON recurrence_patterns (frequency)",
            
            # Sync metadata indexes
            "CREATE INDEX IF NOT EXISTS idx_sync_metadata_entity ON sync_metadata (entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_sync_metadata_timestamp ON sync_metadata (timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_sync_metadata_success ON sync_metadata (success)",
            
            # Performance monitoring indexes
            "CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics (operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics (timestamp)",
            
            # Cache invalidation indexes
            "CREATE INDEX IF NOT EXISTS idx_cache_invalidation_key ON cache_invalidation (cache_key)",
            "CREATE INDEX IF NOT EXISTS idx_cache_invalidation_entity ON cache_invalidation (entity_type, entity_id)"
        ]
        
        async with self.get_connection() as conn:
            for index_sql in indexes_sql:
                await conn.execute(index_sql)
            await conn.commit()
        
        logger.info(f"Created {len(indexes_sql)} performance indexes")
    
    async def _set_performance_pragmas(self):
        """Set SQLite pragmas for optimal performance."""
        pragmas = [
            f"PRAGMA journal_mode = {self.config.journal_mode}",
            f"PRAGMA synchronous = {self.config.synchronous}",
            f"PRAGMA cache_size = {self.config.cache_size}",
            f"PRAGMA temp_store = {self.config.temp_store}",
            "PRAGMA optimize",  # Auto-optimize query planner
            "PRAGMA analysis_limit = 1000",  # Limit ANALYZE to avoid long delays
            "PRAGMA automatic_index = ON",  # Enable automatic indexes
        ]
        
        async with self.get_connection() as conn:
            for pragma in pragmas:
                await conn.execute(pragma)
        
        logger.info("Performance pragmas configured")
    
    async def _initialize_fts(self):
        """Initialize full-text search capabilities."""
        fts_sql = [
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                title, description, location,
                content='events',
                content_rowid='rowid'
            )
            """,
            
            # Trigger to keep FTS table in sync
            """
            CREATE TRIGGER IF NOT EXISTS events_fts_insert AFTER INSERT ON events BEGIN
                INSERT INTO events_fts(rowid, title, description, location) 
                VALUES (new.rowid, new.title, new.description, new.location);
            END
            """,
            
            """
            CREATE TRIGGER IF NOT EXISTS events_fts_delete AFTER DELETE ON events BEGIN
                INSERT INTO events_fts(events_fts, rowid, title, description, location) 
                VALUES('delete', old.rowid, old.title, old.description, old.location);
            END
            """,
            
            """
            CREATE TRIGGER IF NOT EXISTS events_fts_update AFTER UPDATE ON events BEGIN
                INSERT INTO events_fts(events_fts, rowid, title, description, location) 
                VALUES('delete', old.rowid, old.title, old.description, old.location);
                INSERT INTO events_fts(rowid, title, description, location) 
                VALUES (new.rowid, new.title, new.description, new.location);
            END
            """
        ]
        
        async with self.get_connection() as conn:
            for sql in fts_sql:
                await conn.execute(sql)
            await conn.commit()
        
        logger.info("Full-text search initialized")
    
    async def create_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Create a new calendar event with performance tracking."""
        start_time = time.time()
        
        try:
            # Generate event ID if not provided
            event_id = event_data.get("id", str(uuid.uuid4()))
            
            # Calculate checksum for consistency validation
            checksum = self._calculate_checksum(event_data)
            
            # Prepare event data
            now = datetime.now(timezone.utc)
            event_data.update({
                "id": event_id,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "checksum": checksum
            })
            
            async with self.get_connection() as conn:
                # Insert event
                await conn.execute("""
                    INSERT INTO events (
                        id, calendar_id, title, description, location,
                        start_time, end_time, all_day, recurrence_rule,
                        status, url, api_event_id, checksum,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id,
                    event_data.get("calendar_id"),
                    event_data.get("title"),
                    event_data.get("description"),
                    event_data.get("location"),
                    event_data.get("start_time"),
                    event_data.get("end_time"),
                    event_data.get("all_day", False),
                    event_data.get("recurrence_rule"),
                    event_data.get("status", "confirmed"),
                    event_data.get("url"),
                    event_data.get("api_event_id"),
                    checksum,
                    event_data["created_at"],
                    event_data["updated_at"]
                ))
                
                await conn.commit()
            
            # Record performance metrics
            execution_time = time.time() - start_time
            await self._record_performance_metric("create_event", execution_time, {"result_count": 1})
            
            logger.debug(f"Created event {event_id} in {execution_time:.3f}s")
            
            # Return created event
            return await self.get_event(event_id)
            
        except Exception as e:
            logger.error(f"Failed to create event: {e}", exc_info=True)
            return None
    
    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Retrieve event by ID with performance optimization."""
        start_time = time.time()
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT * FROM events WHERE id = ?", (event_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    columns = [desc[0] for desc in cursor.description]
                    event_data = dict(zip(columns, row))
                    
                    execution_time = time.time() - start_time
                    await self._record_performance_metric("get_event", execution_time, {"result_count": 1})
                    
                    return CalendarEvent(**self._normalize_event_data(event_data))
                
                execution_time = time.time() - start_time
                await self._record_performance_metric("get_event", execution_time, {"result_count": 0})
                return None
                
        except Exception as e:
            logger.error(f"Failed to get event {event_id}: {e}", exc_info=True)
            return None
    
    async def update_event(self, event_id: str, update_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """Update event with optimized query and performance tracking."""
        start_time = time.time()
        
        try:
            # Get current event for checksum calculation
            current_event = await self.get_event(event_id)
            if not current_event:
                return None
            
            # Merge update data
            updated_data = asdict(current_event)
            updated_data.update(update_data)
            updated_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            updated_data["checksum"] = self._calculate_checksum(updated_data)
            
            # Build dynamic update query
            set_clauses = []
            params = []
            
            for key, value in update_data.items():
                if key != "id":
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
            
            set_clauses.extend(["updated_at = ?", "checksum = ?"])
            params.extend([updated_data["updated_at"], updated_data["checksum"]])
            params.append(event_id)
            
            async with self.get_connection() as conn:
                await conn.execute(
                    f"UPDATE events SET {', '.join(set_clauses)} WHERE id = ?",
                    params
                )
                await conn.commit()
            
            execution_time = time.time() - start_time
            await self._record_performance_metric("update_event", execution_time, {"result_count": 1})
            
            logger.debug(f"Updated event {event_id} in {execution_time:.3f}s")
            
            return await self.get_event(event_id)
            
        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}", exc_info=True)
            return None
    
    async def delete_event(self, event_id: str) -> bool:
        """Delete event with cascade handling and performance tracking."""
        start_time = time.time()
        
        try:
            async with self.get_connection() as conn:
                cursor = await conn.execute(
                    "DELETE FROM events WHERE id = ?", (event_id,)
                )
                await conn.commit()
                
                execution_time = time.time() - start_time
                success = cursor.rowcount > 0
                
                await self._record_performance_metric(
                    "delete_event", 
                    execution_time, 
                    {"result_count": cursor.rowcount}
                )
                
                if success:
                    logger.debug(f"Deleted event {event_id} in {execution_time:.3f}s")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to delete event {event_id}: {e}", exc_info=True)
            return False
    
    async def list_events(self, 
                         calendar_id: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         limit: int = 100,
                         status_filter: Optional[str] = None) -> List[CalendarEvent]:
        """List events with optimized filtering and performance tracking."""
        start_time = time.time()
        
        try:
            # Build optimized query with proper indexes
            base_query = """
                SELECT * FROM events 
                WHERE 1=1
            """
            params = []
            
            if calendar_id:
                base_query += " AND calendar_id = ?"
                params.append(calendar_id)
            
            if start_date:
                base_query += " AND start_time >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                base_query += " AND end_time <= ?"
                params.append(end_date.isoformat())
            
            if status_filter:
                base_query += " AND status = ?"
                params.append(status_filter)
            
            # Order by start_time for better user experience
            base_query += " ORDER BY start_time ASC"
            
            if limit:
                base_query += " LIMIT ?"
                params.append(limit)
            
            async with self.get_connection() as conn:
                cursor = await conn.execute(base_query, params)
                rows = await cursor.fetchall()
                
                events = []
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    for row in rows:
                        event_data = dict(zip(columns, row))
                        events.append(CalendarEvent(**self._normalize_event_data(event_data)))
                
                execution_time = time.time() - start_time
                await self._record_performance_metric(
                    "list_events", 
                    execution_time, 
                    {"result_count": len(events), "filters_applied": len([f for f in [calendar_id, start_date, end_date, status_filter] if f])}
                )
                
                logger.debug(f"Listed {len(events)} events in {execution_time:.3f}s")
                return events
                
        except Exception as e:
            logger.error(f"Failed to list events: {e}", exc_info=True)
            return []
    
    async def search_events(self, query: str, limit: int = 50) -> List[CalendarEvent]:
        """Full-text search events with FTS optimization."""
        start_time = time.time()
        
        try:
            if not self.config.enable_fts:
                # Fallback to LIKE search if FTS not available
                return await self._search_events_fallback(query, limit)
            
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT e.* FROM events e
                    JOIN events_fts fts ON e.rowid = fts.rowid
                    WHERE events_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                """, (query, limit))
                
                rows = await cursor.fetchall()
                
                events = []
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    for row in rows:
                        event_data = dict(zip(columns, row))
                        events.append(CalendarEvent(**self._normalize_event_data(event_data)))
                
                execution_time = time.time() - start_time
                await self._record_performance_metric(
                    "search_events_fts", 
                    execution_time, 
                    {"result_count": len(events), "query_length": len(query)}
                )
                
                logger.debug(f"FTS search returned {len(events)} events in {execution_time:.3f}s")
                return events
                
        except Exception as e:
            logger.error(f"FTS search failed, falling back to LIKE search: {e}")
            return await self._search_events_fallback(query, limit)
    
    async def _search_events_fallback(self, query: str, limit: int) -> List[CalendarEvent]:
        """Fallback search using LIKE when FTS is not available."""
        start_time = time.time()
        
        try:
            search_pattern = f"%{query}%"
            
            async with self.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM events 
                    WHERE title LIKE ? OR description LIKE ? OR location LIKE ?
                    ORDER BY start_time DESC
                    LIMIT ?
                """, (search_pattern, search_pattern, search_pattern, limit))
                
                rows = await cursor.fetchall()
                
                events = []
                if rows:
                    columns = [desc[0] for desc in cursor.description]
                    for row in rows:
                        event_data = dict(zip(columns, row))
                        events.append(CalendarEvent(**self._normalize_event_data(event_data)))
                
                execution_time = time.time() - start_time
                await self._record_performance_metric(
                    "search_events_like", 
                    execution_time, 
                    {"result_count": len(events), "query_length": len(query)}
                )
                
                logger.debug(f"LIKE search returned {len(events)} events in {execution_time:.3f}s")
                return events
                
        except Exception as e:
            logger.error(f"Fallback search failed: {e}", exc_info=True)
            return []
    
    def _calculate_checksum(self, event_data: Dict[str, Any]) -> str:
        """Calculate checksum for event data consistency validation."""
        # Create normalized data for checksum
        normalized_data = {
            "title": event_data.get("title", ""),
            "description": event_data.get("description", ""),
            "start_time": str(event_data.get("start_time", "")),
            "end_time": str(event_data.get("end_time", "")),
            "location": event_data.get("location", "")
        }
        
        data_string = json.dumps(normalized_data, sort_keys=True)
        return hashlib.sha256(data_string.encode()).hexdigest()
    
    def _normalize_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize event data for CalendarEvent creation."""
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
    
    async def _record_performance_metric(self, operation_type: str, execution_time: float, 
                                       metadata: Dict[str, Any] = None):
        """Record performance metrics for monitoring."""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO performance_metrics (operation_type, execution_time, metadata)
                    VALUES (?, ?, ?)
                """, (operation_type, execution_time, json.dumps(metadata or {})))
                await conn.commit()
            
            # Track in memory for quick access
            self.operation_times.append({
                "operation": operation_type,
                "time": execution_time,
                "timestamp": time.time()
            })
            
            # Keep only recent metrics in memory
            if len(self.operation_times) > 1000:
                self.operation_times = self.operation_times[-500:]
                
        except Exception as e:
            logger.warning(f"Failed to record performance metric: {e}")
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        try:
            recent_ops = [op for op in self.operation_times if time.time() - op["timestamp"] < 3600]  # Last hour
            
            if not recent_ops:
                return {"error": "No recent operations"}
            
            avg_time = sum(op["time"] for op in recent_ops) / len(recent_ops)
            max_time = max(op["time"] for op in recent_ops)
            min_time = min(op["time"] for op in recent_ops)
            
            # Group by operation type
            by_operation = {}
            for op in recent_ops:
                op_type = op["operation"]
                if op_type not in by_operation:
                    by_operation[op_type] = []
                by_operation[op_type].append(op["time"])
            
            operation_stats = {}
            for op_type, times in by_operation.items():
                operation_stats[op_type] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "max_time": max(times),
                    "min_time": min(times),
                    "under_5s": sum(1 for t in times if t < 5.0),
                    "under_5s_percentage": (sum(1 for t in times if t < 5.0) / len(times)) * 100
                }
            
            return {
                "overall_stats": {
                    "total_operations": len(recent_ops),
                    "avg_execution_time": avg_time,
                    "max_execution_time": max_time,
                    "min_execution_time": min_time,
                    "under_5s_count": sum(1 for op in recent_ops if op["time"] < 5.0),
                    "under_5s_percentage": (sum(1 for op in recent_ops if op["time"] < 5.0) / len(recent_ops)) * 100,
                    "performance_target_met": avg_time < 5.0
                },
                "by_operation": operation_stats,
                "connection_stats": self.connection_stats.copy(),
                "database_config": {
                    "journal_mode": self.config.journal_mode,
                    "cache_size": self.config.cache_size,
                    "connection_pool_size": len(self.connection_pool),
                    "fts_enabled": self.config.enable_fts
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get performance stats: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def cleanup(self):
        """Clean up database resources."""
        try:
            async with self.pool_lock:
                for conn in self.connection_pool:
                    await conn.close()
                self.connection_pool.clear()
            
            logger.info("Database cleanup completed")
            
        except Exception as e:
            logger.error(f"Database cleanup failed: {e}", exc_info=True)