"""
Database backup functionality for Contacts Agent.

Provides weekly backup with 1 backup retention policy as specified in roadmap.
"""

import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ContactsBackup:
    """Manages database backups for contacts data."""
    
    def __init__(self, db_path: Optional[str] = None, backup_dir: Optional[str] = None):
        """
        Initialize the backup manager.
        
        Args:
            db_path: Path to the contacts database
            backup_dir: Directory to store backups
        """
        if db_path is None:
            # Use the same path pattern as ContactsDatabase
            app_support = Path.home() / "Library" / "Application Support" / "Kenny"
            self.db_path = str(app_support / "contacts.db")
        else:
            self.db_path = db_path
        
        if backup_dir is None:
            # Store backups in the same Kenny directory
            app_support = Path.home() / "Library" / "Application Support" / "Kenny"
            self.backup_dir = app_support / "backups"
        else:
            self.backup_dir = Path(backup_dir)
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup retention policy: keep 1 backup (weekly RPO as specified)
        self.max_backups = 1
    
    def create_backup(self) -> Optional[str]:
        """
        Create a backup of the contacts database.
        
        Returns:
            Path to the created backup file, or None if failed
        """
        try:
            if not os.path.exists(self.db_path):
                logger.warning(f"Database file not found: {self.db_path}")
                return None
            
            # Generate backup filename with timestamp
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_filename = f"contacts_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Perform backup using SQLite backup API for consistency
            self._backup_database(self.db_path, str(backup_path))
            
            logger.info(f"Created backup: {backup_path}")
            
            # Clean up old backups according to retention policy
            self._cleanup_old_backups()
            
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_backup(self, backup_path: str) -> bool:
        """
        Restore database from a backup file.
        
        Args:
            backup_path: Path to the backup file to restore
            
        Returns:
            True if restoration successful, False otherwise
        """
        try:
            if not os.path.exists(backup_path):
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create a temporary backup of current database
            temp_backup = f"{self.db_path}.pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(self.db_path, temp_backup)
            logger.info(f"Created pre-restore backup: {temp_backup}")
            
            # Restore from backup
            shutil.copy2(backup_path, self.db_path)
            
            # Verify the restored database
            if self._verify_database_integrity(self.db_path):
                logger.info(f"Successfully restored database from: {backup_path}")
                # Remove temporary backup on success
                os.remove(temp_backup)
                return True
            else:
                logger.error("Restored database failed integrity check, reverting")
                # Restore original database
                shutil.copy2(temp_backup, self.db_path)
                os.remove(temp_backup)
                return False
            
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            return False
    
    def list_backups(self) -> list:
        """
        List available backup files.
        
        Returns:
            List of backup file information dictionaries
        """
        backups = []
        try:
            backup_files = list(self.backup_dir.glob("contacts_backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            for backup_file in backup_files:
                stat = backup_file.stat()
                backups.append({
                    "path": str(backup_file),
                    "filename": backup_file.name,
                    "created": datetime.fromtimestamp(stat.st_ctime, timezone.utc).isoformat(),
                    "size_bytes": stat.st_size
                })
        
        except Exception as e:
            logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def _backup_database(self, source_path: str, backup_path: str):
        """
        Perform database backup using SQLite backup API.
        
        This method ensures consistent backups even if the database is in use.
        """
        # Connect to source database
        source_conn = sqlite3.connect(source_path)
        
        try:
            # Connect to backup database
            backup_conn = sqlite3.connect(backup_path)
            
            try:
                # Perform backup using SQLite backup API
                source_conn.backup(backup_conn)
                logger.debug(f"Database backup completed: {source_path} -> {backup_path}")
                
            finally:
                backup_conn.close()
        finally:
            source_conn.close()
    
    def _verify_database_integrity(self, db_path: str) -> bool:
        """
        Verify database integrity.
        
        Args:
            db_path: Path to database to verify
            
        Returns:
            True if database integrity is OK, False otherwise
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Run integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            # Result should be ('ok',) if database is intact
            return result and result[0].lower() == 'ok'
            
        except Exception as e:
            logger.error(f"Database integrity check failed: {e}")
            return False
    
    def _cleanup_old_backups(self):
        """Clean up old backups according to retention policy."""
        try:
            backup_files = list(self.backup_dir.glob("contacts_backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Remove backups beyond retention limit
            for backup_file in backup_files[self.max_backups:]:
                backup_file.unlink()
                logger.info(f"Removed old backup: {backup_file}")
        
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    def should_create_backup(self) -> bool:
        """
        Check if a new backup should be created based on weekly RPO policy.
        
        Returns:
            True if backup should be created, False otherwise
        """
        try:
            backups = self.list_backups()
            
            if not backups:
                # No backups exist, should create one
                return True
            
            # Check if the latest backup is older than 7 days (weekly RPO)
            latest_backup = backups[0]  # Already sorted by creation time, newest first
            latest_backup_time = datetime.fromisoformat(latest_backup['created'].replace('Z', '+00:00'))
            
            now = datetime.now(timezone.utc)
            days_since_backup = (now - latest_backup_time).days
            
            return days_since_backup >= 7
            
        except Exception as e:
            logger.error(f"Failed to check backup policy: {e}")
            # Default to creating backup on error
            return True
    
    def auto_backup(self) -> Optional[str]:
        """
        Create backup only if needed according to weekly RPO policy.
        
        Returns:
            Path to created backup file if backup was created, None otherwise
        """
        if self.should_create_backup():
            logger.info("Creating automatic weekly backup")
            return self.create_backup()
        else:
            logger.debug("Weekly backup not needed yet")
            return None