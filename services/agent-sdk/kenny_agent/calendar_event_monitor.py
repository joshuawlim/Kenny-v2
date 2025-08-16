"""
Calendar Event Monitor for Kenny v2.1 Phase 3.2.3

EventKit integration for real-time macOS Calendar change monitoring.
Provides intelligent cache invalidation and refresh coordination based on
actual calendar modifications.

Key Features:
- Real-time EventKit change notifications
- Intelligent mapping of calendar changes to affected cache entries
- Smart cache invalidation for affected date ranges
- Cross-tier cache refresh coordination
- Performance impact minimization
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass
from enum import Enum


class CalendarChangeType(Enum):
    """Types of calendar changes."""
    EVENT_ADDED = "event_added"
    EVENT_MODIFIED = "event_modified"
    EVENT_DELETED = "event_deleted"
    CALENDAR_MODIFIED = "calendar_modified"
    STORE_CHANGED = "store_changed"


@dataclass
class CalendarEvent:
    """Represents a calendar event change."""
    change_type: CalendarChangeType
    event_id: Optional[str]
    calendar_id: Optional[str]
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    title: Optional[str]
    participants: List[str]
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class CacheInvalidationRange:
    """Represents a range of cache entries to invalidate."""
    date_range: tuple  # (start_date, end_date)
    query_patterns: List[str]
    affected_contacts: List[str]
    priority: float  # 0.0 to 1.0, higher means more urgent
    reasoning: str


class CalendarEventMonitor:
    """
    Monitor macOS Calendar changes via EventKit and intelligently manage cache invalidation.
    
    Integrates with the CalendarBridgeTool to monitor real-time calendar changes
    and coordinate intelligent cache updates across all cache tiers.
    """
    
    def __init__(self, agent, bridge_url: str = "http://localhost:5100"):
        """Initialize the calendar event monitor."""
        self.agent = agent
        self.bridge_url = bridge_url
        self.logger = logging.getLogger(f"calendar-event-monitor-{agent.agent_id}")
        
        # Monitoring configuration
        self.monitoring_enabled = False
        self.polling_interval = 5.0  # seconds
        self.change_detection_window = 60  # seconds to batch changes
        
        # Change tracking
        self.recent_changes: List[CalendarEvent] = []
        self.last_change_check = datetime.now()
        self.change_handlers: List[Callable] = []
        
        # Cache invalidation strategy
        self.invalidation_debounce = 2.0  # seconds to debounce rapid changes
        self.pending_invalidations: Dict[str, CacheInvalidationRange] = {}
        self.last_invalidation_time = {}
        
        # Performance metrics
        self.monitoring_metrics = {
            "changes_detected": 0,
            "cache_invalidations": 0,
            "successful_refreshes": 0,
            "monitoring_errors": 0,
            "avg_invalidation_time": 0.0
        }
        
        # Calendar state tracking for intelligent change detection
        self.known_events: Dict[str, Dict] = {}  # event_id -> event_data
        self.last_sync_time = datetime.now()
        
        # Background tasks
        self.monitor_task = None
        self.invalidation_task = None
    
    async def start_monitoring(self):
        """Start real-time calendar change monitoring."""
        if self.monitoring_enabled:
            self.logger.warning("Calendar monitoring already enabled")
            return
        
        self.monitoring_enabled = True
        self.logger.info("Starting calendar event monitoring...")
        
        # Register for change notifications
        await self.register_change_notifications()
        
        # Start background monitoring tasks
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        self.invalidation_task = asyncio.create_task(self._invalidation_loop())
        
        self.logger.info("Calendar event monitoring started successfully")
    
    async def stop_monitoring(self):
        """Stop calendar change monitoring."""
        self.monitoring_enabled = False
        
        # Cancel background tasks
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        if self.invalidation_task:
            self.invalidation_task.cancel()
            try:
                await self.invalidation_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Calendar event monitoring stopped")
    
    async def register_change_notifications(self):
        """Register for EventKit change notifications via bridge."""
        try:
            # Since we can't directly access EventKit from Python,
            # we'll use polling-based change detection through the bridge
            await self._initialize_calendar_state()
            self.logger.info("Registered for calendar change notifications via polling")
            
        except Exception as e:
            self.logger.error(f"Failed to register for change notifications: {e}")
            self.monitoring_metrics["monitoring_errors"] += 1
    
    async def handle_calendar_change(self, event_change: CalendarEvent):
        """Handle a detected calendar change and trigger appropriate cache actions."""
        self.logger.info(f"Handling calendar change: {event_change.change_type.value}")
        self.monitoring_metrics["changes_detected"] += 1
        
        try:
            # Add to recent changes for batching
            self.recent_changes.append(event_change)
            
            # Identify affected cache entries
            affected_ranges = await self.identify_affected_cache_entries(event_change)
            
            # Schedule intelligent refresh
            for range_info in affected_ranges:
                await self._schedule_cache_invalidation(range_info)
            
            # Trigger immediate refresh for high-priority changes
            if self._is_high_priority_change(event_change):
                await self.trigger_intelligent_refresh([range_info.query_patterns[0] for range_info in affected_ranges])
            
        except Exception as e:
            self.logger.error(f"Error handling calendar change: {e}")
            self.monitoring_metrics["monitoring_errors"] += 1
    
    async def identify_affected_cache_entries(self, change: CalendarEvent) -> List[CacheInvalidationRange]:
        """Identify cache entries affected by a calendar change."""
        affected_ranges = []
        
        try:
            # Determine date range affected by the change
            if change.start_date and change.end_date:
                # Event has specific dates - invalidate that range plus buffer
                start_date = change.start_date - timedelta(hours=1)  # Buffer for "upcoming" queries
                end_date = change.end_date + timedelta(hours=1)
                
                # Extended range for weekly/monthly views
                extended_start = change.start_date - timedelta(days=7)
                extended_end = change.end_date + timedelta(days=7)
                
            else:
                # General change - invalidate current and near-term queries
                now = datetime.now()
                start_date = now - timedelta(hours=1)
                end_date = now + timedelta(days=7)
                extended_start = now - timedelta(days=1)
                extended_end = now + timedelta(days=30)
            
            # Identify affected query patterns based on change type
            query_patterns = self._get_affected_query_patterns(change)
            
            # Extract affected contacts
            affected_contacts = change.participants if change.participants else []
            
            # Create primary invalidation range
            primary_range = CacheInvalidationRange(
                date_range=(start_date, end_date),
                query_patterns=query_patterns[:3],  # Most specific patterns
                affected_contacts=affected_contacts,
                priority=self._calculate_change_priority(change),
                reasoning=f"Direct impact from {change.change_type.value}"
            )
            affected_ranges.append(primary_range)
            
            # Create extended range for broader impact
            if len(query_patterns) > 3:
                extended_range = CacheInvalidationRange(
                    date_range=(extended_start, extended_end),
                    query_patterns=query_patterns[3:],  # Broader patterns
                    affected_contacts=affected_contacts,
                    priority=max(0.3, primary_range.priority - 0.3),
                    reasoning=f"Extended impact from {change.change_type.value}"
                )
                affected_ranges.append(extended_range)
            
            self.logger.debug(f"Identified {len(affected_ranges)} affected cache ranges")
            return affected_ranges
            
        except Exception as e:
            self.logger.error(f"Error identifying affected cache entries: {e}")
            return []
    
    async def trigger_intelligent_refresh(self, cache_keys: List[str]):
        """Trigger intelligent refresh of specified cache entries."""
        start_time = time.time()
        successful_refreshes = 0
        
        try:
            self.logger.info(f"Triggering intelligent refresh for {len(cache_keys)} cache keys")
            
            # Group cache keys by pattern for efficient batch processing
            pattern_groups = self._group_cache_keys_by_pattern(cache_keys)
            
            # Refresh each pattern group
            for pattern, keys in pattern_groups.items():
                try:
                    # Invalidate existing cache entries first
                    await self._invalidate_cache_pattern(pattern)
                    
                    # Pre-warm with fresh data
                    await self._prewarm_cache_pattern(pattern)
                    
                    successful_refreshes += len(keys)
                    self.logger.debug(f"Successfully refreshed pattern: {pattern}")
                    
                except Exception as e:
                    self.logger.error(f"Error refreshing pattern {pattern}: {e}")
            
            # Update metrics
            refresh_time = time.time() - start_time
            self.monitoring_metrics["successful_refreshes"] += successful_refreshes
            self.monitoring_metrics["cache_invalidations"] += 1
            
            # Update average invalidation time
            if self.monitoring_metrics["avg_invalidation_time"] == 0:
                self.monitoring_metrics["avg_invalidation_time"] = refresh_time
            else:
                alpha = 0.1
                self.monitoring_metrics["avg_invalidation_time"] = (
                    alpha * refresh_time + 
                    (1 - alpha) * self.monitoring_metrics["avg_invalidation_time"]
                )
            
            self.logger.info(f"Intelligent refresh completed in {refresh_time:.3f}s: "
                           f"{successful_refreshes}/{len(cache_keys)} successful")
            
        except Exception as e:
            self.logger.error(f"Error in intelligent refresh: {e}")
            self.monitoring_metrics["monitoring_errors"] += 1
    
    async def _monitoring_loop(self):
        """Main monitoring loop for detecting calendar changes."""
        while self.monitoring_enabled:
            try:
                # Poll for calendar changes
                changes = await self._detect_calendar_changes()
                
                # Process detected changes
                for change in changes:
                    await self.handle_calendar_change(change)
                
                # Update last check time
                self.last_change_check = datetime.now()
                
                # Wait for next polling interval
                await asyncio.sleep(self.polling_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                self.monitoring_metrics["monitoring_errors"] += 1
                await asyncio.sleep(self.polling_interval)
    
    async def _invalidation_loop(self):
        """Background loop for processing batched cache invalidations."""
        while self.monitoring_enabled:
            try:
                # Process pending invalidations
                await self._process_pending_invalidations()
                
                # Wait before next processing cycle
                await asyncio.sleep(self.invalidation_debounce)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in invalidation loop: {e}")
                await asyncio.sleep(1.0)
    
    async def _detect_calendar_changes(self) -> List[CalendarEvent]:
        """Detect calendar changes by comparing current state with known state."""
        changes = []
        
        try:
            # Get current calendar events via bridge
            current_events = await self._fetch_current_calendar_state()
            
            # Compare with known events to detect changes
            current_event_ids = set(current_events.keys())
            known_event_ids = set(self.known_events.keys())
            
            # Detect new events
            new_event_ids = current_event_ids - known_event_ids
            for event_id in new_event_ids:
                event_data = current_events[event_id]
                change = CalendarEvent(
                    change_type=CalendarChangeType.EVENT_ADDED,
                    event_id=event_id,
                    calendar_id=event_data.get("calendar_id"),
                    start_date=self._parse_date(event_data.get("start_date")),
                    end_date=self._parse_date(event_data.get("end_date")),
                    title=event_data.get("title"),
                    participants=event_data.get("participants", []),
                    timestamp=datetime.now(),
                    metadata=event_data
                )
                changes.append(change)
            
            # Detect deleted events
            deleted_event_ids = known_event_ids - current_event_ids
            for event_id in deleted_event_ids:
                event_data = self.known_events[event_id]
                change = CalendarEvent(
                    change_type=CalendarChangeType.EVENT_DELETED,
                    event_id=event_id,
                    calendar_id=event_data.get("calendar_id"),
                    start_date=self._parse_date(event_data.get("start_date")),
                    end_date=self._parse_date(event_data.get("end_date")),
                    title=event_data.get("title"),
                    participants=event_data.get("participants", []),
                    timestamp=datetime.now(),
                    metadata=event_data
                )
                changes.append(change)
            
            # Detect modified events
            for event_id in current_event_ids & known_event_ids:
                current_data = current_events[event_id]
                known_data = self.known_events[event_id]
                
                if self._event_has_changed(current_data, known_data):
                    change = CalendarEvent(
                        change_type=CalendarChangeType.EVENT_MODIFIED,
                        event_id=event_id,
                        calendar_id=current_data.get("calendar_id"),
                        start_date=self._parse_date(current_data.get("start_date")),
                        end_date=self._parse_date(current_data.get("end_date")),
                        title=current_data.get("title"),
                        participants=current_data.get("participants", []),
                        timestamp=datetime.now(),
                        metadata=current_data
                    )
                    changes.append(change)
            
            # Update known state
            self.known_events = current_events.copy()
            
            if changes:
                self.logger.info(f"Detected {len(changes)} calendar changes")
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Error detecting calendar changes: {e}")
            return []
    
    async def _fetch_current_calendar_state(self) -> Dict[str, Dict]:
        """Fetch current calendar state via bridge."""
        try:
            # Use calendar bridge to get current events
            bridge_tool = self.agent.tools.get("calendar_bridge")
            if not bridge_tool:
                self.logger.error("Calendar bridge tool not available")
                return {}
            
            # Get events for the next 30 days to monitor changes
            end_date = (datetime.now() + timedelta(days=30)).isoformat()
            start_date = (datetime.now() - timedelta(days=7)).isoformat()
            
            events_response = await bridge_tool.get_events({
                "start_date": start_date,
                "end_date": end_date,
                "include_all_day": True
            })
            
            # Convert to indexed format
            events_dict = {}
            if events_response.get("success") and events_response.get("events"):
                for event in events_response["events"]:
                    event_id = event.get("id", event.get("uid", str(hash(str(event)))))
                    events_dict[event_id] = event
            
            return events_dict
            
        except Exception as e:
            self.logger.error(f"Error fetching calendar state: {e}")
            return {}
    
    def _event_has_changed(self, current: Dict, known: Dict) -> bool:
        """Check if an event has meaningful changes."""
        # Check key fields for changes
        key_fields = ["title", "start_date", "end_date", "location", "participants"]
        
        for field in key_fields:
            if current.get(field) != known.get(field):
                return True
        
        return False
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            # Handle various date formats
            if 'T' in date_str:
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            else:
                return datetime.fromisoformat(date_str)
        except Exception:
            return None
    
    def _get_affected_query_patterns(self, change: CalendarEvent) -> List[str]:
        """Get query patterns affected by a calendar change."""
        patterns = []
        
        # Base patterns always affected by calendar changes
        base_patterns = [
            "events today",
            "meetings today",
            "schedule today",
            "upcoming events",
            "upcoming meetings"
        ]
        patterns.extend(base_patterns)
        
        # Add date-specific patterns if we have event dates
        if change.start_date:
            event_date = change.start_date.date()
            today = datetime.now().date()
            
            if event_date == today:
                patterns.extend(["events today", "meetings today", "schedule today"])
            elif event_date == today + timedelta(days=1):
                patterns.extend(["events tomorrow", "meetings tomorrow", "schedule tomorrow"])
            
            # Week-based patterns
            if (event_date - today).days <= 7:
                patterns.extend(["events this week", "meetings this week", "schedule this week"])
            elif (event_date - today).days <= 14:
                patterns.extend(["events next week", "meetings next week", "schedule next week"])
        
        # Add contact-specific patterns if participants are involved
        if change.participants:
            for participant in change.participants:
                patterns.extend([
                    f"meetings with {participant}",
                    f"events with {participant}",
                    f"schedule with {participant}"
                ])
        
        # Add event type patterns
        if change.title:
            title_lower = change.title.lower()
            if any(word in title_lower for word in ["meeting", "call", "conference"]):
                patterns.extend(["all meetings", "meeting schedule"])
            elif any(word in title_lower for word in ["event", "appointment"]):
                patterns.extend(["all events", "event schedule"])
        
        # Remove duplicates and return
        return list(set(patterns))
    
    def _calculate_change_priority(self, change: CalendarEvent) -> float:
        """Calculate priority for a calendar change (0.0 to 1.0)."""
        base_priority = 0.5
        
        # Increase priority for changes affecting today/tomorrow
        if change.start_date:
            days_from_now = (change.start_date.date() - datetime.now().date()).days
            if days_from_now == 0:  # Today
                base_priority += 0.4
            elif days_from_now == 1:  # Tomorrow
                base_priority += 0.3
            elif days_from_now <= 7:  # This week
                base_priority += 0.2
        
        # Increase priority for changes with participants
        if change.participants:
            base_priority += 0.1
        
        # Increase priority for certain change types
        if change.change_type == CalendarChangeType.EVENT_DELETED:
            base_priority += 0.2
        elif change.change_type == CalendarChangeType.EVENT_MODIFIED:
            base_priority += 0.1
        
        return min(base_priority, 1.0)
    
    def _is_high_priority_change(self, change: CalendarEvent) -> bool:
        """Determine if a change requires immediate cache refresh."""
        priority = self._calculate_change_priority(change)
        return priority >= 0.8
    
    async def _schedule_cache_invalidation(self, range_info: CacheInvalidationRange):
        """Schedule cache invalidation for later processing."""
        range_key = f"{range_info.date_range[0]}_{range_info.date_range[1]}"
        
        # Merge with existing invalidation if present
        if range_key in self.pending_invalidations:
            existing = self.pending_invalidations[range_key]
            # Merge query patterns
            existing.query_patterns.extend(range_info.query_patterns)
            existing.query_patterns = list(set(existing.query_patterns))
            # Take higher priority
            existing.priority = max(existing.priority, range_info.priority)
            # Merge contacts
            existing.affected_contacts.extend(range_info.affected_contacts)
            existing.affected_contacts = list(set(existing.affected_contacts))
        else:
            self.pending_invalidations[range_key] = range_info
    
    async def _process_pending_invalidations(self):
        """Process all pending cache invalidations."""
        if not self.pending_invalidations:
            return
        
        # Sort by priority
        sorted_invalidations = sorted(
            self.pending_invalidations.items(),
            key=lambda x: x[1].priority,
            reverse=True
        )
        
        processed_keys = []
        
        for range_key, range_info in sorted_invalidations:
            try:
                # Check if enough time has passed since last invalidation
                if range_key in self.last_invalidation_time:
                    time_since_last = time.time() - self.last_invalidation_time[range_key]
                    if time_since_last < self.invalidation_debounce:
                        continue  # Skip, too soon
                
                # Process invalidation
                await self.trigger_intelligent_refresh(range_info.query_patterns)
                
                # Update last invalidation time
                self.last_invalidation_time[range_key] = time.time()
                processed_keys.append(range_key)
                
                self.logger.debug(f"Processed invalidation for range: {range_key}")
                
            except Exception as e:
                self.logger.error(f"Error processing invalidation {range_key}: {e}")
        
        # Remove processed invalidations
        for key in processed_keys:
            del self.pending_invalidations[key]
    
    def _group_cache_keys_by_pattern(self, cache_keys: List[str]) -> Dict[str, List[str]]:
        """Group cache keys by pattern for efficient batch processing."""
        pattern_groups = {}
        
        for key in cache_keys:
            # Extract base pattern (simplified)
            if "today" in key:
                pattern = "today"
            elif "tomorrow" in key:
                pattern = "tomorrow"
            elif "this week" in key:
                pattern = "this_week"
            elif "upcoming" in key:
                pattern = "upcoming"
            elif "meetings" in key:
                pattern = "meetings"
            elif "events" in key:
                pattern = "events"
            else:
                pattern = "general"
            
            if pattern not in pattern_groups:
                pattern_groups[pattern] = []
            pattern_groups[pattern].append(key)
        
        return pattern_groups
    
    async def _invalidate_cache_pattern(self, pattern: str):
        """Invalidate cache entries matching a pattern."""
        if hasattr(self.agent, 'semantic_cache'):
            await self.agent.semantic_cache.invalidate_cache_pattern(pattern, self.agent.agent_id)
    
    async def _prewarm_cache_pattern(self, pattern: str):
        """Pre-warm cache for a specific pattern."""
        try:
            # Generate query from pattern
            query = self._pattern_to_query(pattern)
            
            # Warm cache by executing query
            if hasattr(self.agent, 'process_natural_language_query'):
                await self.agent.process_natural_language_query(query)
                
        except Exception as e:
            self.logger.error(f"Error pre-warming pattern {pattern}: {e}")
    
    def _pattern_to_query(self, pattern: str) -> str:
        """Convert pattern to executable query."""
        pattern_queries = {
            "today": "events today",
            "tomorrow": "events tomorrow", 
            "this_week": "events this week",
            "upcoming": "upcoming events",
            "meetings": "meetings today",
            "events": "events today",
            "general": "upcoming events"
        }
        
        return pattern_queries.get(pattern, "upcoming events")
    
    async def _initialize_calendar_state(self):
        """Initialize known calendar state for change detection."""
        self.known_events = await self._fetch_current_calendar_state()
        self.last_sync_time = datetime.now()
        self.logger.info(f"Initialized calendar state with {len(self.known_events)} events")
    
    def get_monitoring_stats(self) -> Dict[str, Any]:
        """Get calendar monitoring statistics."""
        return {
            "monitoring_enabled": self.monitoring_enabled,
            "monitoring_metrics": self.monitoring_metrics.copy(),
            "recent_changes_count": len(self.recent_changes),
            "pending_invalidations": len(self.pending_invalidations),
            "known_events_count": len(self.known_events),
            "last_sync_time": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "polling_interval": self.polling_interval,
            "invalidation_debounce": self.invalidation_debounce
        }