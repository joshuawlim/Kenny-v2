"""
SQLite-based mail message cache for high-performance Apple Mail integration.

This module provides a local database layer to cache mail messages, enabling
sub-second queries instead of 60+ second JXA calls to Apple Mail.
"""

import sqlite3
import json
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MailCache:
    """SQLite-based cache for mail messages with incremental sync support."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Initialize mail cache with SQLite database."""
        if db_path is None:
            # Store in user's application support directory
            cache_dir = Path.home() / "Library" / "Application Support" / "Kenny"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(cache_dir / "mail_cache.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    mailbox TEXT NOT NULL,
                    subject TEXT,
                    sender TEXT,
                    recipients TEXT,  -- JSON array
                    date_received TEXT NOT NULL,  -- ISO timestamp
                    content TEXT,
                    snippet TEXT,
                    last_synced TEXT NOT NULL,  -- ISO timestamp
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_status (
                    mailbox TEXT PRIMARY KEY,
                    last_sync_time TEXT NOT NULL,  -- ISO timestamp
                    last_sync_success INTEGER DEFAULT 1,
                    message_count INTEGER DEFAULT 0,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_mailbox_date 
                ON messages(mailbox, date_received DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_date 
                ON messages(date_received DESC)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_sender 
                ON messages(sender)
            """)
            
            conn.commit()
            logger.info(f"Mail cache database initialized: {self.db_path}")
    
    def get_last_sync_time(self, mailbox: str) -> Optional[datetime]:
        """Get the last successful sync time for a mailbox."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT last_sync_time FROM sync_status WHERE mailbox = ? AND last_sync_success = 1",
                (mailbox,)
            )
            row = cursor.fetchone()
            if row:
                return datetime.fromisoformat(row[0].replace('Z', '+00:00'))
            return None
    
    def update_sync_status(self, mailbox: str, success: bool = True, message_count: int = 0):
        """Update sync status for a mailbox."""
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_status 
                (mailbox, last_sync_time, last_sync_success, message_count, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (mailbox, now, int(success), message_count, now))
            conn.commit()
    
    def cache_messages(self, messages: List[Dict[str, Any]], mailbox: str):
        """Cache a list of messages in the database."""
        if not messages:
            return
        
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            for msg in messages:
                # Convert recipients list to JSON string
                recipients_json = json.dumps(msg.get('to', []))
                
                conn.execute("""
                    INSERT OR REPLACE INTO messages 
                    (message_id, mailbox, subject, sender, recipients, date_received, 
                     content, snippet, last_synced)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    msg.get('id', ''),
                    mailbox,
                    msg.get('subject', ''),
                    msg.get('from', ''),
                    recipients_json,
                    msg.get('ts', now),
                    msg.get('content', ''),
                    msg.get('snippet', ''),
                    now
                ))
            conn.commit()
            logger.info(f"Cached {len(messages)} messages for mailbox {mailbox}")
    
    def get_messages(
        self, 
        mailbox: str, 
        limit: int = 100, 
        page: int = 0, 
        since: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get cached messages from the database."""
        offset = page * limit
        
        with sqlite3.connect(self.db_path) as conn:
            # Build query with optional date filter
            query = """
                SELECT message_id, mailbox, subject, sender, recipients, 
                       date_received, content, snippet
                FROM messages 
                WHERE mailbox = ?
            """
            params = [mailbox]
            
            if since:
                query += " AND date_received >= ?"
                params.append(since.isoformat())
            
            query += " ORDER BY date_received DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            # Convert rows to dictionaries
            messages = []
            for row in rows:
                message = {
                    'id': row[0],
                    'mailbox': row[1],
                    'subject': row[2],
                    'from': row[3],
                    'to': json.loads(row[4]) if row[4] else [],
                    'ts': row[5],
                    'content': row[6],
                    'snippet': row[7]
                }
                messages.append(message)
            
            return messages
    
    def get_message_count(self, mailbox: str) -> int:
        """Get the total number of cached messages for a mailbox."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE mailbox = ?",
                (mailbox,)
            )
            return cursor.fetchone()[0]
    
    def cleanup_old_messages(self, days_to_keep: int = 30):
        """Remove messages older than specified days to manage storage."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cutoff_iso = cutoff_date.isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM messages WHERE date_received < ?",
                (cutoff_iso,)
            )
            deleted_count = cursor.rowcount
            conn.commit()
            logger.info(f"Cleaned up {deleted_count} old messages")
            return deleted_count
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        with sqlite3.connect(self.db_path) as conn:
            # Get total message count
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            total_messages = cursor.fetchone()[0]
            
            # Get per-mailbox stats
            cursor = conn.execute("""
                SELECT mailbox, COUNT(*), MAX(date_received), MIN(date_received)
                FROM messages 
                GROUP BY mailbox
            """)
            mailbox_stats = {}
            for row in cursor.fetchall():
                mailbox_stats[row[0]] = {
                    'count': row[1],
                    'newest': row[2],
                    'oldest': row[3]
                }
            
            # Get sync status
            cursor = conn.execute("SELECT * FROM sync_status")
            sync_status = {}
            for row in cursor.fetchall():
                sync_status[row[0]] = {
                    'last_sync': row[1],
                    'success': bool(row[2]),
                    'message_count': row[3]
                }
            
            return {
                'total_messages': total_messages,
                'mailbox_stats': mailbox_stats,
                'sync_status': sync_status,
                'db_path': self.db_path
            }