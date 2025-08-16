"""
Performance monitoring module for Calendar Agent Phase 3.2.1 optimizations.

This module provides comprehensive performance tracking and metrics collection
for parallel processing optimizations in the calendar system.
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetrics:
    """Performance metrics for calendar operations."""
    
    operation_name: str
    start_time: float
    end_time: float = 0.0
    execution_time: float = 0.0
    parallel_operations: int = 1
    cache_hits: int = 0
    cache_misses: int = 0
    error_count: int = 0
    success_count: int = 0
    concurrent_tasks: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def complete(self):
        """Mark the operation as complete and calculate execution time."""
        self.end_time = time.time()
        self.execution_time = self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for logging/reporting."""
        return {
            "operation": self.operation_name,
            "execution_time": round(self.execution_time, 3),
            "parallel_operations": self.parallel_operations,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "error_count": self.error_count,
            "success_count": self.success_count,
            "concurrent_tasks": self.concurrent_tasks,
            "cache_hit_ratio": self.cache_hits / max(self.cache_hits + self.cache_misses, 1),
            "success_ratio": self.success_count / max(self.success_count + self.error_count, 1),
            "metadata": self.metadata
        }


class PerformanceMonitor:
    """Enhanced performance monitor for calendar operations with parallel processing tracking."""
    
    def __init__(self, max_history: int = 1000):
        """Initialize performance monitor."""
        self.max_history = max_history
        self.operation_history: deque = deque(maxlen=max_history)
        self.current_operations: Dict[str, PerformanceMetrics] = {}
        self.aggregate_stats = defaultdict(list)
        self.logger = logging.getLogger("calendar-performance")
        
    @asynccontextmanager
    async def monitor_operation(self, operation_name: str, **metadata):
        """Context manager for monitoring operation performance."""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=time.time(),
            metadata=metadata
        )
        
        self.current_operations[operation_id] = metrics
        
        try:
            yield metrics
        except Exception as e:
            metrics.error_count += 1
            metrics.metadata["error"] = str(e)
            raise
        finally:
            metrics.complete()
            self._record_operation(metrics)
            if operation_id in self.current_operations:
                del self.current_operations[operation_id]
    
    def _record_operation(self, metrics: PerformanceMetrics):
        """Record completed operation metrics."""
        self.operation_history.append(metrics)
        self.aggregate_stats[metrics.operation_name].append(metrics.execution_time)
        
        # Log performance data
        perf_data = metrics.to_dict()
        if metrics.error_count > 0:
            self.logger.warning(f"Operation completed with errors: {perf_data}")
        else:
            self.logger.info(f"Operation completed: {perf_data}")
    
    def get_operation_stats(self, operation_name: str) -> Dict[str, Any]:
        """Get aggregate statistics for a specific operation."""
        times = self.aggregate_stats.get(operation_name, [])
        if not times:
            return {"operation": operation_name, "no_data": True}
        
        return {
            "operation": operation_name,
            "count": len(times),
            "avg_time": round(sum(times) / len(times), 3),
            "min_time": round(min(times), 3),
            "max_time": round(max(times), 3),
            "recent_avg": round(sum(times[-10:]) / min(len(times), 10), 3),
            "performance_trend": self._calculate_trend(times)
        }
    
    def _calculate_trend(self, times: List[float]) -> str:
        """Calculate performance trend (improving/declining/stable)."""
        if len(times) < 5:
            return "insufficient_data"
        
        recent = times[-5:]
        older = times[-10:-5] if len(times) >= 10 else times[:-5]
        
        if not older:
            return "insufficient_data"
        
        recent_avg = sum(recent) / len(recent)
        older_avg = sum(older) / len(older)
        
        improvement = (older_avg - recent_avg) / older_avg
        
        if improvement > 0.1:
            return "improving"
        elif improvement < -0.1:
            return "declining"
        else:
            return "stable"
    
    def get_parallel_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report for parallel operations."""
        total_operations = len(self.operation_history)
        if total_operations == 0:
            return {"status": "no_data", "message": "No performance data available"}
        
        # Analyze parallel vs sequential performance
        parallel_ops = [op for op in self.operation_history if op.parallel_operations > 1]
        sequential_ops = [op for op in self.operation_history if op.parallel_operations == 1]
        
        report = {
            "summary": {
                "total_operations": total_operations,
                "parallel_operations": len(parallel_ops),
                "sequential_operations": len(sequential_ops),
                "parallel_adoption_rate": round(len(parallel_ops) / total_operations, 2)
            },
            "performance_comparison": {},
            "operation_breakdown": {},
            "optimization_impact": {}
        }
        
        # Calculate performance improvements
        if parallel_ops and sequential_ops:
            parallel_avg = sum(op.execution_time for op in parallel_ops) / len(parallel_ops)
            sequential_avg = sum(op.execution_time for op in sequential_ops) / len(sequential_ops)
            
            improvement = (sequential_avg - parallel_avg) / sequential_avg if sequential_avg > 0 else 0
            
            report["performance_comparison"] = {
                "parallel_avg_time": round(parallel_avg, 3),
                "sequential_avg_time": round(sequential_avg, 3),
                "improvement_percentage": round(improvement * 100, 1),
                "target_improvement": "30-40%",
                "target_met": improvement >= 0.30
            }
        
        # Break down by operation type
        for op_name in self.aggregate_stats.keys():
            report["operation_breakdown"][op_name] = self.get_operation_stats(op_name)
        
        # Calculate optimization impact
        recent_ops = list(self.operation_history)[-50:]  # Last 50 operations
        if recent_ops:
            cache_hit_ratio = sum(op.cache_hits for op in recent_ops) / max(
                sum(op.cache_hits + op.cache_misses for op in recent_ops), 1
            )
            success_ratio = sum(op.success_count for op in recent_ops) / max(
                sum(op.success_count + op.error_count for op in recent_ops), 1
            )
            
            report["optimization_impact"] = {
                "cache_hit_ratio": round(cache_hit_ratio, 3),
                "success_ratio": round(success_ratio, 3),
                "avg_concurrent_tasks": round(
                    sum(op.concurrent_tasks for op in recent_ops) / len(recent_ops), 1
                ),
                "recent_performance_trend": self._get_recent_trend()
            }
        
        return report
    
    def _get_recent_trend(self) -> str:
        """Get performance trend for recent operations."""
        recent_times = [op.execution_time for op in list(self.operation_history)[-20:]]
        return self._calculate_trend(recent_times)
    
    def log_performance_summary(self):
        """Log a comprehensive performance summary."""
        report = self.get_parallel_performance_report()
        
        if report.get("status") == "no_data":
            self.logger.info("No performance data available for summary")
            return
        
        summary = report["summary"]
        comparison = report.get("performance_comparison", {})
        optimization = report.get("optimization_impact", {})
        
        self.logger.info(f"""
Calendar Agent Performance Summary (Phase 3.2.1):
=================================================
Total Operations: {summary['total_operations']}
Parallel Operations: {summary['parallel_operations']} ({summary['parallel_adoption_rate']*100:.1f}%)
Sequential Operations: {summary['sequential_operations']}

Performance Improvements:
- Target: 30-40% improvement in execution time
- Achieved: {comparison.get('improvement_percentage', 'N/A')}%
- Target Met: {comparison.get('target_met', 'Unknown')}

System Health:
- Cache Hit Ratio: {optimization.get('cache_hit_ratio', 'N/A')*100:.1f}%
- Success Ratio: {optimization.get('success_ratio', 'N/A')*100:.1f}%
- Avg Concurrent Tasks: {optimization.get('avg_concurrent_tasks', 'N/A')}
- Recent Trend: {optimization.get('recent_performance_trend', 'Unknown')}
        """)


# Global performance monitor instance
performance_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    return performance_monitor


async def log_calendar_operation(operation_name: str, **metadata):
    """Convenience function for monitoring calendar operations."""
    return performance_monitor.monitor_operation(operation_name, **metadata)