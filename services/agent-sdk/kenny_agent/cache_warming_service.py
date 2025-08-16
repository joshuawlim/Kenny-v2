"""
Cache Warming Service for Kenny v2.1

Background service for pre-computing and warming cache with common calendar queries
and popular contact resolutions to improve response times.

Key Features:
- Pre-computed calendar views (today, this week, upcoming)
- Background cache warming based on usage patterns
- Intelligent cache invalidation triggers
- Performance monitoring for cache effectiveness
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import logging


class CacheWarmingService:
    """Background service for intelligent cache warming and pre-computation."""
    
    def __init__(self, agent, warming_interval: int = 3600):
        """
        Initialize cache warming service.
        
        Args:
            agent: The agent instance to warm cache for
            warming_interval: Interval in seconds between warming cycles (default 1 hour)
        """
        self.agent = agent
        self.warming_interval = warming_interval
        self.logger = logging.getLogger(f"cache-warming-{agent.agent_id}")
        self.logger.setLevel(logging.INFO)
        
        self.is_running = False
        self.warming_task = None
        
        # Common calendar query patterns for warming
        self.calendar_warming_patterns = [
            "events today",
            "meetings today", 
            "schedule today",
            "events this week",
            "meetings this week",
            "schedule this week",
            "upcoming events",
            "upcoming meetings",
            "events tomorrow",
            "meetings tomorrow",
            "events next week",
            "meetings next week"
        ]
        
        # Performance metrics
        self.warming_metrics = {
            "warming_cycles": 0,
            "patterns_warmed": 0,
            "warming_errors": 0,
            "last_warming_time": None,
            "avg_warming_duration": 0.0
        }
    
    async def start(self):
        """Start the background cache warming service."""
        if self.is_running:
            self.logger.warning("Cache warming service already running")
            return
        
        self.is_running = True
        self.warming_task = asyncio.create_task(self._warming_loop())
        self.logger.info(f"Cache warming service started with {self.warming_interval}s interval")
    
    async def stop(self):
        """Stop the background cache warming service."""
        self.is_running = False
        if self.warming_task:
            self.warming_task.cancel()
            try:
                await self.warming_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Cache warming service stopped")
    
    async def _warming_loop(self):
        """Main warming loop that runs in the background."""
        while self.is_running:
            try:
                await self._perform_warming_cycle()
                await asyncio.sleep(self.warming_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in warming loop: {e}")
                self.warming_metrics["warming_errors"] += 1
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def _perform_warming_cycle(self):
        """Perform a single cache warming cycle."""
        start_time = time.time()
        self.logger.info("Starting cache warming cycle")
        
        try:
            # Warm calendar patterns
            await self._warm_calendar_patterns()
            
            # Warm contact patterns if contacts agent is available
            await self._warm_contact_patterns()
            
            # Update metrics
            duration = time.time() - start_time
            self.warming_metrics["warming_cycles"] += 1
            self.warming_metrics["last_warming_time"] = datetime.now()
            
            # Update average duration with exponential moving average
            if self.warming_metrics["avg_warming_duration"] == 0:
                self.warming_metrics["avg_warming_duration"] = duration
            else:
                alpha = 0.1
                self.warming_metrics["avg_warming_duration"] = (
                    alpha * duration + 
                    (1 - alpha) * self.warming_metrics["avg_warming_duration"]
                )
            
            self.logger.info(f"Cache warming cycle completed in {duration:.2f}s")
            
        except Exception as e:
            self.logger.error(f"Error in warming cycle: {e}")
            self.warming_metrics["warming_errors"] += 1
    
    async def _warm_calendar_patterns(self):
        """Warm cache with common calendar query patterns."""
        self.logger.info("Warming calendar cache patterns")
        
        for pattern in self.calendar_warming_patterns:
            try:
                # Use the agent's process_natural_language_query to warm the cache
                if hasattr(self.agent, 'process_natural_language_query'):
                    await self.agent.process_natural_language_query(pattern)
                    self.warming_metrics["patterns_warmed"] += 1
                    self.logger.debug(f"Warmed cache for pattern: {pattern}")
                    
                    # Small delay to avoid overwhelming the system
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                self.logger.error(f"Error warming pattern '{pattern}': {e}")
                self.warming_metrics["warming_errors"] += 1
    
    async def _warm_contact_patterns(self):
        """Warm cache with common contact resolution patterns."""
        # This would warm common contact queries if contacts agent is available
        # For now, we'll skip this as it requires cross-agent communication
        self.logger.debug("Contact pattern warming skipped (requires cross-agent integration)")
    
    async def force_warm_pattern(self, pattern: str):
        """Force warm cache for a specific pattern immediately."""
        self.logger.info(f"Force warming pattern: {pattern}")
        try:
            if hasattr(self.agent, 'process_natural_language_query'):
                await self.agent.process_natural_language_query(pattern)
                self.warming_metrics["patterns_warmed"] += 1
                self.logger.info(f"Successfully warmed pattern: {pattern}")
        except Exception as e:
            self.logger.error(f"Error force warming pattern '{pattern}': {e}")
            self.warming_metrics["warming_errors"] += 1
    
    async def warm_time_based_patterns(self):
        """Warm cache with time-sensitive patterns based on current time."""
        current_hour = datetime.now().hour
        current_day = datetime.now().strftime("%A").lower()
        
        # Morning patterns (6 AM - 12 PM)
        if 6 <= current_hour < 12:
            morning_patterns = [
                "meetings today",
                "schedule today", 
                "events this morning",
                "upcoming meetings"
            ]
            for pattern in morning_patterns:
                await self.force_warm_pattern(pattern)
        
        # Afternoon patterns (12 PM - 6 PM)
        elif 12 <= current_hour < 18:
            afternoon_patterns = [
                "meetings this afternoon",
                "events today",
                "meetings tomorrow",
                "schedule tomorrow"
            ]
            for pattern in afternoon_patterns:
                await self.force_warm_pattern(pattern)
        
        # Evening patterns (6 PM - 10 PM)
        elif 18 <= current_hour < 22:
            evening_patterns = [
                "events tomorrow",
                "meetings tomorrow",
                "schedule this week",
                "upcoming events"
            ]
            for pattern in evening_patterns:
                await self.force_warm_pattern(pattern)
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get cache warming performance statistics."""
        return {
            "service_status": "running" if self.is_running else "stopped",
            "warming_interval_seconds": self.warming_interval,
            "patterns_count": len(self.calendar_warming_patterns),
            "metrics": self.warming_metrics.copy(),
            "next_warming_eta": (
                self.warming_interval - 
                (time.time() - self.warming_metrics.get("last_warming_time", datetime.now()).timestamp())
            ) if self.warming_metrics.get("last_warming_time") else 0
        }
    
    async def invalidate_time_sensitive_cache(self):
        """Invalidate cache entries that are time-sensitive."""
        time_patterns = ["today", "tomorrow", "this week", "next week", "upcoming"]
        
        for pattern in time_patterns:
            if hasattr(self.agent, 'semantic_cache'):
                await self.agent.semantic_cache.invalidate_cache_pattern(pattern, self.agent.agent_id)
        
        self.logger.info("Invalidated time-sensitive cache entries")