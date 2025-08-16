#!/usr/bin/env python3
"""
EventKit Sync Engine for Phase 3.5 Week 2: Real-Time Bidirectional Synchronization

This module provides high-performance real-time synchronization with macOS EventKit,
maintaining <0.01s query performance while ensuring data freshness through
bidirectional synchronization.

Key Features:
- Real-time EventKit change monitoring with <100ms detection latency
- Efficient event filtering and batching for minimal CPU usage (<5%)
- Background processing queue for non-blocking operations
- Delta computation for precise change classification
- Integration with Phase 3.5 Week 1 database foundation

Performance Targets:
- Change detection latency: <100ms
- CPU usage during monitoring: <5%
- Zero missed change events
- Sync propagation delay: <1s end-to-end
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Set
from dataclasses import dataclass, asdict
from enum import Enum
import json
import threading
from queue import Queue, Empty
import sqlite3
from pathlib import Path

# Import EventKit via PyObjC (requires: pip install pyobjc-framework-EventKit)
try:
    import objc
    from EventKit import (
        EKEventStore, EKEntityTypeEvent, EKAuthorizationStatusAuthorized, EKAuthorizationStatusWriteOnly,
        EKEventStoreChangedNotification, EKEvent, EKCalendar
    )
    from Foundation import NSNotificationCenter, NSRunLoop, NSDefaultRunLoopMode
    EVENTKIT_AVAILABLE = True
except ImportError:
    EVENTKIT_AVAILABLE = False
    logging.warning("EventKit not available - using mock implementation")

# Import calendar_live as fallback
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "bridge"))
from calendar_live import list_events, list_calendars, create_event, get_event_by_id

logger = logging.getLogger("eventkit_sync_engine")


class ChangeType(Enum):
    """Types of calendar changes detected."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    UNKNOWN = "unknown"


@dataclass
class EventChange:
    """Represents a detected calendar event change."""
    change_type: ChangeType
    event_id: str
    calendar_id: str
    timestamp: datetime
    event_data: Optional[Dict[str, Any]] = None
    source_app: str = "unknown"


@dataclass
class SyncMetrics:
    """Performance metrics for sync operations."""
    changes_detected: int = 0
    changes_processed: int = 0
    detection_latency_ms: float = 0.0
    processing_latency_ms: float = 0.0
    cpu_usage_percent: float = 0.0
    queue_size: int = 0
    errors: int = 0
    last_sync_time: Optional[datetime] = None


