"""
Database Integration Layer for Phase 3.5 Calendar Database

Seamlessly integrates SQLite database with Phase 3.2 multi-tier caching system
to provide hybrid performance with database persistence and cache speed.

Integration Strategy:
- Database as L4 cache: Persistent storage with L1/L2/L3 integration
- Cache-first reads: Check L1 → L2 → L3 → Database → API
- Write-through strategy: Update Database + invalidate relevant caches
- Predictive warming: Database-aware cache warming based on query patterns
- Fallback safety: Maintain Phase 3.2 performance as backup
"""

import asyncio
import time
import logging
import json
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass, asdict

from calendar_database import CalendarDatabase, CalendarEvent, DatabaseConfig
from kenny_agent.semantic_cache import SemanticCache
from kenny_agent.cache_warming_service import CacheWarmingService
from kenny_agent.intelligent_cache_orchestrator import IntelligentCacheOrchestrator

logger = logging.getLogger("database_integration")


@dataclass
class IntegrationConfig:
    """Configuration for database-cache integration."""
    enable_database: bool = True
    database_first: bool = True  # Query database before API
    cache_write_through: bool = True  # Update cache on database writes
    cache_invalidation: bool = True  # Invalidate cache on database changes
    fallback_to_phase32: bool = True  # Fallback to Phase 3.2 on database errors
    performance_monitoring: bool = True
    sync_interval_seconds: int = 300  # 5 minutes


