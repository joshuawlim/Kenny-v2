"""
Database Migration Utilities for Phase 3.5 Calendar Database

Provides comprehensive database initialization, migration, and maintenance utilities
for seamless deployment and updates of the Phase 3.5 calendar database system.

Features:
- Version-aware migration system
- Data validation and integrity checks
- Backup and rollback capabilities
- Performance optimization utilities
- Schema evolution support
"""

import asyncio
import sqlite3
import aiosqlite
import json
import time
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("database_migration")


@dataclass
class MigrationResult:
    """Result of a database migration operation."""
    success: bool
    migration_id: str
    execution_time: float
    messages: List[str]
    error: Optional[str] = None
    rollback_available: bool = False


class DatabaseMigrationManager:
    """
    Comprehensive database migration and maintenance manager.
    
    Handles:
    - Schema creation and evolution
    - Data migration between versions
    - Performance optimization
    - Backup and recovery
    - Integrity validation
    """
    
    def __init__(self, database_path: str):
        """Initialize migration manager."""
        self.database_path = Path(database_path)
        self.backup_dir = self.database_path.parent / "backups"
        self.migration_history = []
        
        # Schema versions and migrations
        self.schema_version = "3.5.0"
        self.minimum_version = "1.0.0"
        
        # Migration definitions
        self.migrations = {
            "1.0.0": self._migration_1_0_0,
            "2.0.0": self._migration_2_0_0,
            "3.0.0": self._migration_3_0_0,
            "3.5.0": self._migration_3_5_0
        }
        
        logger.info(f"Database migration manager initialized for {self.database_path}")
    
    async def initialize_database(self, force_recreate: bool = False) -> MigrationResult:
        """
        Initialize database with complete schema and optimizations.
        
        Args:
            force_recreate: If True, drop existing database and recreate
            
        Returns:
            MigrationResult with operation details
        """
        start_time = time.time()
        messages = []
        
        try:
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if database exists
            db_exists = self.database_path.exists()
            
            if force_recreate and db_exists:
                await self._backup_database()
                self.database_path.unlink()
                messages.append("Existing database backed up and removed")
                db_exists = False
            
            if not db_exists:
                # Create new database with latest schema
                messages.append("Creating new database with Phase 3.5 schema")
                result = await self._create_fresh_database()
                messages.extend(result.messages)
                
                if not result.success:
                    return result
            else:
                # Migrate existing database
                messages.append("Migrating existing database to Phase 3.5")
                result = await self._migrate_to_latest()
                messages.extend(result.messages)
                
                if not result.success:
                    return result
            
            # Validate database integrity
            validation_result = await self._validate_database_integrity()
            messages.extend(validation_result.messages)
            
            if not validation_result.success:
                return validation_result
            
            # Optimize database performance
            optimization_result = await self._optimize_database()
            messages.extend(optimization_result.messages)
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="database_initialization",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Database initialization failed: {e}", exc_info=True)
            
            return MigrationResult(
                success=False,
                migration_id="database_initialization",
                execution_time=execution_time,
                messages=messages,
                error=str(e)
            )
    
    async def _create_fresh_database(self) -> MigrationResult:
        """Create a new database with the latest schema."""
        start_time = time.time()
        messages = []
        
        try:
            # Create database file
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Connect and create schema
            async with aiosqlite.connect(self.database_path) as conn:
                # Enable foreign keys
                await conn.execute("PRAGMA foreign_keys = ON")
                
                # Create all tables for current version
                schema_sql = await self._get_schema_sql(self.schema_version)
                
                for sql_statement in schema_sql:
                    await conn.execute(sql_statement)
                    messages.append(f"Created: {sql_statement.split()[2]}")  # Extract table name
                
                # Create indexes
                index_sql = await self._get_index_sql()
                for sql_statement in index_sql:
                    await conn.execute(sql_statement)
                
                messages.append(f"Created {len(index_sql)} performance indexes")
                
                # Set performance pragmas
                pragma_sql = await self._get_pragma_sql()
                for pragma in pragma_sql:
                    await conn.execute(pragma)
                
                messages.append("Applied performance optimizations")
                
                # Create metadata table and insert version
                await self._create_metadata_table(conn)
                await self._set_schema_version(conn, self.schema_version)
                
                await conn.commit()
                messages.append(f"Database created with schema version {self.schema_version}")
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="create_fresh_database",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Fresh database creation failed: {e}", exc_info=True)
            
            return MigrationResult(
                success=False,
                migration_id="create_fresh_database",
                execution_time=execution_time,
                messages=messages,
                error=str(e)
            )
    
    async def _migrate_to_latest(self) -> MigrationResult:
        """Migrate existing database to the latest schema version."""
        start_time = time.time()
        messages = []
        
        try:
            # Get current version
            current_version = await self._get_current_version()
            messages.append(f"Current database version: {current_version}")
            
            if current_version == self.schema_version:
                messages.append("Database already at latest version")
                return MigrationResult(
                    success=True,
                    migration_id="migrate_to_latest",
                    execution_time=time.time() - start_time,
                    messages=messages
                )
            
            # Create backup before migration
            backup_result = await self._backup_database()
            if backup_result.success:
                messages.append(f"Created backup: {backup_result.messages[0]}")
            
            # Apply migrations in sequence
            migration_path = self._get_migration_path(current_version, self.schema_version)
            
            for version in migration_path:
                if version in self.migrations:
                    messages.append(f"Applying migration to {version}")
                    
                    migration_result = await self.migrations[version]()
                    if not migration_result.success:
                        messages.extend(migration_result.messages)
                        return migration_result
                    
                    messages.extend(migration_result.messages)
                    
                    # Update version in database
                    async with aiosqlite.connect(self.database_path) as conn:
                        await self._set_schema_version(conn, version)
                        await conn.commit()
            
            execution_time = time.time() - start_time
            messages.append(f"Migration completed successfully in {execution_time:.3f}s")
            
            return MigrationResult(
                success=True,
                migration_id="migrate_to_latest",
                execution_time=execution_time,
                messages=messages,
                rollback_available=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Database migration failed: {e}", exc_info=True)
            
            return MigrationResult(
                success=False,
                migration_id="migrate_to_latest",
                execution_time=execution_time,
                messages=messages,
                error=str(e),
                rollback_available=True
            )
    
    async def _get_current_version(self) -> str:
        """Get the current schema version of the database."""
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Check if metadata table exists
                cursor = await conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='_migration_metadata'
                """)
                
                if not await cursor.fetchone():
                    # No metadata table, assume version 1.0.0
                    return "1.0.0"
                
                # Get version from metadata table
                cursor = await conn.execute(
                    "SELECT value FROM _migration_metadata WHERE key = 'schema_version'"
                )
                result = await cursor.fetchone()
                
                return result[0] if result else "1.0.0"
                
        except Exception as e:
            logger.error(f"Failed to get current version: {e}")
            return "1.0.0"
    
    def _get_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """Get the migration path from one version to another."""
        all_versions = sorted(self.migrations.keys(), key=lambda v: [int(x) for x in v.split('.')])
        
        start_idx = all_versions.index(from_version) if from_version in all_versions else 0
        end_idx = all_versions.index(to_version)
        
        return all_versions[start_idx + 1:end_idx + 1]
    
    async def _create_metadata_table(self, conn: aiosqlite.Connection):
        """Create migration metadata table."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS _migration_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    async def _set_schema_version(self, conn: aiosqlite.Connection, version: str):
        """Set the schema version in metadata table."""
        await conn.execute("""
            INSERT OR REPLACE INTO _migration_metadata (key, value, updated_at)
            VALUES ('schema_version', ?, CURRENT_TIMESTAMP)
        """, (version,))
    
    async def _backup_database(self) -> MigrationResult:
        """Create a backup of the current database."""
        start_time = time.time()
        
        try:
            if not self.database_path.exists():
                return MigrationResult(
                    success=False,
                    migration_id="backup_database",
                    execution_time=0,
                    messages=[],
                    error="Database file does not exist"
                )
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.database_path.stem}_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_name
            
            # Create backup directory
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy database file
            shutil.copy2(self.database_path, backup_path)
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="backup_database",
                execution_time=execution_time,
                messages=[f"Backup created: {backup_path}"]
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Database backup failed: {e}", exc_info=True)
            
            return MigrationResult(
                success=False,
                migration_id="backup_database",
                execution_time=execution_time,
                messages=[],
                error=str(e)
            )
    
    async def _validate_database_integrity(self) -> MigrationResult:
        """Validate database integrity and structure."""
        start_time = time.time()
        messages = []
        
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Check database integrity
                cursor = await conn.execute("PRAGMA integrity_check")
                integrity_result = await cursor.fetchone()
                
                if integrity_result[0] != "ok":
                    return MigrationResult(
                        success=False,
                        migration_id="validate_integrity",
                        execution_time=time.time() - start_time,
                        messages=messages,
                        error=f"Database integrity check failed: {integrity_result[0]}"
                    )
                
                messages.append("Database integrity check: PASSED")
                
                # Validate required tables exist
                required_tables = [
                    "calendars", "events", "recurrence_patterns", 
                    "participants", "event_participants", "sync_metadata",
                    "performance_metrics", "cache_invalidation"
                ]
                
                for table in required_tables:
                    cursor = await conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                    
                    if not await cursor.fetchone():
                        return MigrationResult(
                            success=False,
                            migration_id="validate_integrity",
                            execution_time=time.time() - start_time,
                            messages=messages,
                            error=f"Required table '{table}' is missing"
                        )
                
                messages.append(f"All {len(required_tables)} required tables present")
                
                # Validate indexes exist
                cursor = await conn.execute("""
                    SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'
                """)
                index_count = (await cursor.fetchone())[0]
                
                if index_count < 10:  # Expect at least 10 performance indexes
                    messages.append(f"Warning: Only {index_count} indexes found, may impact performance")
                else:
                    messages.append(f"Performance indexes validated: {index_count} indexes")
                
                # Check foreign key constraints
                cursor = await conn.execute("PRAGMA foreign_key_check")
                fk_violations = await cursor.fetchall()
                
                if fk_violations:
                    return MigrationResult(
                        success=False,
                        migration_id="validate_integrity",
                        execution_time=time.time() - start_time,
                        messages=messages,
                        error=f"Foreign key violations found: {len(fk_violations)}"
                    )
                
                messages.append("Foreign key constraints validated")
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="validate_integrity",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Database validation failed: {e}", exc_info=True)
            
            return MigrationResult(
                success=False,
                migration_id="validate_integrity",
                execution_time=execution_time,
                messages=messages,
                error=str(e)
            )
    
    async def _optimize_database(self) -> MigrationResult:
        """Optimize database for performance."""
        start_time = time.time()
        messages = []
        
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Analyze database for query optimizer
                await conn.execute("ANALYZE")
                messages.append("Database analysis completed for query optimizer")
                
                # Update table statistics
                await conn.execute("PRAGMA optimize")
                messages.append("Query optimizer statistics updated")
                
                # Vacuum database to reclaim space and optimize
                await conn.execute("VACUUM")
                messages.append("Database vacuumed and optimized")
                
                # Get database size
                db_size = self.database_path.stat().st_size
                messages.append(f"Database size after optimization: {db_size / 1024:.1f} KB")
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="optimize_database",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Database optimization failed: {e}", exc_info=True)
            
            return MigrationResult(
                success=False,
                migration_id="optimize_database",
                execution_time=execution_time,
                messages=messages,
                error=str(e)
            )
    
    # Migration implementations for different versions
    
    async def _migration_1_0_0(self) -> MigrationResult:
        """Migration to version 1.0.0 (baseline)."""
        return MigrationResult(
            success=True,
            migration_id="migration_1_0_0",
            execution_time=0.0,
            messages=["Baseline version 1.0.0"]
        )
    
    async def _migration_2_0_0(self) -> MigrationResult:
        """Migration to version 2.0.0."""
        start_time = time.time()
        messages = []
        
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Add new columns or tables for version 2.0.0
                await conn.execute("""
                    ALTER TABLE events ADD COLUMN sync_token TEXT
                """)
                messages.append("Added sync_token column to events table")
                
                await conn.commit()
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="migration_2_0_0",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                # Column already exists, migration already applied
                return MigrationResult(
                    success=True,
                    migration_id="migration_2_0_0",
                    execution_time=time.time() - start_time,
                    messages=["Migration 2.0.0 already applied"]
                )
            
            return MigrationResult(
                success=False,
                migration_id="migration_2_0_0",
                execution_time=time.time() - start_time,
                messages=messages,
                error=str(e)
            )
    
    async def _migration_3_0_0(self) -> MigrationResult:
        """Migration to version 3.0.0."""
        start_time = time.time()
        messages = []
        
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Add performance metrics table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        operation_type TEXT NOT NULL,
                        execution_time REAL NOT NULL,
                        cache_hit BOOLEAN DEFAULT 0,
                        result_count INTEGER DEFAULT 0,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                """)
                messages.append("Created performance_metrics table")
                
                await conn.commit()
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="migration_3_0_0",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                migration_id="migration_3_0_0",
                execution_time=time.time() - start_time,
                messages=messages,
                error=str(e)
            )
    
    async def _migration_3_5_0(self) -> MigrationResult:
        """Migration to version 3.5.0 (Phase 3.5 features)."""
        start_time = time.time()
        messages = []
        
        try:
            async with aiosqlite.connect(self.database_path) as conn:
                # Add cache invalidation table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS cache_invalidation (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        cache_key TEXT NOT NULL,
                        entity_type TEXT NOT NULL,
                        entity_id TEXT,
                        invalidation_reason TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                messages.append("Created cache_invalidation table")
                
                # Add checksum column to events for consistency validation
                try:
                    await conn.execute("ALTER TABLE events ADD COLUMN checksum TEXT")
                    messages.append("Added checksum column to events table")
                except:
                    messages.append("Checksum column already exists")
                
                # Create FTS table for full-text search
                await conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
                        title, description, location,
                        content='events',
                        content_rowid='rowid'
                    )
                """)
                messages.append("Created full-text search table")
                
                # Create FTS triggers
                fts_triggers = [
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
                
                for trigger_sql in fts_triggers:
                    await conn.execute(trigger_sql)
                
                messages.append("Created FTS synchronization triggers")
                
                await conn.commit()
            
            execution_time = time.time() - start_time
            
            return MigrationResult(
                success=True,
                migration_id="migration_3_5_0",
                execution_time=execution_time,
                messages=messages
            )
            
        except Exception as e:
            return MigrationResult(
                success=False,
                migration_id="migration_3_5_0",
                execution_time=time.time() - start_time,
                messages=messages,
                error=str(e)
            )
    
    async def _get_schema_sql(self, version: str) -> List[str]:
        """Get schema SQL statements for a specific version."""
        # Return the latest schema (from calendar_database.py)
        return [
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
            """
            CREATE TABLE IF NOT EXISTS recurrence_patterns (
                id TEXT PRIMARY KEY,
                event_id TEXT NOT NULL,
                frequency TEXT NOT NULL,
                interval_count INTEGER DEFAULT 1,
                by_day TEXT,
                by_month_day TEXT,
                by_month TEXT,
                until_date TIMESTAMP,
                count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE
            )
            """,
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
            """
            CREATE TABLE IF NOT EXISTS event_participants (
                event_id TEXT,
                participant_id TEXT,
                role TEXT DEFAULT 'attendee',
                response_status TEXT DEFAULT 'needs-action',
                PRIMARY KEY (event_id, participant_id),
                FOREIGN KEY (event_id) REFERENCES events (id) ON DELETE CASCADE,
                FOREIGN KEY (participant_id) REFERENCES participants (id) ON DELETE CASCADE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sync_metadata (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                sync_direction TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                conflict_resolution TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_type TEXT NOT NULL,
                execution_time REAL NOT NULL,
                cache_hit BOOLEAN DEFAULT 0,
                result_count INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT
            )
            """,
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
    
    async def _get_index_sql(self) -> List[str]:
        """Get index creation SQL statements."""
        return [
            "CREATE INDEX IF NOT EXISTS idx_events_calendar_id ON events (calendar_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_start_time ON events (start_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_end_time ON events (end_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_date_range ON events (start_time, end_time)",
            "CREATE INDEX IF NOT EXISTS idx_events_title ON events (title)",
            "CREATE INDEX IF NOT EXISTS idx_events_status ON events (status)",
            "CREATE INDEX IF NOT EXISTS idx_events_api_id ON events (api_event_id)",
            "CREATE INDEX IF NOT EXISTS idx_events_checksum ON events (checksum)",
            "CREATE INDEX IF NOT EXISTS idx_event_participants_event_id ON event_participants (event_id)",
            "CREATE INDEX IF NOT EXISTS idx_participants_email ON participants (email)",
            "CREATE INDEX IF NOT EXISTS idx_sync_metadata_entity ON sync_metadata (entity_type, entity_id)",
            "CREATE INDEX IF NOT EXISTS idx_performance_operation ON performance_metrics (operation_type)",
            "CREATE INDEX IF NOT EXISTS idx_cache_invalidation_key ON cache_invalidation (cache_key)"
        ]
    
    async def _get_pragma_sql(self) -> List[str]:
        """Get pragma statements for performance optimization."""
        return [
            "PRAGMA journal_mode = WAL",
            "PRAGMA synchronous = NORMAL",
            "PRAGMA cache_size = -64000",
            "PRAGMA temp_store = MEMORY",
            "PRAGMA optimize"
        ]
    
    async def get_migration_status(self) -> Dict[str, Any]:
        """Get comprehensive migration and database status."""
        try:
            current_version = await self._get_current_version()
            
            status = {
                "current_version": current_version,
                "latest_version": self.schema_version,
                "migration_needed": current_version != self.schema_version,
                "database_exists": self.database_path.exists(),
                "backup_directory": str(self.backup_dir),
                "available_migrations": list(self.migrations.keys()),
                "migration_history": self.migration_history
            }
            
            if self.database_path.exists():
                db_size = self.database_path.stat().st_size
                status["database_size"] = db_size
                status["database_size_mb"] = round(db_size / (1024 * 1024), 2)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e)}