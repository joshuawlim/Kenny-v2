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

class AdaptiveBatchSyncer:
    """Adaptive batch processing for problematic mailboxes like Inbox."""
    
    def __init__(self, mailbox: str):
        self.mailbox = mailbox
        self.batch_size = 10 if mailbox.lower() == "inbox" else 50  # Start small for Inbox
        self.success_rate = 0.0
        self.consecutive_failures = 0
        self.max_batch_size = 200
        self.min_batch_size = 5
        self.success_history = []  # Track last 10 attempts
        
    def update_success_rate(self, success: bool):
        """Update success rate based on recent attempts."""
        self.success_history.append(success)
        if len(self.success_history) > 10:
            self.success_history.pop(0)
        
        self.success_rate = sum(self.success_history) / len(self.success_history)
        
        if success:
            self.consecutive_failures = 0
        else:
            self.consecutive_failures += 1
    
    def adapt_batch_size(self):
        """Adapt batch size based on success rate."""
        if self.success_rate > 0.8 and self.consecutive_failures == 0:
            # High success rate: increase batch size
            self.batch_size = min(int(self.batch_size * 1.2), self.max_batch_size)
        elif self.success_rate < 0.5 or self.consecutive_failures >= 2:
            # Low success rate or consecutive failures: decrease batch size
            self.batch_size = max(int(self.batch_size * 0.6), self.min_batch_size)
        
        logger.info(f"Adapted batch size for {self.mailbox}: {self.batch_size} (success rate: {self.success_rate:.2f})")
    
    def should_abort(self) -> bool:
        """Determine if we should abort due to consistent failures."""
        return self.consecutive_failures >= 5 and self.success_rate < 0.2


