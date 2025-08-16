import time
import asyncio
import logging
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import statistics

logger = logging.getLogger(__name__)

@dataclass
class MetricEvent:
    """Individual performance metric event"""
    timestamp: float
    event_type: str  # "request_start", "request_end", "model_switch", "cache_hit", "error"
    model_name: str
    query: str
    response_time: Optional[float] = None
    confidence: Optional[float] = None
    accuracy: Optional[float] = None
    cache_hit: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class PerformanceSnapshot:
    """Performance metrics snapshot"""
    timestamp: float
    total_requests: int
    avg_response_time: float
    p95_response_time: float
    p99_response_time: float
    success_rate: float
    cache_hit_rate: float
    model_distribution: Dict[str, int]
    error_rate: float
    active_model: str

class PerformanceMetrics:
    """Real-time performance metrics collection and analysis"""
    
    def __init__(self, max_events: int = 10000, window_minutes: int = 60):
        self.max_events = max_events
        self.window_minutes = window_minutes
        self.events: List[MetricEvent] = []
        self.active_requests: Dict[str, MetricEvent] = {}
        
        # Performance targets
        self.target_response_time = 5.0  # seconds
        self.target_success_rate = 0.95
        self.target_cache_hit_rate = 0.80
        
        # Current state
        self.current_model = "qwen3:8b"  # Default
        
    def start_request(self, request_id: str, model_name: str, query: str, **metadata) -> None:
        """Record the start of a request"""
        event = MetricEvent(
            timestamp=time.time(),
            event_type="request_start",
            model_name=model_name,
            query=query,
            metadata=metadata
        )
        
        self.active_requests[request_id] = event
        self._add_event(event)
        
    def end_request(self, request_id: str, success: bool = True, confidence: Optional[float] = None, 
                   accuracy: Optional[float] = None, cache_hit: bool = False, error: Optional[str] = None) -> None:
        """Record the end of a request"""
        if request_id not in self.active_requests:
            logger.warning(f"End request called for unknown request_id: {request_id}")
            return
        
        start_event = self.active_requests.pop(request_id)
        response_time = time.time() - start_event.timestamp
        
        event = MetricEvent(
            timestamp=time.time(),
            event_type="request_end",
            model_name=start_event.model_name,
            query=start_event.query,
            response_time=response_time,
            confidence=confidence,
            accuracy=accuracy,
            cache_hit=cache_hit,
            error=error if not success else None,
            metadata=start_event.metadata
        )
        
        self._add_event(event)
        
    def record_model_switch(self, from_model: str, to_model: str, reason: str) -> None:
        """Record a model switch event"""
        event = MetricEvent(
            timestamp=time.time(),
            event_type="model_switch",
            model_name=to_model,
            query="",
            metadata={
                "from_model": from_model,
                "to_model": to_model,
                "reason": reason
            }
        )
        
        self.current_model = to_model
        self._add_event(event)
        
    def _add_event(self, event: MetricEvent) -> None:
        """Add event to the metrics collection"""
        self.events.append(event)
        
        # Cleanup old events if we exceed max_events
        if len(self.events) > self.max_events:
            # Remove oldest 10% of events
            remove_count = self.max_events // 10
            self.events = self.events[remove_count:]
            
    def get_current_snapshot(self) -> PerformanceSnapshot:
        """Get current performance snapshot"""
        now = time.time()
        window_start = now - (self.window_minutes * 60)
        
        # Filter events within the time window
        recent_events = [
            e for e in self.events 
            if e.timestamp >= window_start and e.event_type == "request_end"
        ]
        
        if not recent_events:
            return PerformanceSnapshot(
                timestamp=now,
                total_requests=0,
                avg_response_time=0.0,
                p95_response_time=0.0,
                p99_response_time=0.0,
                success_rate=1.0,
                cache_hit_rate=0.0,
                model_distribution={},
                error_rate=0.0,
                active_model=self.current_model
            )
        
        # Calculate metrics
        total_requests = len(recent_events)
        response_times = [e.response_time for e in recent_events if e.response_time is not None]
        successful_requests = [e for e in recent_events if e.error is None]
        cache_hits = [e for e in recent_events if e.cache_hit]
        
        avg_response_time = statistics.mean(response_times) if response_times else 0.0
        p95_response_time = self._percentile(response_times, 0.95) if response_times else 0.0
        p99_response_time = self._percentile(response_times, 0.99) if response_times else 0.0
        
        success_rate = len(successful_requests) / total_requests if total_requests > 0 else 1.0
        cache_hit_rate = len(cache_hits) / total_requests if total_requests > 0 else 0.0
        error_rate = 1.0 - success_rate
        
        # Model distribution
        model_distribution = {}
        for event in recent_events:
            model = event.model_name
            model_distribution[model] = model_distribution.get(model, 0) + 1
        
        return PerformanceSnapshot(
            timestamp=now,
            total_requests=total_requests,
            avg_response_time=avg_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            success_rate=success_rate,
            cache_hit_rate=cache_hit_rate,
            model_distribution=model_distribution,
            error_rate=error_rate,
            active_model=self.current_model
        )
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        index = int(percentile * len(sorted_values))
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def is_performance_degraded(self) -> Dict[str, bool]:
        """Check if performance has degraded below targets"""
        snapshot = self.get_current_snapshot()
        
        return {
            "response_time_exceeded": snapshot.avg_response_time > self.target_response_time,
            "success_rate_low": snapshot.success_rate < self.target_success_rate,
            "cache_hit_rate_low": snapshot.cache_hit_rate < self.target_cache_hit_rate,
            "p95_response_time_high": snapshot.p95_response_time > (self.target_response_time * 1.5)
        }
    
    def get_model_performance_comparison(self) -> Dict[str, Dict[str, float]]:
        """Compare performance across different models"""
        now = time.time()
        window_start = now - (self.window_minutes * 60)
        
        recent_events = [
            e for e in self.events 
            if e.timestamp >= window_start and e.event_type == "request_end"
        ]
        
        model_stats = {}
        
        for event in recent_events:
            model = event.model_name
            if model not in model_stats:
                model_stats[model] = {
                    "response_times": [],
                    "success_count": 0,
                    "total_count": 0,
                    "cache_hits": 0,
                    "accuracies": []
                }
            
            stats = model_stats[model]
            stats["total_count"] += 1
            
            if event.response_time is not None:
                stats["response_times"].append(event.response_time)
            
            if event.error is None:
                stats["success_count"] += 1
                
            if event.cache_hit:
                stats["cache_hits"] += 1
                
            if event.accuracy is not None:
                stats["accuracies"].append(event.accuracy)
        
        # Calculate aggregated metrics for each model
        comparison = {}
        for model, stats in model_stats.items():
            comparison[model] = {
                "avg_response_time": statistics.mean(stats["response_times"]) if stats["response_times"] else 0.0,
                "success_rate": stats["success_count"] / stats["total_count"] if stats["total_count"] > 0 else 0.0,
                "cache_hit_rate": stats["cache_hits"] / stats["total_count"] if stats["total_count"] > 0 else 0.0,
                "avg_accuracy": statistics.mean(stats["accuracies"]) if stats["accuracies"] else 0.0,
                "total_requests": stats["total_count"],
                "p95_response_time": self._percentile(stats["response_times"], 0.95) if stats["response_times"] else 0.0
            }
        
        return comparison
    
    def get_performance_trends(self, hours: int = 24) -> Dict[str, List[Dict[str, Any]]]:
        """Get performance trends over time"""
        now = time.time()
        start_time = now - (hours * 3600)
        
        # Create hourly buckets
        buckets = []
        bucket_size = 3600  # 1 hour
        
        for i in range(hours):
            bucket_start = start_time + (i * bucket_size)
            bucket_end = bucket_start + bucket_size
            
            bucket_events = [
                e for e in self.events
                if bucket_start <= e.timestamp < bucket_end and e.event_type == "request_end"
            ]
            
            if bucket_events:
                response_times = [e.response_time for e in bucket_events if e.response_time is not None]
                successful = [e for e in bucket_events if e.error is None]
                
                buckets.append({
                    "hour": i,
                    "timestamp": bucket_start,
                    "total_requests": len(bucket_events),
                    "avg_response_time": statistics.mean(response_times) if response_times else 0.0,
                    "success_rate": len(successful) / len(bucket_events) if bucket_events else 0.0,
                    "active_models": list(set(e.model_name for e in bucket_events))
                })
        
        return {"hourly_trends": buckets}
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report"""
        snapshot = self.get_current_snapshot()
        model_comparison = self.get_model_performance_comparison()
        degradation = self.is_performance_degraded()
        
        report = ["\n=== PERFORMANCE METRICS REPORT ==="]
        report.append(f"Timestamp: {datetime.fromtimestamp(snapshot.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Window: Last {self.window_minutes} minutes")
        report.append("")
        
        # Current performance
        report.append("=== CURRENT PERFORMANCE ===")
        report.append(f"Total Requests: {snapshot.total_requests}")
        report.append(f"Average Response Time: {snapshot.avg_response_time:.2f}s (target: <{self.target_response_time}s)")
        report.append(f"95th Percentile: {snapshot.p95_response_time:.2f}s")
        report.append(f"99th Percentile: {snapshot.p99_response_time:.2f}s")
        report.append(f"Success Rate: {snapshot.success_rate:.1%} (target: >{self.target_success_rate:.1%})")
        report.append(f"Cache Hit Rate: {snapshot.cache_hit_rate:.1%} (target: >{self.target_cache_hit_rate:.1%})")
        report.append(f"Active Model: {snapshot.active_model}")
        report.append("")
        
        # Performance status
        report.append("=== PERFORMANCE STATUS ===")
        status_items = []
        if degradation["response_time_exceeded"]:
            status_items.append("❌ Response time exceeds target")
        else:
            status_items.append("✅ Response time within target")
            
        if degradation["success_rate_low"]:
            status_items.append("❌ Success rate below target")
        else:
            status_items.append("✅ Success rate meets target")
            
        if degradation["cache_hit_rate_low"]:
            status_items.append("⚠️ Cache hit rate below target")
        else:
            status_items.append("✅ Cache hit rate meets target")
            
        report.extend(status_items)
        report.append("")
        
        # Model comparison
        if model_comparison:
            report.append("=== MODEL PERFORMANCE COMPARISON ===")
            for model, metrics in model_comparison.items():
                report.append(f"{model}:")
                report.append(f"  Avg Response Time: {metrics['avg_response_time']:.2f}s")
                report.append(f"  Success Rate: {metrics['success_rate']:.1%}")
                report.append(f"  Avg Accuracy: {metrics['avg_accuracy']:.1%}")
                report.append(f"  Total Requests: {metrics['total_requests']}")
                report.append("")
        
        # Recommendations
        report.append("=== RECOMMENDATIONS ===")
        if degradation["response_time_exceeded"]:
            report.append("- Consider switching to a faster model")
            report.append("- Investigate caching opportunities")
        if degradation["success_rate_low"]:
            report.append("- Review error patterns and model stability")
        if degradation["cache_hit_rate_low"]:
            report.append("- Optimize caching strategy")
            
        if not any(degradation.values()):
            report.append("✅ All performance metrics are within targets")
        
        return "\n".join(report)
    
    def export_metrics(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """Export metrics data"""
        data = {
            "snapshot": self.get_current_snapshot().__dict__,
            "model_comparison": self.get_model_performance_comparison(),
            "performance_degraded": self.is_performance_degraded(),
            "trends": self.get_performance_trends(),
            "config": {
                "target_response_time": self.target_response_time,
                "target_success_rate": self.target_success_rate,
                "target_cache_hit_rate": self.target_cache_hit_rate,
                "window_minutes": self.window_minutes
            }
        }
        
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        else:
            return data