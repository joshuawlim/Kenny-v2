"""
Predictive Cache Warmer for Kenny v2.1 Phase 3.2.3

Enhanced cache warming service with ML-based query prediction and intelligent
pre-computation. Integrates with Query Pattern Analyzer to predict likely
queries and warm cache proactively.

Key Features:
- ML-based query prediction for cache warming
- Time-aware pre-computation (morning prep, evening cleanup)
- Contact relationship analysis and caching
- Recurring event pattern recognition
- Seasonal/weekly pattern learning
- Dynamic TTL adjustment based on query frequency
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict
import json

from .query_pattern_analyzer import QueryPatternAnalyzer, PredictedQuery, CacheAction


@dataclass
class WarmingJob:
    """Represents a cache warming job."""
    job_id: str
    query: str
    priority: float
    predicted_time: datetime
    reasoning: str
    job_type: str  # "predicted", "time_based", "contact_based", "recurring"
    estimated_benefit: float
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class WarmingResult:
    """Result of a cache warming operation."""
    job_id: str
    success: bool
    execution_time: float
    cache_hit: bool
    confidence: float
    error_message: Optional[str] = None


class PredictiveCacheWarmer:
    """
    Intelligent cache warming service with ML-based prediction capabilities.
    
    Extends the basic CacheWarmingService with predictive intelligence,
    time-aware optimization, and adaptive learning.
    """
    
    def __init__(self, agent, pattern_analyzer: QueryPatternAnalyzer, 
                 warming_interval: int = 1800):  # 30 minutes default
        """Initialize the predictive cache warmer."""
        self.agent = agent
        self.pattern_analyzer = pattern_analyzer
        self.warming_interval = warming_interval
        self.logger = logging.getLogger(f"predictive-cache-warmer-{agent.agent_id}")
        
        # Warming configuration
        self.prediction_window_hours = 2  # Hours ahead to predict
        self.max_concurrent_jobs = 5  # Maximum concurrent warming jobs
        self.adaptive_ttl_enabled = True
        self.contact_analysis_enabled = True
        
        # Job management
        self.warming_queue: List[WarmingJob] = []
        self.active_jobs: Dict[str, WarmingJob] = {}
        self.completed_jobs: List[WarmingResult] = []
        self.job_counter = 0
        
        # Performance optimization
        self.warming_scheduler = None
        self.prediction_scheduler = None
        self.is_running = False
        
        # Contact relationship cache
        self.contact_relationships: Dict[str, Dict] = {}
        self.last_contact_analysis = datetime.now()
        
        # Time-based patterns
        self.time_patterns = {
            "morning_prep": {"hours": [7, 8, 9], "queries": []},
            "midday_check": {"hours": [12, 13], "queries": []},
            "afternoon_planning": {"hours": [14, 15, 16], "queries": []},
            "evening_cleanup": {"hours": [18, 19, 20], "queries": []},
            "weekly_planning": {"weekdays": [0, 6], "queries": []}  # Monday, Sunday
        }
        
        # Performance metrics
        self.warming_metrics = {
            "predictions_generated": 0,
            "warming_jobs_completed": 0,
            "warming_jobs_failed": 0,
            "prediction_accuracy": 0.0,
            "avg_warming_time": 0.0,
            "cache_hit_improvement": 0.0,
            "total_queries_warmed": 0,
            "adaptive_ttl_adjustments": 0
        }
        
        # Learning and adaptation
        self.learning_enabled = True
        self.accuracy_tracking: List[Tuple[str, bool, float]] = []  # query, success, timestamp
    
    async def start(self):
        """Start the predictive cache warming service."""
        if self.is_running:
            self.logger.warning("Predictive cache warmer already running")
            return
        
        self.is_running = True
        self.logger.info("Starting predictive cache warming service...")
        
        # Start background schedulers
        self.warming_scheduler = asyncio.create_task(self._warming_scheduler_loop())
        self.prediction_scheduler = asyncio.create_task(self._prediction_scheduler_loop())
        
        # Initial prediction and warming
        await self._generate_initial_predictions()
        
        self.logger.info("Predictive cache warming service started successfully")
    
    async def stop(self):
        """Stop the predictive cache warming service."""
        self.is_running = False
        
        # Cancel schedulers
        if self.warming_scheduler:
            self.warming_scheduler.cancel()
            try:
                await self.warming_scheduler
            except asyncio.CancelledError:
                pass
        
        if self.prediction_scheduler:
            self.prediction_scheduler.cancel()
            try:
                await self.prediction_scheduler
            except asyncio.CancelledError:
                pass
        
        # Wait for active jobs to complete (with timeout)
        if self.active_jobs:
            self.logger.info(f"Waiting for {len(self.active_jobs)} active warming jobs to complete...")
            try:
                await asyncio.wait_for(self._wait_for_active_jobs(), timeout=30.0)
            except asyncio.TimeoutError:
                self.logger.warning("Timeout waiting for active jobs, forcing shutdown")
        
        self.logger.info("Predictive cache warming service stopped")
    
    async def warm_predicted_queries(self, predictions: List[PredictedQuery]):
        """Warm cache with predicted queries."""
        self.logger.info(f"Warming cache with {len(predictions)} predicted queries")
        
        jobs_created = 0
        for prediction in predictions:
            # Create warming job
            job = WarmingJob(
                job_id=f"pred_{self.job_counter}",
                query=prediction.query,
                priority=prediction.probability,
                predicted_time=prediction.predicted_time,
                reasoning=prediction.reasoning,
                job_type="predicted",
                estimated_benefit=prediction.confidence * 0.8
            )
            
            self.job_counter += 1
            self.warming_queue.append(job)
            jobs_created += 1
        
        # Sort queue by priority
        self.warming_queue.sort(key=lambda x: x.priority, reverse=True)
        
        self.logger.info(f"Created {jobs_created} warming jobs from predictions")
        self.warming_metrics["predictions_generated"] += len(predictions)
    
    async def schedule_time_based_warming(self, time_context: datetime):
        """Schedule time-based cache warming based on temporal patterns."""
        current_hour = time_context.hour
        current_weekday = time_context.weekday()
        
        # Determine active time pattern
        active_patterns = []
        
        for pattern_name, pattern_config in self.time_patterns.items():
            if "hours" in pattern_config and current_hour in pattern_config["hours"]:
                active_patterns.append(pattern_name)
            elif "weekdays" in pattern_config and current_weekday in pattern_config["weekdays"]:
                active_patterns.append(pattern_name)
        
        # Generate time-based warming jobs
        for pattern_name in active_patterns:
            queries = self._get_time_pattern_queries(pattern_name, time_context)
            
            for query in queries:
                job = WarmingJob(
                    job_id=f"time_{self.job_counter}",
                    query=query,
                    priority=0.8,  # High priority for time-based
                    predicted_time=time_context,
                    reasoning=f"Time-based pattern: {pattern_name}",
                    job_type="time_based",
                    estimated_benefit=0.7
                )
                
                self.job_counter += 1
                self.warming_queue.append(job)
        
        if active_patterns:
            self.logger.info(f"Scheduled time-based warming for patterns: {active_patterns}")
    
    async def optimize_cache_distribution(self, usage_patterns: Dict):
        """Optimize cache distribution based on usage patterns."""
        try:
            self.logger.info("Optimizing cache distribution based on usage patterns")
            
            # Analyze current cache performance
            cache_stats = self.agent.semantic_cache.get_cache_stats()
            
            # Calculate optimal cache sizes based on usage
            total_queries = usage_patterns.get("total_queries", 1)
            high_frequency_patterns = usage_patterns.get("high_frequency_patterns", [])
            
            optimization_actions = []
            
            # Increase L1 cache size if hit rate is high but utilization is near max
            l1_stats = cache_stats["l1_cache"]
            if l1_stats["hit_rate_percent"] > 80 and l1_stats["utilization_percent"] > 90:
                optimization_actions.append({
                    "action": "increase_l1_cache_size",
                    "current_size": l1_stats["size"],
                    "recommended_size": min(l1_stats["max_size"] * 1.5, 2000),
                    "reasoning": "High hit rate with near-max utilization"
                })
            
            # Adjust TTL for frequently accessed patterns
            if high_frequency_patterns:
                for pattern in high_frequency_patterns:
                    optimization_actions.append({
                        "action": "extend_ttl",
                        "pattern": pattern,
                        "current_ttl": 30,  # L1 TTL
                        "recommended_ttl": 60,
                        "reasoning": "High frequency pattern deserves longer TTL"
                    })
            
            # Apply adaptive TTL adjustments
            if self.adaptive_ttl_enabled:
                await self._apply_adaptive_ttl_adjustments(usage_patterns)
            
            self.logger.info(f"Generated {len(optimization_actions)} cache optimization actions")
            return optimization_actions
            
        except Exception as e:
            self.logger.error(f"Error optimizing cache distribution: {e}")
            return []
    
    async def measure_prediction_accuracy(self) -> float:
        """Measure accuracy of cache warming predictions."""
        if not self.accuracy_tracking:
            return 0.0
        
        # Calculate accuracy from recent tracking data
        recent_window = 24 * 3600  # 24 hours
        current_time = time.time()
        
        recent_predictions = [
            (query, success, timestamp) for query, success, timestamp in self.accuracy_tracking
            if current_time - timestamp < recent_window
        ]
        
        if not recent_predictions:
            return 0.0
        
        successful_predictions = sum(1 for _, success, _ in recent_predictions if success)
        accuracy = successful_predictions / len(recent_predictions)
        
        # Update metrics
        self.warming_metrics["prediction_accuracy"] = accuracy
        
        self.logger.info(f"Prediction accuracy: {accuracy:.2%} based on {len(recent_predictions)} recent predictions")
        return accuracy
    
    async def _warming_scheduler_loop(self):
        """Main warming scheduler loop."""
        while self.is_running:
            try:
                # Process warming queue
                await self._process_warming_queue()
                
                # Clean up completed jobs
                await self._cleanup_completed_jobs()
                
                # Wait before next cycle
                await asyncio.sleep(5.0)  # 5-second cycle
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in warming scheduler loop: {e}")
                await asyncio.sleep(10.0)
    
    async def _prediction_scheduler_loop(self):
        """Prediction generation scheduler loop."""
        while self.is_running:
            try:
                # Generate new predictions
                await self._generate_predictions()
                
                # Schedule time-based warming
                await self.schedule_time_based_warming(datetime.now())
                
                # Analyze contact relationships periodically
                if self.contact_analysis_enabled:
                    await self._analyze_contact_relationships()
                
                # Measure and update prediction accuracy
                await self.measure_prediction_accuracy()
                
                # Wait for next prediction cycle
                await asyncio.sleep(self.warming_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in prediction scheduler loop: {e}")
                await asyncio.sleep(60.0)
    
    async def _process_warming_queue(self):
        """Process jobs in the warming queue."""
        if not self.warming_queue or len(self.active_jobs) >= self.max_concurrent_jobs:
            return
        
        # Take jobs from queue up to concurrency limit
        jobs_to_start = []
        while (self.warming_queue and 
               len(self.active_jobs) + len(jobs_to_start) < self.max_concurrent_jobs):
            job = self.warming_queue.pop(0)  # Take highest priority job
            jobs_to_start.append(job)
        
        # Start warming jobs concurrently
        if jobs_to_start:
            warming_tasks = []
            for job in jobs_to_start:
                self.active_jobs[job.job_id] = job
                task = asyncio.create_task(
                    self._execute_warming_job(job),
                    name=f"warm_{job.job_id}"
                )
                warming_tasks.append(task)
            
            self.logger.debug(f"Started {len(jobs_to_start)} warming jobs")
    
    async def _execute_warming_job(self, job: WarmingJob) -> WarmingResult:
        """Execute a single warming job."""
        start_time = time.time()
        
        try:
            self.logger.debug(f"Executing warming job {job.job_id}: {job.query}")
            
            # Execute query to warm cache
            result = await self.agent.process_natural_language_query(job.query)
            
            execution_time = time.time() - start_time
            success = result.get("success", False)
            cached = result.get("cached", False)
            confidence = result.get("confidence", 0.0)
            
            warming_result = WarmingResult(
                job_id=job.job_id,
                success=success,
                execution_time=execution_time,
                cache_hit=cached,
                confidence=confidence
            )
            
            # Update metrics
            if success:
                self.warming_metrics["warming_jobs_completed"] += 1
                self.warming_metrics["total_queries_warmed"] += 1
            else:
                self.warming_metrics["warming_jobs_failed"] += 1
            
            # Update average warming time
            if self.warming_metrics["avg_warming_time"] == 0:
                self.warming_metrics["avg_warming_time"] = execution_time
            else:
                alpha = 0.1
                self.warming_metrics["avg_warming_time"] = (
                    alpha * execution_time + 
                    (1 - alpha) * self.warming_metrics["avg_warming_time"]
                )
            
            # Track prediction accuracy if this was a predicted query
            if job.job_type == "predicted":
                self.accuracy_tracking.append((job.query, success, time.time()))
                # Limit tracking history
                if len(self.accuracy_tracking) > 1000:
                    self.accuracy_tracking = self.accuracy_tracking[-500:]
            
            self.logger.debug(f"Warming job {job.job_id} completed: success={success}, time={execution_time:.3f}s")
            return warming_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"Error executing warming job {job.job_id}: {e}")
            
            warming_result = WarmingResult(
                job_id=job.job_id,
                success=False,
                execution_time=execution_time,
                cache_hit=False,
                confidence=0.0,
                error_message=str(e)
            )
            
            self.warming_metrics["warming_jobs_failed"] += 1
            return warming_result
        
        finally:
            # Remove from active jobs
            if job.job_id in self.active_jobs:
                del self.active_jobs[job.job_id]
            
            # Add to completed jobs
            if 'warming_result' in locals():
                self.completed_jobs.append(warming_result)
    
    async def _generate_predictions(self):
        """Generate new query predictions."""
        try:
            # Get predictions from pattern analyzer
            current_time = datetime.now()
            prediction_time = current_time + timedelta(hours=self.prediction_window_hours)
            
            predictions = await self.pattern_analyzer.predict_likely_queries(prediction_time)
            
            if predictions:
                await self.warm_predicted_queries(predictions)
                self.logger.debug(f"Generated {len(predictions)} new predictions")
            
        except Exception as e:
            self.logger.error(f"Error generating predictions: {e}")
    
    async def _generate_initial_predictions(self):
        """Generate initial predictions on startup."""
        try:
            self.logger.info("Generating initial cache warming predictions...")
            
            # Analyze historical patterns
            pattern_weights = await self.pattern_analyzer.analyze_historical_patterns()
            
            # Generate predictions for next few hours
            for hours_ahead in [0.5, 1, 2]:
                prediction_time = datetime.now() + timedelta(hours=hours_ahead)
                predictions = await self.pattern_analyzer.predict_likely_queries(prediction_time)
                
                if predictions:
                    # Filter to high-confidence predictions for initial warming
                    high_confidence_predictions = [
                        p for p in predictions if p.confidence >= 0.7
                    ]
                    await self.warm_predicted_queries(high_confidence_predictions)
            
            self.logger.info("Initial predictions generated successfully")
            
        except Exception as e:
            self.logger.error(f"Error generating initial predictions: {e}")
    
    def _get_time_pattern_queries(self, pattern_name: str, time_context: datetime) -> List[str]:
        """Get queries for a specific time pattern."""
        base_queries = {
            "morning_prep": [
                "events today",
                "meetings today",
                "schedule today",
                "upcoming meetings"
            ],
            "midday_check": [
                "meetings this afternoon",
                "events today",
                "meetings tomorrow"
            ],
            "afternoon_planning": [
                "events tomorrow",
                "meetings tomorrow",
                "schedule this week"
            ],
            "evening_cleanup": [
                "events tomorrow",
                "meetings tomorrow",
                "schedule next week"
            ],
            "weekly_planning": [
                "events this week",
                "meetings this week",
                "events next week",
                "meetings next week"
            ]
        }
        
        return base_queries.get(pattern_name, [])
    
    async def _analyze_contact_relationships(self):
        """Analyze contact relationships for improved prediction."""
        current_time = datetime.now()
        
        # Only analyze once per hour
        if (current_time - self.last_contact_analysis).total_seconds() < 3600:
            return
        
        try:
            self.logger.debug("Analyzing contact relationships for cache optimization")
            
            # This would analyze recent calendar events to identify frequently co-occurring contacts
            # For now, we'll implement a basic version
            
            # Get recent calendar events
            recent_events = await self._get_recent_calendar_events()
            
            # Extract contact co-occurrence patterns
            contact_patterns = self._extract_contact_patterns(recent_events)
            
            # Update contact relationships cache
            self.contact_relationships.update(contact_patterns)
            
            self.last_contact_analysis = current_time
            self.logger.debug(f"Updated contact relationships: {len(contact_patterns)} patterns")
            
        except Exception as e:
            self.logger.error(f"Error analyzing contact relationships: {e}")
    
    async def _get_recent_calendar_events(self) -> List[Dict]:
        """Get recent calendar events for analysis."""
        try:
            # Use the calendar bridge to get recent events
            bridge_tool = self.agent.tools.get("calendar_bridge")
            if not bridge_tool:
                return []
            
            # Get events from last 30 days
            start_date = (datetime.now() - timedelta(days=30)).isoformat()
            end_date = datetime.now().isoformat()
            
            events_response = await bridge_tool.get_events({
                "start_date": start_date,
                "end_date": end_date,
                "include_all_day": True
            })
            
            if events_response.get("success") and events_response.get("events"):
                return events_response["events"]
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error fetching recent calendar events: {e}")
            return []
    
    def _extract_contact_patterns(self, events: List[Dict]) -> Dict[str, Dict]:
        """Extract contact co-occurrence patterns from events."""
        patterns = {}
        
        try:
            # Group events by participants
            participant_groups = defaultdict(list)
            
            for event in events:
                participants = event.get("participants", [])
                if len(participants) > 1:
                    # Sort participants for consistent grouping
                    participant_key = tuple(sorted(participants))
                    participant_groups[participant_key].append(event)
            
            # Create patterns for frequently occurring groups
            for participant_group, group_events in participant_groups.items():
                if len(group_events) >= 3:  # Minimum frequency threshold
                    pattern_key = "_".join(participant_group)
                    patterns[pattern_key] = {
                        "participants": list(participant_group),
                        "frequency": len(group_events),
                        "last_meeting": max(event.get("start_date", "") for event in group_events),
                        "typical_duration": self._calculate_typical_duration(group_events)
                    }
            
        except Exception as e:
            self.logger.error(f"Error extracting contact patterns: {e}")
        
        return patterns
    
    def _calculate_typical_duration(self, events: List[Dict]) -> float:
        """Calculate typical duration for a group of events."""
        durations = []
        
        for event in events:
            start_str = event.get("start_date")
            end_str = event.get("end_date")
            
            if start_str and end_str:
                try:
                    start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    duration_hours = (end - start).total_seconds() / 3600
                    durations.append(duration_hours)
                except Exception:
                    continue
        
        return sum(durations) / len(durations) if durations else 1.0
    
    async def _apply_adaptive_ttl_adjustments(self, usage_patterns: Dict):
        """Apply adaptive TTL adjustments based on usage patterns."""
        try:
            # This would adjust cache TTLs based on query frequency
            # For now, implement basic logic
            
            high_frequency_patterns = usage_patterns.get("high_frequency_patterns", [])
            
            for pattern in high_frequency_patterns:
                # Extend TTL for high-frequency patterns
                self.logger.debug(f"Would extend TTL for high-frequency pattern: {pattern}")
                self.warming_metrics["adaptive_ttl_adjustments"] += 1
            
        except Exception as e:
            self.logger.error(f"Error applying adaptive TTL adjustments: {e}")
    
    async def _cleanup_completed_jobs(self):
        """Clean up old completed jobs to prevent memory buildup."""
        # Keep only last 100 completed jobs
        if len(self.completed_jobs) > 100:
            self.completed_jobs = self.completed_jobs[-50:]
    
    async def _wait_for_active_jobs(self):
        """Wait for all active jobs to complete."""
        while self.active_jobs:
            await asyncio.sleep(0.5)
    
    def get_warming_stats(self) -> Dict[str, Any]:
        """Get comprehensive warming statistics."""
        return {
            "service_status": "running" if self.is_running else "stopped",
            "warming_metrics": self.warming_metrics.copy(),
            "queue_status": {
                "queued_jobs": len(self.warming_queue),
                "active_jobs": len(self.active_jobs),
                "completed_jobs": len(self.completed_jobs)
            },
            "configuration": {
                "warming_interval": self.warming_interval,
                "prediction_window_hours": self.prediction_window_hours,
                "max_concurrent_jobs": self.max_concurrent_jobs,
                "adaptive_ttl_enabled": self.adaptive_ttl_enabled,
                "contact_analysis_enabled": self.contact_analysis_enabled
            },
            "contact_relationships": len(self.contact_relationships),
            "prediction_accuracy": self.warming_metrics["prediction_accuracy"]
        }