class MailSyncWorker:
    """Background worker for incremental mail synchronization with adaptive batch processing."""
    
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
        
        # Adaptive batch processing
        self.adaptive_syncers = {
            mailbox: AdaptiveBatchSyncer(mailbox) 
            for mailbox in self.mailboxes_to_sync
        }
        
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
        """Sync a specific mailbox with adaptive batch processing."""
        adaptive_syncer = self.adaptive_syncers[mailbox]
        total_messages_synced = 0
        
        # Check if we should abort due to consistent failures
        if adaptive_syncer.should_abort():
            logger.warning(f"Aborting sync for {mailbox} due to consistent failures")
            self.cache.update_sync_status(mailbox, success=False, message_count=0)
            return 0
        
        try:
            if is_initial:
                # Initial sync with adaptive batching
                since_date = datetime.now(timezone.utc) - timedelta(days=self.initial_sync_days)
                total_messages_synced = self._adaptive_initial_sync(mailbox, since_date, adaptive_syncer)
            else:
                # Incremental sync
                last_sync = self.cache.get_last_sync_time(mailbox)
                if last_sync:
                    messages = fetch_messages_since_timestamp(
                        mailbox=mailbox,
                        since_timestamp=last_sync.isoformat(),
                        limit=adaptive_syncer.batch_size
                    )
                    if messages:
                        self.cache.cache_messages(messages, mailbox)
                    total_messages_synced = len(messages) if messages else 0
                    adaptive_syncer.update_success_rate(True)
                    logger.debug(f"Incremental sync for {mailbox}: {total_messages_synced} new messages")
                else:
                    # No previous sync, treat as initial with smaller scope
                    since_date = datetime.now(timezone.utc) - timedelta(days=1)
                    total_messages_synced = self._adaptive_initial_sync(mailbox, since_date, adaptive_syncer)
            
            # Cache the messages if successful
            if total_messages_synced >= 0:  # Even 0 is success
                self.cache.update_sync_status(mailbox, success=True, message_count=total_messages_synced)
                adaptive_syncer.adapt_batch_size()
            
            return total_messages_synced
            
        except Exception as e:
            # Update sync status and adaptive syncer on failure
            adaptive_syncer.update_success_rate(False)
            adaptive_syncer.adapt_batch_size()
            self.cache.update_sync_status(mailbox, success=False, message_count=0)
            logger.error(f"Sync failed for {mailbox}: {e}")
            raise e
    
    def _adaptive_initial_sync(self, mailbox: str, since_date: datetime, adaptive_syncer: AdaptiveBatchSyncer) -> int:
        """Perform adaptive initial sync with progressive batch processing."""
        total_messages = 0
        max_attempts = 10  # Prevent infinite loops
        attempt = 0
        
        logger.info(f"Starting adaptive initial sync for {mailbox} with batch size {adaptive_syncer.batch_size}")
        
        while attempt < max_attempts and not adaptive_syncer.should_abort():
            attempt += 1
            
            try:
                # Calculate timeout based on batch size (2-3 seconds per message expected)
                timeout_seconds = min(max(adaptive_syncer.batch_size * 2, 10), 45)
                
                messages = fetch_recent_messages(
                    mailbox=mailbox,
                    limit=adaptive_syncer.batch_size,
                    since_date=since_date,
                    timeout_seconds=timeout_seconds
                )
                
                if messages:
                    # Cache successful batch
                    self.cache.cache_messages(messages, mailbox)
                    batch_count = len(messages)
                    total_messages += batch_count
                    adaptive_syncer.update_success_rate(True)
                    
                    logger.info(f"Adaptive sync batch {attempt} for {mailbox}: {batch_count} messages (total: {total_messages})")
                    
                    # If we got fewer messages than batch size, we're likely done
                    if batch_count < adaptive_syncer.batch_size:
                        logger.info(f"Completed adaptive sync for {mailbox}: fetched {total_messages} messages in {attempt} batches")
                        break
                        
                    # Adjust since_date for next batch to avoid overlap
                    if messages:
                        # Get timestamp of oldest message in this batch
                        oldest_msg_ts = min(msg.get('ts', '') for msg in messages if msg.get('ts'))
                        if oldest_msg_ts:
                            try:
                                since_date = datetime.fromisoformat(oldest_msg_ts.replace('Z', '+00:00')) - timedelta(minutes=1)
                            except ValueError:
                                # If parsing fails, use current batch completion time
                                since_date = datetime.now(timezone.utc) - timedelta(hours=1)
                    
                else:
                    # No messages found - might be end of data
                    adaptive_syncer.update_success_rate(True)
                    logger.info(f"No more messages found for {mailbox} after {total_messages} messages")
                    break
                    
            except Exception as e:
                logger.warning(f"Adaptive sync batch {attempt} failed for {mailbox}: {e}")
                adaptive_syncer.update_success_rate(False)
                
                # If consecutive failures, break early
                if adaptive_syncer.consecutive_failures >= 3:
                    logger.warning(f"Too many consecutive failures for {mailbox}, stopping adaptive sync")
                    break
            
            # Adapt batch size after each attempt
            adaptive_syncer.adapt_batch_size()
            
            # Small delay between batches to avoid overwhelming the system
            time.sleep(1)
        
        return total_messages
    
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
        """Get current sync worker status and statistics including adaptive batch info."""
        cache_stats = self.cache.get_cache_stats()
        
        # Get adaptive syncer statistics
        adaptive_stats = {}
        for mailbox, syncer in self.adaptive_syncers.items():
            adaptive_stats[mailbox] = {
                "batch_size": syncer.batch_size,
                "success_rate": syncer.success_rate,
                "consecutive_failures": syncer.consecutive_failures,
                "should_abort": syncer.should_abort()
            }
        
        return {
            "worker_status": {
                "is_running": self.is_running,
                "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
                "sync_interval_minutes": self.sync_interval_minutes,
                "mailboxes": self.mailboxes_to_sync
            },
            "sync_statistics": self.sync_stats,
            "adaptive_batch_status": adaptive_stats,
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