class DatabaseCacheIntegration:
    """
    Advanced integration layer between SQLite database and Phase 3.2 caching.
    
    Provides hybrid performance by combining:
    - Database persistence and complex queries
    - Multi-tier cache speed (L1/L2/L3)
    - Intelligent cache warming and invalidation
    - Seamless fallback to Phase 3.2 performance
    """
    
    def __init__(self, 
                 database: CalendarDatabase,
                 semantic_cache: SemanticCache,
                 cache_warming_service: CacheWarmingService,
                 cache_orchestrator: IntelligentCacheOrchestrator,
                 config: IntegrationConfig = None):
        """Initialize database-cache integration."""
        self.database = database
        self.semantic_cache = semantic_cache
        self.cache_warming_service = cache_warming_service
        self.cache_orchestrator = cache_orchestrator
        self.config = config or IntegrationConfig()
        
        # Performance tracking
        self.integration_metrics = {
            "cache_hits": 0,
            "database_hits": 0,
            "api_fallbacks": 0,
            "write_throughs": 0,
            "invalidations": 0,
            "total_operations": 0,
            "avg_response_time": 0.0
        }
        
        # Cache invalidation tracking
        self.pending_invalidations = set()
        self.invalidation_lock = asyncio.Lock()
        
        logger.info("Database-cache integration initialized")
    
    async def get_event(self, event_id: str, use_cache: bool = True) -> Optional[CalendarEvent]:
        """
        Get event using hybrid cache-database strategy.
        
        Query order: L1 Cache → L2 Cache → L3 Cache → Database → API
        """
        start_time = time.time()
        operation_path = []
        
        try:
            self.integration_metrics["total_operations"] += 1
            
            # 1. Try L1/L2/L3 cache first (if enabled)
            if use_cache:
                cache_key = f"event:{event_id}"
                cached_result = await self.semantic_cache.get(cache_key)
                
                if cached_result:
                    operation_path.append("cache_hit")
                    self.integration_metrics["cache_hits"] += 1
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Cache hit for event {event_id} in {execution_time:.3f}s")
                    return CalendarEvent(**cached_result) if isinstance(cached_result, dict) else cached_result
            
            # 2. Try database (L4 cache)
            if self.config.enable_database and self.database.is_initialized:
                operation_path.append("database_query")
                db_event = await self.database.get_event(event_id)
                
                if db_event:
                    self.integration_metrics["database_hits"] += 1
                    
                    # Update cache with database result
                    if use_cache:
                        await self._cache_event_result(f"event:{event_id}", db_event)
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Database hit for event {event_id} in {execution_time:.3f}s")
                    return db_event
            
            # 3. Fallback to API (Phase 3.2 behavior)
            operation_path.append("api_fallback")
            self.integration_metrics["api_fallbacks"] += 1
            
            # This would call the original calendar bridge
            # For now, return None to indicate not found
            execution_time = time.time() - start_time
            await self._update_performance_metrics(execution_time)
            
            logger.debug(f"Event {event_id} not found, path: {' → '.join(operation_path)}")
            return None
            
        except Exception as e:
            logger.error(f"Error in hybrid get_event for {event_id}: {e}", exc_info=True)
            
            # Fallback to Phase 3.2 cache-only behavior
            if use_cache and self.config.fallback_to_phase32:
                try:
                    cache_key = f"event:{event_id}"
                    cached_result = await self.semantic_cache.get(cache_key)
                    if cached_result:
                        return CalendarEvent(**cached_result) if isinstance(cached_result, dict) else cached_result
                except:
                    pass
            
            return None
    
    async def create_event(self, event_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """
        Create event with write-through caching strategy.
        
        Strategy: Database Write → Cache Update → Cache Warming
        """
        start_time = time.time()
        
        try:
            self.integration_metrics["total_operations"] += 1
            
            # 1. Create in database first (master data store)
            if self.config.enable_database and self.database.is_initialized:
                db_event = await self.database.create_event(event_data)
                
                if db_event:
                    # 2. Write-through to cache
                    if self.config.cache_write_through:
                        await self._write_through_cache(db_event)
                        self.integration_metrics["write_throughs"] += 1
                    
                    # 3. Invalidate related caches
                    if self.config.cache_invalidation:
                        await self._invalidate_related_caches("event_created", asdict(db_event))
                    
                    # 4. Trigger predictive cache warming
                    await self._trigger_predictive_warming("event_created", asdict(db_event))
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Created event {db_event.id} in {execution_time:.3f}s")
                    return db_event
            
            # Fallback: return None or throw exception
            logger.warning("Database not available for event creation")
            return None
            
        except Exception as e:
            logger.error(f"Error creating event: {e}", exc_info=True)
            return None
    
    async def update_event(self, event_id: str, update_data: Dict[str, Any]) -> Optional[CalendarEvent]:
        """
        Update event with cache invalidation and warming.
        
        Strategy: Database Update → Cache Invalidation → Selective Cache Update
        """
        start_time = time.time()
        
        try:
            self.integration_metrics["total_operations"] += 1
            
            # 1. Update in database
            if self.config.enable_database and self.database.is_initialized:
                updated_event = await self.database.update_event(event_id, update_data)
                
                if updated_event:
                    # 2. Invalidate specific cache entries
                    if self.config.cache_invalidation:
                        await self._invalidate_event_caches(event_id)
                        await self._invalidate_related_caches("event_updated", asdict(updated_event))
                    
                    # 3. Update cache with new data (selective update)
                    if self.config.cache_write_through:
                        await self._write_through_cache(updated_event)
                        self.integration_metrics["write_throughs"] += 1
                    
                    # 4. Warm related caches
                    await self._trigger_predictive_warming("event_updated", asdict(updated_event))
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Updated event {event_id} in {execution_time:.3f}s")
                    return updated_event
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating event {event_id}: {e}", exc_info=True)
            return None
    
    async def delete_event(self, event_id: str) -> bool:
        """
        Delete event with comprehensive cache cleanup.
        
        Strategy: Database Delete → Cache Invalidation → Related Cache Cleanup
        """
        start_time = time.time()
        
        try:
            self.integration_metrics["total_operations"] += 1
            
            # Get event data before deletion for cache cleanup
            event_to_delete = await self.get_event(event_id, use_cache=False)
            
            # 1. Delete from database
            if self.config.enable_database and self.database.is_initialized:
                success = await self.database.delete_event(event_id)
                
                if success:
                    # 2. Remove from all cache layers
                    await self._invalidate_event_caches(event_id)
                    
                    # 3. Invalidate related caches (list queries, etc.)
                    if event_to_delete and self.config.cache_invalidation:
                        await self._invalidate_related_caches("event_deleted", asdict(event_to_delete))
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Deleted event {event_id} in {execution_time:.3f}s")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting event {event_id}: {e}", exc_info=True)
            return False
    
    async def list_events(self, 
                         calendar_id: Optional[str] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         limit: int = 100,
                         use_cache: bool = True) -> List[CalendarEvent]:
        """
        List events with intelligent cache-database coordination.
        
        Strategy: Smart Cache Check → Database Query → Result Caching
        """
        start_time = time.time()
        
        try:
            self.integration_metrics["total_operations"] += 1
            
            # Generate cache key for this list query
            list_cache_key = self._generate_list_cache_key(
                calendar_id, start_date, end_date, limit
            )
            
            # 1. Try cache first (if enabled and not bypassed)
            if use_cache:
                cached_result = await self.semantic_cache.get(list_cache_key)
                if cached_result:
                    self.integration_metrics["cache_hits"] += 1
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Cache hit for list query in {execution_time:.3f}s")
                    return [CalendarEvent(**event_data) for event_data in cached_result]
            
            # 2. Query database
            if self.config.enable_database and self.database.is_initialized:
                events = await self.database.list_events(
                    calendar_id=calendar_id,
                    start_date=start_date,
                    end_date=end_date,
                    limit=limit
                )
                
                self.integration_metrics["database_hits"] += 1
                
                # 3. Cache the results
                if use_cache and events:
                    events_data = [asdict(event) for event in events]
                    await self.semantic_cache.set(
                        list_cache_key, 
                        events_data, 
                        ttl=300  # 5 minutes for list queries
                    )
                
                execution_time = time.time() - start_time
                await self._update_performance_metrics(execution_time)
                
                logger.debug(f"Database list query returned {len(events)} events in {execution_time:.3f}s")
                return events
            
            # 3. Fallback to API (Phase 3.2 behavior)
            self.integration_metrics["api_fallbacks"] += 1
            return []
            
        except Exception as e:
            logger.error(f"Error in list_events: {e}", exc_info=True)
            return []
    
    async def search_events(self, query: str, limit: int = 50, use_cache: bool = True) -> List[CalendarEvent]:
        """
        Search events with FTS database optimization and caching.
        
        Strategy: Cache Check → Database FTS → Result Caching
        """
        start_time = time.time()
        
        try:
            self.integration_metrics["total_operations"] += 1
            
            # Generate cache key for search query
            search_cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}:{limit}"
            
            # 1. Try cache first
            if use_cache:
                cached_result = await self.semantic_cache.get(search_cache_key)
                if cached_result:
                    self.integration_metrics["cache_hits"] += 1
                    
                    execution_time = time.time() - start_time
                    await self._update_performance_metrics(execution_time)
                    
                    logger.debug(f"Cache hit for search '{query}' in {execution_time:.3f}s")
                    return [CalendarEvent(**event_data) for event_data in cached_result]
            
            # 2. Use database FTS search
            if self.config.enable_database and self.database.is_initialized:
                events = await self.database.search_events(query, limit)
                
                self.integration_metrics["database_hits"] += 1
                
                # 3. Cache search results
                if use_cache and events:
                    events_data = [asdict(event) for event in events]
                    await self.semantic_cache.set(
                        search_cache_key, 
                        events_data, 
                        ttl=600  # 10 minutes for search results
                    )
                
                execution_time = time.time() - start_time
                await self._update_performance_metrics(execution_time)
                
                logger.debug(f"Database search for '{query}' returned {len(events)} events in {execution_time:.3f}s")
                return events
            
            return []
            
        except Exception as e:
            logger.error(f"Error in search_events: {e}", exc_info=True)
            return []
    
    async def _write_through_cache(self, event: CalendarEvent):
        """Write event data through to all cache layers."""
        try:
            cache_key = f"event:{event.id}"
            event_data = asdict(event)
            
            # Write to cache with appropriate TTL
            await self.semantic_cache.set(cache_key, event_data, ttl=1800)  # 30 minutes
            
            logger.debug(f"Write-through cache update for event {event.id}")
            
        except Exception as e:
            logger.error(f"Write-through cache failed for event {event.id}: {e}")
    
    async def _invalidate_event_caches(self, event_id: str):
        """Invalidate all cache entries related to a specific event."""
        try:
            async with self.invalidation_lock:
                # Direct event cache
                cache_key = f"event:{event_id}"
                await self.semantic_cache.delete(cache_key)
                
                self.integration_metrics["invalidations"] += 1
                
                logger.debug(f"Invalidated cache for event {event_id}")
                
        except Exception as e:
            logger.error(f"Cache invalidation failed for event {event_id}: {e}")
    
    async def _invalidate_related_caches(self, operation: str, event_data: Dict[str, Any]):
        """Invalidate caches related to the modified event."""
        try:
            async with self.invalidation_lock:
                invalidation_patterns = []
                
                # Calendar-based invalidations
                if "calendar_id" in event_data:
                    invalidation_patterns.extend([
                        f"list:calendar:{event_data['calendar_id']}*",
                        f"search:*",  # Search results may be affected
                        f"calendar_events:*"  # General calendar event lists
                    ])
                
                # Date-based invalidations
                if "start_time" in event_data:
                    try:
                        start_date = datetime.fromisoformat(event_data["start_time"].replace('Z', '+00:00'))
                        date_key = start_date.strftime("%Y-%m-%d")
                        invalidation_patterns.append(f"list:date:{date_key}*")
                    except:
                        pass
                
                # Apply invalidations
                for pattern in invalidation_patterns:
                    await self.semantic_cache.delete_pattern(pattern)
                    self.integration_metrics["invalidations"] += 1
                
                logger.debug(f"Invalidated {len(invalidation_patterns)} cache patterns for {operation}")
                
        except Exception as e:
            logger.error(f"Related cache invalidation failed: {e}")
    
    async def _trigger_predictive_warming(self, operation: str, event_data: Dict[str, Any]):
        """Trigger predictive cache warming based on the operation."""
        try:
            if not hasattr(self, 'cache_orchestrator') or not self.cache_orchestrator:
                return
            
            # Warm likely queries based on the operation
            warming_queries = []
            
            if operation in ["event_created", "event_updated"]:
                # Warm calendar view for the event's calendar
                if "calendar_id" in event_data:
                    warming_queries.extend([
                        f"events today in {event_data['calendar_id']}",
                        f"upcoming events in {event_data['calendar_id']}",
                        "events this week"
                    ])
                
                # Warm search for event title
                if "title" in event_data:
                    title_words = event_data["title"].split()[:2]  # First two words
                    if title_words:
                        warming_queries.append(" ".join(title_words))
            
            # Execute warming queries in background
            for query in warming_queries:
                asyncio.create_task(
                    self._background_cache_warm(query),
                    name=f"warm_{operation}_{hash(query)}"
                )
                
        except Exception as e:
            logger.warning(f"Predictive warming failed: {e}")
    
    async def _background_cache_warm(self, query: str):
        """Background task for cache warming."""
        try:
            # This would trigger a query to warm the cache
            # Implementation depends on integration with cache warming service
            if hasattr(self, 'cache_warming_service') and self.cache_warming_service:
                await self.cache_warming_service.warm_query_pattern(query)
        except Exception as e:
            logger.debug(f"Background cache warming failed for '{query}': {e}")
    
    def _generate_list_cache_key(self, 
                                calendar_id: Optional[str],
                                start_date: Optional[datetime],
                                end_date: Optional[datetime],
                                limit: int) -> str:
        """Generate cache key for list queries."""
        key_parts = ["list"]
        
        if calendar_id:
            key_parts.append(f"calendar:{calendar_id}")
        
        if start_date:
            key_parts.append(f"start:{start_date.isoformat()}")
        
        if end_date:
            key_parts.append(f"end:{end_date.isoformat()}")
        
        key_parts.append(f"limit:{limit}")
        
        return ":".join(key_parts)
    
    async def _cache_event_result(self, cache_key: str, event: CalendarEvent):
        """Cache an event result with appropriate TTL."""
        try:
            event_data = asdict(event)
            await self.semantic_cache.set(cache_key, event_data, ttl=1800)  # 30 minutes
        except Exception as e:
            logger.warning(f"Failed to cache event result: {e}")
    
    async def _update_performance_metrics(self, execution_time: float):
        """Update integration performance metrics."""
        try:
            # Update running average
            total_ops = self.integration_metrics["total_operations"]
            current_avg = self.integration_metrics["avg_response_time"]
            
            new_avg = ((current_avg * (total_ops - 1)) + execution_time) / total_ops
            self.integration_metrics["avg_response_time"] = new_avg
            
        except Exception as e:
            logger.warning(f"Failed to update performance metrics: {e}")
    
    def get_integration_stats(self) -> Dict[str, Any]:
        """Get comprehensive integration performance statistics."""
        try:
            total_ops = self.integration_metrics["total_operations"]
            
            if total_ops == 0:
                return {"error": "No operations recorded"}
            
            cache_hit_rate = (self.integration_metrics["cache_hits"] / total_ops) * 100
            database_hit_rate = (self.integration_metrics["database_hits"] / total_ops) * 100
            api_fallback_rate = (self.integration_metrics["api_fallbacks"] / total_ops) * 100
            
            return {
                "integration_performance": {
                    "total_operations": total_ops,
                    "avg_response_time": self.integration_metrics["avg_response_time"],
                    "cache_hit_rate": cache_hit_rate,
                    "database_hit_rate": database_hit_rate,
                    "api_fallback_rate": api_fallback_rate,
                    "performance_target_met": self.integration_metrics["avg_response_time"] < 5.0
                },
                "cache_efficiency": {
                    "cache_hits": self.integration_metrics["cache_hits"],
                    "database_hits": self.integration_metrics["database_hits"],
                    "api_fallbacks": self.integration_metrics["api_fallbacks"],
                    "write_throughs": self.integration_metrics["write_throughs"],
                    "invalidations": self.integration_metrics["invalidations"]
                },
                "hybrid_strategy": {
                    "database_enabled": self.config.enable_database,
                    "database_first": self.config.database_first,
                    "cache_write_through": self.config.cache_write_through,
                    "cache_invalidation": self.config.cache_invalidation,
                    "fallback_enabled": self.config.fallback_to_phase32
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get integration stats: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check for database-cache integration."""
        health_status = {
            "integration_healthy": True,
            "components": {},
            "performance": {},
            "recommendations": []
        }
        
        try:
            # Check database health
            if self.config.enable_database:
                db_healthy = self.database.is_initialized
                health_status["components"]["database"] = {
                    "healthy": db_healthy,
                    "initialized": self.database.is_initialized
                }
                
                if db_healthy:
                    db_stats = await self.database.get_performance_stats()
                    health_status["components"]["database"]["performance"] = db_stats
            
            # Check cache health
            if hasattr(self.semantic_cache, 'get_cache_stats'):
                cache_stats = self.semantic_cache.get_cache_stats()
                health_status["components"]["cache"] = {
                    "healthy": True,
                    "stats": cache_stats
                }
            
            # Integration performance
            integration_stats = self.get_integration_stats()
            health_status["performance"] = integration_stats
            
            # Health recommendations
            avg_time = self.integration_metrics.get("avg_response_time", 0)
            if avg_time > 5.0:
                health_status["recommendations"].append(
                    f"Average response time ({avg_time:.3f}s) exceeds 5s target"
                )
            
            cache_hit_rate = (self.integration_metrics.get("cache_hits", 0) / 
                            max(1, self.integration_metrics.get("total_operations", 1))) * 100
            if cache_hit_rate < 70:
                health_status["recommendations"].append(
                    f"Cache hit rate ({cache_hit_rate:.1f}%) below optimal 70%"
                )
            
            # Overall health
            health_status["integration_healthy"] = (
                avg_time < 5.0 and 
                cache_hit_rate > 50 and
                len(health_status["recommendations"]) == 0
            )
            
            return health_status
            
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            health_status["integration_healthy"] = False
            health_status["error"] = str(e)
            return health_status