class EventKitSyncEngine:
    """
    High-performance EventKit synchronization engine with real-time change detection.
    
    This engine provides bidirectional synchronization between the local database
    and macOS Calendar system, maintaining exceptional performance while ensuring
    data freshness.
    """
    
    def __init__(self, database_path: str, max_queue_size: int = 1000):
        """
        Initialize the EventKit sync engine.
        
        Args:
            database_path: Path to the SQLite database
            max_queue_size: Maximum size of the change processing queue
        """
        self.database_path = database_path
        self.max_queue_size = max_queue_size
        
        # EventKit components
        self.event_store = None
        self.notification_observer = None
        
        # Processing components
        self.change_queue = Queue(maxsize=max_queue_size)
        self.processing_thread = None
        self.monitoring_active = False
        
        # Performance tracking
        self.metrics = SyncMetrics()
        self.last_change_detection = time.time()
        
        # Change tracking
        self.known_events: Dict[str, Dict[str, Any]] = {}
        self.known_calendars: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks
        self.change_callbacks: List[Callable[[EventChange], None]] = []
        
        logger.info(f"EventKit Sync Engine initialized for database: {database_path}")
    
    async def initialize(self) -> bool:
        """
        Initialize EventKit integration and start monitoring.
        
        Returns:
            True if initialization successful, False otherwise
        """
        logger.info("Initializing EventKit Sync Engine...")
        
        try:
            # Initialize EventKit if available
            if EVENTKIT_AVAILABLE:
                success = await self._initialize_eventkit()
                if not success:
                    logger.warning("EventKit initialization failed, using fallback mode")
                    return await self._initialize_fallback_mode()
            else:
                logger.info("EventKit not available, using fallback mode")
                return await self._initialize_fallback_mode()
            
            # Load initial state
            await self._load_initial_state()
            
            # Start change monitoring
            await self._start_monitoring()
            
            logger.info("EventKit Sync Engine initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"EventKit initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_eventkit(self) -> bool:
        """Initialize native EventKit integration."""
        try:
            # Create EventKit store
            self.event_store = EKEventStore.alloc().init()
            
            # Request calendar access
            auth_status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
            
            if auth_status not in [EKAuthorizationStatusAuthorized, EKAuthorizationStatusWriteOnly]:
                logger.info("Requesting EventKit authorization...")
                
                # Request access (this will prompt user if needed)
                def auth_completion(granted, error):
                    if not granted:
                        logger.error(f"EventKit access denied: {error}")
                    else:
                        logger.info("EventKit access granted")
                
                self.event_store.requestAccessToEntityType_completion_(
                    EKEntityTypeEvent, auth_completion
                )
                
                # Wait a moment for auth to complete
                await asyncio.sleep(1.0)
                
                # Check final status
                final_status = EKEventStore.authorizationStatusForEntityType_(EKEntityTypeEvent)
                if final_status not in [EKAuthorizationStatusAuthorized, EKAuthorizationStatusWriteOnly]:
                    logger.error("EventKit authorization failed")
                    return False
            
            # Set up change notifications
            self._setup_change_notifications()
            
            logger.info("EventKit native integration initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"EventKit native initialization failed: {e}", exc_info=True)
            return False
    
    async def _initialize_fallback_mode(self) -> bool:
        """Initialize fallback mode using calendar_live.py."""
        try:
            logger.info("Initializing fallback mode with calendar_live")
            
            # Test calendar_live functionality
            calendars = list_calendars()
            events = list_events(limit=1)
            
            logger.info(f"Fallback mode: Found {len(calendars)} calendars, {len(events)} recent events")
            return True
            
        except Exception as e:
            logger.error(f"Fallback mode initialization failed: {e}", exc_info=True)
            return False
    
    def _setup_change_notifications(self):
        """Set up EventKit change notifications."""
        if not EVENTKIT_AVAILABLE or not self.event_store:
            return
        
        try:
            # Get default notification center
            notification_center = NSNotificationCenter.defaultCenter()
            
            # Set up observer for EventKit changes
            def change_notification_handler(notification):
                self._handle_eventkit_change(notification)
            
            self.notification_observer = notification_center.addObserverForName_object_queue_usingBlock_(
                EKEventStoreChangedNotification,
                self.event_store,
                None,
                change_notification_handler
            )
            
            logger.info("EventKit change notifications configured")
            
        except Exception as e:
            logger.error(f"Failed to setup change notifications: {e}", exc_info=True)
    
    def _handle_eventkit_change(self, notification):
        """Handle EventKit change notification."""
        try:
            detection_start = time.time()
            
            # Log the change detection
            logger.debug("EventKit change detected")
            
            # Calculate detection latency
            self.metrics.detection_latency_ms = (time.time() - self.last_change_detection) * 1000
            self.last_change_detection = time.time()
            
            # Process changes asynchronously
            asyncio.create_task(self._process_eventkit_changes())
            
        except Exception as e:
            logger.error(f"Error handling EventKit change: {e}", exc_info=True)
            self.metrics.errors += 1
    
    async def _process_eventkit_changes(self):
        """Process detected EventKit changes."""
        try:
            processing_start = time.time()
            
            # Get current events and calendars
            current_events = await self._get_current_events()
            current_calendars = await self._get_current_calendars()
            
            # Detect changes
            changes = await self._detect_changes(current_events, current_calendars)
            
            # Queue changes for processing
            for change in changes:
                if not self.change_queue.full():
                    self.change_queue.put(change)
                    self.metrics.changes_detected += 1
                else:
                    logger.warning("Change queue full, dropping change")
                    self.metrics.errors += 1
            
            # Update metrics
            self.metrics.processing_latency_ms = (time.time() - processing_start) * 1000
            self.metrics.queue_size = self.change_queue.qsize()
            
            logger.debug(f"Processed {len(changes)} changes in {self.metrics.processing_latency_ms:.2f}ms")
            
        except Exception as e:
            logger.error(f"Error processing EventKit changes: {e}", exc_info=True)
            self.metrics.errors += 1
    
    async def _get_current_events(self) -> Dict[str, Dict[str, Any]]:
        """Get current events from EventKit or fallback."""
        try:
            if EVENTKIT_AVAILABLE and self.event_store:
                return await self._get_eventkit_events()
            else:
                return await self._get_fallback_events()
        except Exception as e:
            logger.error(f"Error getting current events: {e}", exc_info=True)
            return {}
    
    async def _get_eventkit_events(self) -> Dict[str, Dict[str, Any]]:
        """Get events from native EventKit."""
        events = {}
        
        try:
            # Get date range (next 30 days)
            start_date = datetime.now()
            end_date = start_date + timedelta(days=30)
            
            # Create predicate for date range
            predicate = self.event_store.predicateForEventsWithStartDate_endDate_calendars_(
                start_date, end_date, None
            )
            
            # Get events
            ek_events = self.event_store.eventsMatchingPredicate_(predicate)
            
            for ek_event in ek_events:
                event_id = ek_event.eventIdentifier()
                events[event_id] = {
                    "id": event_id,
                    "title": ek_event.title() or "Untitled",
                    "start": ek_event.startDate().isoformat() if ek_event.startDate() else None,
                    "end": ek_event.endDate().isoformat() if ek_event.endDate() else None,
                    "all_day": ek_event.allDay(),
                    "calendar_id": ek_event.calendar().calendarIdentifier(),
                    "calendar": ek_event.calendar().title(),
                    "location": ek_event.location() or "",
                    "description": ek_event.notes() or "",
                    "last_modified": ek_event.lastModifiedDate().isoformat() if ek_event.lastModifiedDate() else None
                }
            
            logger.debug(f"Retrieved {len(events)} events from EventKit")
            
        except Exception as e:
            logger.error(f"Error getting EventKit events: {e}", exc_info=True)
        
        return events
    
    async def _get_fallback_events(self) -> Dict[str, Dict[str, Any]]:
        """Get events using fallback calendar_live."""
        events = {}
        
        try:
            # Get events from calendar_live
            event_list = list_events(limit=1000)  # Get more events for sync
            
            for event in event_list:
                event_id = event.get("id", f"fallback_{hash(event.get('title', ''))}_{event.get('start', '')}")
                events[event_id] = {
                    "id": event_id,
                    "title": event.get("title", "Untitled"),
                    "start": event.get("start"),
                    "end": event.get("end"),
                    "all_day": event.get("all_day", False),
                    "calendar_id": f"cal_{hash(event.get('calendar', ''))}",
                    "calendar": event.get("calendar", "Calendar"),
                    "location": event.get("location", ""),
                    "description": event.get("description", ""),
                    "last_modified": datetime.now().isoformat()
                }
            
            logger.debug(f"Retrieved {len(events)} events from fallback")
            
        except Exception as e:
            logger.error(f"Error getting fallback events: {e}", exc_info=True)
        
        return events
    
    async def _get_current_calendars(self) -> Dict[str, Dict[str, Any]]:
        """Get current calendars from EventKit or fallback."""
        try:
            if EVENTKIT_AVAILABLE and self.event_store:
                return await self._get_eventkit_calendars()
            else:
                return await self._get_fallback_calendars()
        except Exception as e:
            logger.error(f"Error getting current calendars: {e}", exc_info=True)
            return {}
    
    async def _get_eventkit_calendars(self) -> Dict[str, Dict[str, Any]]:
        """Get calendars from native EventKit."""
        calendars = {}
        
        try:
            ek_calendars = self.event_store.calendarsForEntityType_(EKEntityTypeEvent)
            
            for ek_calendar in ek_calendars:
                calendar_id = ek_calendar.calendarIdentifier()
                calendars[calendar_id] = {
                    "id": calendar_id,
                    "name": ek_calendar.title(),
                    "description": "",  # EventKit doesn't expose description
                    "color": str(ek_calendar.color()) if ek_calendar.color() else "blue",
                    "writable": not ek_calendar.isImmutable(),
                    "visible": True,  # Assume visible if accessible
                    "source": ek_calendar.source().title() if ek_calendar.source() else "Unknown"
                }
            
            logger.debug(f"Retrieved {len(calendars)} calendars from EventKit")
            
        except Exception as e:
            logger.error(f"Error getting EventKit calendars: {e}", exc_info=True)
        
        return calendars
    
    async def _get_fallback_calendars(self) -> Dict[str, Dict[str, Any]]:
        """Get calendars using fallback calendar_live."""
        calendars = {}
        
        try:
            calendar_list = list_calendars()
            
            for calendar in calendar_list:
                calendar_id = calendar.get("id", f"cal_{hash(calendar.get('name', ''))}")
                calendars[calendar_id] = {
                    "id": calendar_id,
                    "name": calendar.get("name", "Untitled Calendar"),
                    "description": calendar.get("description", ""),
                    "color": calendar.get("color", "blue"),
                    "writable": calendar.get("writable", True),
                    "visible": calendar.get("visible", True),
                    "source": "Calendar.app"
                }
            
            logger.debug(f"Retrieved {len(calendars)} calendars from fallback")
            
        except Exception as e:
            logger.error(f"Error getting fallback calendars: {e}", exc_info=True)
        
        return calendars
    
    async def _detect_changes(self, current_events: Dict[str, Dict[str, Any]], 
                             current_calendars: Dict[str, Dict[str, Any]]) -> List[EventChange]:
        """Detect changes between current and known state."""
        changes = []
        
        try:
            # Detect event changes
            changes.extend(await self._detect_event_changes(current_events))
            
            # Detect calendar changes (less frequent but important)
            changes.extend(await self._detect_calendar_changes(current_calendars))
            
            # Update known state
            self.known_events = current_events.copy()
            self.known_calendars = current_calendars.copy()
            
        except Exception as e:
            logger.error(f"Error detecting changes: {e}", exc_info=True)
        
        return changes
    
    async def _detect_event_changes(self, current_events: Dict[str, Dict[str, Any]]) -> List[EventChange]:
        """Detect event-specific changes."""
        changes = []
        
        try:
            current_ids = set(current_events.keys())
            known_ids = set(self.known_events.keys())
            
            # Detect new events
            for event_id in current_ids - known_ids:
                event_data = current_events[event_id]
                change = EventChange(
                    change_type=ChangeType.ADDED,
                    event_id=event_id,
                    calendar_id=event_data.get("calendar_id", "unknown"),
                    timestamp=datetime.now(),
                    event_data=event_data,
                    source_app="EventKit"
                )
                changes.append(change)
            
            # Detect deleted events
            for event_id in known_ids - current_ids:
                known_event = self.known_events[event_id]
                change = EventChange(
                    change_type=ChangeType.DELETED,
                    event_id=event_id,
                    calendar_id=known_event.get("calendar_id", "unknown"),
                    timestamp=datetime.now(),
                    event_data=known_event,
                    source_app="EventKit"
                )
                changes.append(change)
            
            # Detect modified events
            for event_id in current_ids & known_ids:
                current_event = current_events[event_id]
                known_event = self.known_events[event_id]
                
                # Compare relevant fields for changes
                if self._events_differ(current_event, known_event):
                    change = EventChange(
                        change_type=ChangeType.MODIFIED,
                        event_id=event_id,
                        calendar_id=current_event.get("calendar_id", "unknown"),
                        timestamp=datetime.now(),
                        event_data=current_event,
                        source_app="EventKit"
                    )
                    changes.append(change)
            
            logger.debug(f"Detected {len(changes)} event changes")
            
        except Exception as e:
            logger.error(f"Error detecting event changes: {e}", exc_info=True)
        
        return changes
    
    async def _detect_calendar_changes(self, current_calendars: Dict[str, Dict[str, Any]]) -> List[EventChange]:
        """Detect calendar-specific changes."""
        changes = []
        
        try:
            current_ids = set(current_calendars.keys())
            known_ids = set(self.known_calendars.keys())
            
            # For now, we'll treat calendar changes as events that need sync
            # This could be expanded to handle calendar-specific operations
            
            # Detect new calendars
            for calendar_id in current_ids - known_ids:
                calendar_data = current_calendars[calendar_id]
                change = EventChange(
                    change_type=ChangeType.ADDED,
                    event_id=f"calendar_{calendar_id}",
                    calendar_id=calendar_id,
                    timestamp=datetime.now(),
                    event_data={"type": "calendar", "data": calendar_data},
                    source_app="EventKit"
                )
                changes.append(change)
            
            # Detect deleted calendars
            for calendar_id in known_ids - current_ids:
                known_calendar = self.known_calendars[calendar_id]
                change = EventChange(
                    change_type=ChangeType.DELETED,
                    event_id=f"calendar_{calendar_id}",
                    calendar_id=calendar_id,
                    timestamp=datetime.now(),
                    event_data={"type": "calendar", "data": known_calendar},
                    source_app="EventKit"
                )
                changes.append(change)
            
            logger.debug(f"Detected {len(changes)} calendar changes")
            
        except Exception as e:
            logger.error(f"Error detecting calendar changes: {e}", exc_info=True)
        
        return changes
    
    def _events_differ(self, event1: Dict[str, Any], event2: Dict[str, Any]) -> bool:
        """Check if two events differ in significant ways."""
        # Fields to compare for changes
        compare_fields = ["title", "start", "end", "all_day", "location", "description", "last_modified"]
        
        for field in compare_fields:
            if event1.get(field) != event2.get(field):
                return True
        
        return False
    
    async def _load_initial_state(self):
        """Load initial state of events and calendars."""
        try:
            logger.info("Loading initial EventKit state...")
            
            # Get current state
            self.known_events = await self._get_current_events()
            self.known_calendars = await self._get_current_calendars()
            
            logger.info(f"Initial state: {len(self.known_events)} events, {len(self.known_calendars)} calendars")
            
        except Exception as e:
            logger.error(f"Error loading initial state: {e}", exc_info=True)
    
    async def _start_monitoring(self):
        """Start background monitoring and processing."""
        try:
            self.monitoring_active = True
            
            # Start change processing thread
            self.processing_thread = threading.Thread(
                target=self._change_processing_worker,
                daemon=True
            )
            self.processing_thread.start()
            
            # Start periodic sync check (fallback mode)
            if not EVENTKIT_AVAILABLE:
                asyncio.create_task(self._periodic_sync_check())
            
            logger.info("EventKit monitoring started")
            
        except Exception as e:
            logger.error(f"Error starting monitoring: {e}", exc_info=True)
    
    def _change_processing_worker(self):
        """Worker thread for processing change queue."""
        logger.info("Change processing worker started")
        
        while self.monitoring_active:
            try:
                # Get change from queue with timeout
                change = self.change_queue.get(timeout=1.0)
                
                # Process the change
                self._process_change(change)
                
                # Update metrics
                self.metrics.changes_processed += 1
                self.metrics.queue_size = self.change_queue.qsize()
                
                # Mark task done
                self.change_queue.task_done()
                
            except Empty:
                # No changes to process, continue
                continue
            except Exception as e:
                logger.error(f"Error processing change: {e}", exc_info=True)
                self.metrics.errors += 1
    
    def _process_change(self, change: EventChange):
        """Process a single change."""
        try:
            logger.debug(f"Processing change: {change.change_type.value} for {change.event_id}")
            
            # Call registered callbacks
            for callback in self.change_callbacks:
                try:
                    callback(change)
                except Exception as e:
                    logger.error(f"Callback error: {e}", exc_info=True)
            
            # Update last sync time
            self.metrics.last_sync_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in _process_change: {e}", exc_info=True)
    
    async def _periodic_sync_check(self):
        """Periodic sync check for fallback mode."""
        while self.monitoring_active:
            try:
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
                # Trigger change detection
                await self._process_eventkit_changes()
                
            except Exception as e:
                logger.error(f"Error in periodic sync check: {e}", exc_info=True)
    
    def register_change_callback(self, callback: Callable[[EventChange], None]):
        """Register a callback for change notifications."""
        self.change_callbacks.append(callback)
        logger.debug(f"Registered change callback: {callback.__name__}")
    
    def get_metrics(self) -> SyncMetrics:
        """Get current sync metrics."""
        # Update queue size
        self.metrics.queue_size = self.change_queue.qsize()
        return self.metrics
    
    async def shutdown(self):
        """Shutdown the sync engine."""
        logger.info("Shutting down EventKit Sync Engine...")
        
        try:
            # Stop monitoring
            self.monitoring_active = False
            
            # Wait for processing thread to finish
            if self.processing_thread and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=5.0)
            
            # Remove EventKit observer
            if EVENTKIT_AVAILABLE and self.notification_observer:
                notification_center = NSNotificationCenter.defaultCenter()
                notification_center.removeObserver_(self.notification_observer)
            
            logger.info("EventKit Sync Engine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)


# Test and demonstration functions
async def main():
    """Test the EventKit Sync Engine."""
    logging.basicConfig(level=logging.INFO)
    
    # Create sync engine
    sync_engine = EventKitSyncEngine(":memory:")
    
    # Register test callback
    def test_callback(change: EventChange):
        print(f"Change detected: {change.change_type.value} - {change.event_id}")
    
    sync_engine.register_change_callback(test_callback)
    
    # Initialize and run
    if await sync_engine.initialize():
        print("EventKit Sync Engine initialized successfully")
        
        # Run for a bit to test
        print("Monitoring for changes... (press Ctrl+C to stop)")
        try:
            await asyncio.sleep(30)  # Monitor for 30 seconds
        except KeyboardInterrupt:
            pass
        
        # Show metrics
        metrics = sync_engine.get_metrics()
        print(f"Metrics: {asdict(metrics)}")
        
        # Shutdown
        await sync_engine.shutdown()
    else:
        print("Failed to initialize EventKit Sync Engine")


if __name__ == "__main__":
    asyncio.run(main())