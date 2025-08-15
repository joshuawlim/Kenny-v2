"""
Background sync worker for incremental Apple Mail synchronization.

This worker decouples slow JXA calls from API responses by maintaining
a local SQLite cache that's updated in the background.
"""

import asyncio
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List
import logging

from mail_cache import MailCache
from mail_live_optimized import fetch_recent_messages, fetch_messages_since_timestamp

logger = logging.getLogger(__name__)

class MailSyncWorker:
    """Background worker for incremental mail synchronization."""
    
    def __init__(self, 
                 sync_interval_minutes: int = 5,
                 initial_sync_days: int = 7,
                 max_messages_per_sync: int = 100):
        """
        Initialize the mail sync worker.
        
        Args:
            sync_interval_minutes: How often to sync (in minutes)
            initial_sync_days: How many days to sync on first run
            max_messages_per_sync: Maximum messages to fetch per sync
        """
        self.sync_interval_minutes = sync_interval_minutes
        self.initial_sync_days = initial_sync_days
        self.max_messages_per_sync = max_messages_per_sync
        
        self.cache = MailCache()
        self.is_running = False
        self.sync_thread = None
        self.mailboxes_to_sync = ["Inbox", "Sent"]
        
        # Sync statistics
        self.last_sync_time = None
        self.sync_stats = {
            "total_syncs": 0,
            "successful_syncs": 0,
            "failed_syncs": 0,
            "messages_synced": 0,
            "last_error": None
        }
    
    def start_background_sync(self):
        """Start the background sync worker in a separate thread."""
        if self.is_running:
            logger.warning("Sync worker is already running")
            return
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info(f"Mail sync worker started (interval: {self.sync_interval_minutes}m)")
    
    def stop_background_sync(self):
        """Stop the background sync worker."""
        self.is_running = False
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=10)
        logger.info("Mail sync worker stopped")
    
    def _sync_loop(self):
        """Main sync loop that runs in background thread."""
        logger.info("Background sync loop started")
        
        # Perform initial sync
        self._perform_sync(is_initial=True)
        
        # Regular sync loop
        while self.is_running:
            try:
                # Wait for next sync interval
                for _ in range(self.sync_interval_minutes * 60):
                    if not self.is_running:
                        break
                    time.sleep(1)
                
                if self.is_running:
                    self._perform_sync(is_initial=False)
                    
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                self.sync_stats["last_error"] = str(e)
                # Continue running despite errors
                time.sleep(60)  # Wait 1 minute before retrying
    
    def _perform_sync(self, is_initial: bool = False):
        """Perform synchronization for all configured mailboxes."""
        sync_start_time = time.time()
        self.sync_stats["total_syncs"] += 1
        
        try:
            total_messages_synced = 0
            
            for mailbox in self.mailboxes_to_sync:
                try:
                    messages_synced = self._sync_mailbox(mailbox, is_initial)
                    total_messages_synced += messages_synced
                    logger.info(f"Synced {messages_synced} messages from {mailbox}")
                    
                except Exception as e:
                    logger.error(f"Failed to sync mailbox {mailbox}: {e}")
                    # Continue with other mailboxes
            
            # Update sync statistics
            self.sync_stats["successful_syncs"] += 1
            self.sync_stats["messages_synced"] += total_messages_synced
            self.last_sync_time = datetime.now(timezone.utc)
            
            sync_duration = time.time() - sync_start_time
            sync_type = "initial" if is_initial else "incremental"
            logger.info(f"Completed {sync_type} sync: {total_messages_synced} messages in {sync_duration:.1f}s")
            
        except Exception as e:
            self.sync_stats["failed_syncs"] += 1
            self.sync_stats["last_error"] = str(e)
            logger.error(f"Sync failed: {e}")
    
    def _sync_mailbox(self, mailbox: str, is_initial: bool) -> int:
        """Sync a specific mailbox incrementally."""
        try:
            if is_initial:
                # Initial sync: fetch recent messages
                since_date = datetime.now(timezone.utc) - timedelta(days=self.initial_sync_days)
                messages = fetch_recent_messages(
                    mailbox=mailbox,
                    limit=self.max_messages_per_sync,
                    since_date=since_date,
                    timeout_seconds=30  # Longer timeout for initial sync
                )
                logger.info(f"Initial sync for {mailbox}: fetching messages since {since_date.isoformat()}")
            else:
                # Incremental sync: fetch only new messages
                last_sync = self.cache.get_last_sync_time(mailbox)
                if last_sync:
                    messages = fetch_messages_since_timestamp(
                        mailbox=mailbox,
                        since_timestamp=last_sync.isoformat(),
                        limit=self.max_messages_per_sync
                    )
                    logger.debug(f"Incremental sync for {mailbox}: fetching messages since {last_sync.isoformat()}")
                else:
                    # No previous sync, treat as initial
                    since_date = datetime.now(timezone.utc) - timedelta(days=1)
                    messages = fetch_recent_messages(
                        mailbox=mailbox,
                        limit=self.max_messages_per_sync,
                        since_date=since_date,
                        timeout_seconds=20
                    )
                    logger.info(f"No previous sync for {mailbox}, fetching last 24 hours")
            
            # Cache the messages
            if messages:
                self.cache.cache_messages(messages, mailbox)
                self.cache.update_sync_status(mailbox, success=True, message_count=len(messages))
            else:
                # Still update sync status even if no new messages
                self.cache.update_sync_status(mailbox, success=True, message_count=0)
            
            return len(messages)
            
        except Exception as e:
            # Update sync status to indicate failure
            self.cache.update_sync_status(mailbox, success=False, message_count=0)
            raise e
    
    def force_sync_now(self, mailbox: Optional[str] = None) -> Dict[str, Any]:
        """Force an immediate sync of specified mailbox or all mailboxes."""
        try:
            if mailbox:
                messages_synced = self._sync_mailbox(mailbox, is_initial=False)
                return {
                    "status": "success",
                    "mailbox": mailbox,
                    "messages_synced": messages_synced,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            else:
                self._perform_sync(is_initial=False)
                return {
                    "status": "success",
                    "mailboxes": self.mailboxes_to_sync,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync worker status and statistics."""
        cache_stats = self.cache.get_cache_stats()
        
        return {
            "worker_status": {
                "is_running": self.is_running,
                "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
                "sync_interval_minutes": self.sync_interval_minutes,
                "mailboxes": self.mailboxes_to_sync
            },
            "sync_statistics": self.sync_stats,
            "cache_statistics": cache_stats
        }

# Global sync worker instance
_sync_worker: Optional[MailSyncWorker] = None

def get_sync_worker() -> MailSyncWorker:
    """Get or create the global sync worker instance."""
    global _sync_worker
    if _sync_worker is None:
        _sync_worker = MailSyncWorker()
    return _sync_worker

def start_sync_worker():
    """Start the global sync worker."""
    worker = get_sync_worker()
    worker.start_background_sync()

def stop_sync_worker():
    """Stop the global sync worker."""
    global _sync_worker
    if _sync_worker:
        _sync_worker.stop_background_sync()
        _sync_worker = None

def get_cached_messages(
    mailbox: str, 
    limit: int = 100, 
    page: int = 0, 
    since: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get messages from cache (for fast API responses)."""
    worker = get_sync_worker()
    return worker.cache.get_messages(mailbox, limit, page, since)