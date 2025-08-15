"""
Health check utilities for the Kenny v2 multi-agent system.

This module provides classes and utilities for monitoring and reporting
agent health status with performance metrics and trend analysis.
"""

from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import time
import statistics
from collections import deque


class HealthStatusEnum(str, Enum):
    """Enumeration of possible health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class PerformanceMetrics:
    """Performance metrics for agent operations."""
    response_time_ms: float
    success_rate_percent: float
    throughput_ops_per_min: float
    error_count: int
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "response_time_ms": self.response_time_ms,
            "success_rate_percent": self.success_rate_percent,
            "throughput_ops_per_min": self.throughput_ops_per_min,
            "error_count": self.error_count,
            "timestamp": self.timestamp.isoformat()
        }


class PerformanceTracker:
    """Tracks performance metrics with sliding window analysis."""
    
    def __init__(self, window_size: int = 100, time_window_minutes: int = 60):
        """
        Initialize performance tracker.
        
        Args:
            window_size: Number of recent operations to track
            time_window_minutes: Time window for rate calculations
        """
        self.window_size = window_size
        self.time_window = timedelta(minutes=time_window_minutes)
        
        # Sliding windows for metrics
        self.response_times: deque = deque(maxlen=window_size)
        self.operations: deque = deque(maxlen=window_size * 2)  # Store (timestamp, success) tuples
        self.error_count = 0
        
        # SLA thresholds
        self.response_time_sla_ms = 2000  # 2 second default SLA
        self.success_rate_sla_percent = 95.0  # 95% success rate SLA
        
    def record_operation(self, response_time_ms: float, success: bool = True):
        """Record a single operation for metrics calculation."""
        timestamp = datetime.now(timezone.utc)
        
        self.response_times.append(response_time_ms)
        self.operations.append((timestamp, success))
        
        if not success:
            self.error_count += 1
    
    def get_current_metrics(self) -> PerformanceMetrics:
        """Calculate current performance metrics."""
        now = datetime.now(timezone.utc)
        cutoff_time = now - self.time_window
        
        # Filter recent operations
        recent_ops = [(ts, success) for ts, success in self.operations if ts >= cutoff_time]
        
        # Calculate metrics
        if not recent_ops:
            return PerformanceMetrics(
                response_time_ms=0.0,
                success_rate_percent=100.0,
                throughput_ops_per_min=0.0,
                error_count=0,
                timestamp=now
            )
        
        # Response time metrics
        recent_response_times = list(self.response_times)[-len(recent_ops):]
        avg_response_time = statistics.mean(recent_response_times) if recent_response_times else 0.0
        
        # Success rate
        successful_ops = sum(1 for _, success in recent_ops if success)
        success_rate = (successful_ops / len(recent_ops) * 100) if recent_ops else 100.0
        
        # Throughput (operations per minute)
        time_span_minutes = max(1, self.time_window.total_seconds() / 60)
        throughput = len(recent_ops) / time_span_minutes
        
        # Error count
        error_count = sum(1 for _, success in recent_ops if not success)
        
        return PerformanceMetrics(
            response_time_ms=avg_response_time,
            success_rate_percent=success_rate,
            throughput_ops_per_min=throughput,
            error_count=error_count,
            timestamp=now
        )
    
    def check_sla_compliance(self) -> Dict[str, Any]:
        """Check if current performance meets SLA thresholds."""
        metrics = self.get_current_metrics()
        
        response_time_ok = metrics.response_time_ms <= self.response_time_sla_ms
        success_rate_ok = metrics.success_rate_percent >= self.success_rate_sla_percent
        
        return {
            "response_time_sla": {
                "current_ms": metrics.response_time_ms,
                "threshold_ms": self.response_time_sla_ms,
                "compliant": response_time_ok
            },
            "success_rate_sla": {
                "current_percent": metrics.success_rate_percent,
                "threshold_percent": self.success_rate_sla_percent,
                "compliant": success_rate_ok
            },
            "overall_compliant": response_time_ok and success_rate_ok
        }
    
    def get_performance_trend(self) -> Dict[str, Any]:
        """Analyze performance trends over time."""
        if len(self.response_times) < 10:
            return {"trend": "insufficient_data"}
        
        # Calculate trend over recent operations
        recent_times = list(self.response_times)[-20:]  # Last 20 operations
        older_times = list(self.response_times)[-40:-20] if len(self.response_times) >= 40 else []
        
        if not older_times:
            return {"trend": "insufficient_data"}
        
        recent_avg = statistics.mean(recent_times)
        older_avg = statistics.mean(older_times)
        
        # Determine trend
        change_percent = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
        
        if change_percent > 20:
            trend = "degrading"
        elif change_percent < -10:
            trend = "improving"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "change_percent": change_percent,
            "recent_avg_ms": recent_avg,
            "older_avg_ms": older_avg
        }


@dataclass
class HealthStatus:
    """
    Represents the health status of an agent or component.
    
    Attributes:
        status: Health status (healthy, degraded, unhealthy, unknown)
        message: Human-readable description of the health status
        details: Additional health information
        timestamp: When this health status was recorded
        performance_metrics: Optional performance metrics
    """
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    performance_metrics: Optional[PerformanceMetrics] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        if self.performance_metrics:
            data['performance_metrics'] = self.performance_metrics.to_dict()
        return data
    
    def is_healthy(self) -> bool:
        """Check if the status indicates healthy operation."""
        return self.status == HealthStatusEnum.HEALTHY
    
    def is_degraded(self) -> bool:
        """Check if the status indicates degraded operation."""
        return self.status == HealthStatusEnum.DEGRADED
    
    def is_unhealthy(self) -> bool:
        """Check if the status indicates unhealthy operation."""
        return self.status == HealthStatusEnum.UNHEALTHY


class HealthCheck:
    """
    Represents a single health check that can be executed.
    
    Health checks are functions that return a HealthStatus object
    and can be used to monitor various aspects of agent health.
    """
    
    def __init__(
        self,
        name: str,
        check_function: Callable[[], HealthStatus],
        description: str = "",
        timeout: Optional[float] = None,
        critical: bool = False
    ):
        """
        Initialize the health check.
        
        Args:
            name: Name of the health check
            check_function: Function that performs the health check
            description: Description of what the health check does
            timeout: Timeout in seconds for the health check
            critical: Whether this is a critical health check
        """
        self.name = name
        self.check_function = check_function
        self.description = description
        self.timeout = timeout
        self.critical = critical
        
        # Execution metadata
        self.last_executed = None
        self.last_status = None
        self.execution_count = 0
        self.failure_count = 0
    
    def execute(self) -> HealthStatus:
        """
        Execute the health check.
        
        Returns:
            HealthStatus object representing the result
            
        Raises:
            Exception: If the health check fails
        """
        try:
            # Execute the health check function
            result = self.check_function()
            
            # Update metadata
            self.last_executed = datetime.now(timezone.utc)
            self.last_status = result.status
            self.execution_count += 1
            
            # Track failures
            if result.is_unhealthy():
                self.failure_count += 1
            
            return result
            
        except Exception as e:
            # Update metadata
            self.last_executed = datetime.now(timezone.utc)
            self.last_status = HealthStatusEnum.UNHEALTHY
            self.execution_count += 1
            self.failure_count += 1
            
            # Return unhealthy status for exceptions
            return HealthStatus(
                status=HealthStatusEnum.UNHEALTHY,
                message=f"Health check failed: {str(e)}",
                details={"error": str(e), "check_name": self.name}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get execution statistics for the health check.
        
        Returns:
            Dictionary containing execution statistics
        """
        stats = {
            "name": self.name,
            "description": self.description,
            "critical": self.critical,
            "execution_count": self.execution_count,
            "failure_count": self.failure_count,
            "success_rate": ((self.execution_count - self.failure_count) / self.execution_count * 100) if self.execution_count > 0 else 0,
            "last_executed": self.last_executed.isoformat() if self.last_executed else None,
            "last_status": self.last_status
        }
        
        return stats


class HealthMonitor:
    """
    Manages multiple health checks for an agent or component.
    
    The health monitor can execute multiple health checks and aggregate
    their results into an overall health status.
    """
    
    def __init__(self, name: str = "health_monitor"):
        """
        Initialize the health monitor.
        
        Args:
            name: Name of the health monitor
        """
        self.name = name
        self.health_checks: Dict[str, HealthCheck] = {}
    
    def add_health_check(self, health_check: HealthCheck) -> None:
        """
        Add a health check to the monitor.
        
        Args:
            health_check: HealthCheck object to add
        """
        self.health_checks[health_check.name] = health_check
    
    def remove_health_check(self, name: str) -> None:
        """
        Remove a health check from the monitor.
        
        Args:
            name: Name of the health check to remove
        """
        if name in self.health_checks:
            del self.health_checks[name]
    
    def execute_all_checks(self) -> Dict[str, HealthStatus]:
        """
        Execute all registered health checks.
        
        Returns:
            Dictionary mapping health check names to their results
        """
        results = {}
        
        for name, health_check in self.health_checks.items():
            try:
                results[name] = health_check.execute()
            except Exception as e:
                results[name] = HealthStatus(
                    status=HealthStatusEnum.UNHEALTHY,
                    message=f"Health check execution failed: {str(e)}",
                    details={"error": str(e), "check_name": name}
                )
        
        return results
    
    def get_overall_health(self) -> HealthStatus:
        """
        Get the overall health status based on all health checks.
        
        Returns:
            Aggregated HealthStatus object
        """
        if not self.health_checks:
            return HealthStatus(
                status=HealthStatusEnum.UNKNOWN,
                message="No health checks registered",
                details={}
            )
        
        # Execute all checks
        results = self.execute_all_checks()
        
        # Determine overall status
        status_counts = {}
        for result in results.values():
            status = result.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Check for critical failures
        critical_failures = 0
        for name, health_check in self.health_checks.items():
            if health_check.critical and results[name].is_unhealthy():
                critical_failures += 1
        
        # Determine overall status
        if critical_failures > 0:
            overall_status = HealthStatusEnum.UNHEALTHY
            message = f"Critical health checks failed: {critical_failures}"
        elif HealthStatusEnum.UNHEALTHY in status_counts:
            overall_status = HealthStatusEnum.UNHEALTHY
            message = f"Unhealthy checks: {status_counts[HealthStatusEnum.UNHEALTHY]}"
        elif HealthStatusEnum.DEGRADED in status_counts:
            overall_status = HealthStatusEnum.DEGRADED
            message = f"Degraded checks: {status_counts[HealthStatusEnum.DEGRADED]}"
        else:
            overall_status = HealthStatusEnum.HEALTHY
            message = "All health checks passed"
        
        # Create overall health status
        overall_health = HealthStatus(
            status=overall_status,
            message=message,
            details={
                "total_checks": len(self.health_checks),
                "status_breakdown": status_counts,
                "critical_failures": critical_failures,
                "individual_results": {name: result.to_dict() for name, result in results.items()}
            }
        )
        
        return overall_health
    
    def get_health_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all health check results.
        
        Returns:
            Dictionary containing health summary information
        """
        overall_health = self.get_overall_health()
        
        summary = {
            "monitor_name": self.name,
            "overall_health": overall_health.to_dict(),
            "health_checks": {}
        }
        
        for name, health_check in self.health_checks.items():
            summary["health_checks"][name] = {
                "description": health_check.description,
                "critical": health_check.critical,
                "stats": health_check.get_stats()
            }
        
        return summary


class AgentHealthMonitor(HealthMonitor):
    """
    Enhanced health monitor with performance metrics and predictive capabilities.
    
    Extends the basic HealthMonitor with performance tracking, SLA monitoring,
    and trend analysis for predictive degradation detection.
    """
    
    def __init__(self, name: str = "agent_health_monitor"):
        """Initialize the enhanced health monitor."""
        super().__init__(name)
        self.performance_tracker = PerformanceTracker()
        self.degradation_alerts: List[Dict[str, Any]] = []
        
    def record_operation(self, response_time_ms: float, success: bool = True):
        """Record an operation for performance tracking."""
        self.performance_tracker.record_operation(response_time_ms, success)
        
        # Check for degradation patterns
        self._check_degradation_patterns()
    
    def _check_degradation_patterns(self):
        """Check for patterns that indicate impending degradation."""
        sla_compliance = self.performance_tracker.check_sla_compliance()
        trend = self.performance_tracker.get_performance_trend()
        
        # Detect concerning patterns
        alerts = []
        
        if not sla_compliance["overall_compliant"]:
            alerts.append({
                "type": "sla_violation",
                "severity": "high",
                "message": "Performance SLA violation detected",
                "details": sla_compliance,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        if trend.get("trend") == "degrading" and trend.get("change_percent", 0) > 30:
            alerts.append({
                "type": "performance_degradation",
                "severity": "medium",
                "message": f"Performance degrading by {trend['change_percent']:.1f}%",
                "details": trend,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Store recent alerts (keep last 10)
        self.degradation_alerts.extend(alerts)
        self.degradation_alerts = self.degradation_alerts[-10:]
    
    def get_enhanced_health(self) -> HealthStatus:
        """Get overall health status enhanced with performance metrics."""
        basic_health = self.get_overall_health()
        current_metrics = self.performance_tracker.get_current_metrics()
        sla_compliance = self.performance_tracker.check_sla_compliance()
        trend = self.performance_tracker.get_performance_trend()
        
        # Adjust health status based on performance
        if not sla_compliance["overall_compliant"]:
            if basic_health.status == HealthStatusEnum.HEALTHY:
                status = HealthStatusEnum.DEGRADED
                message = f"{basic_health.message} (Performance SLA violation)"
            else:
                status = basic_health.status
                message = basic_health.message
        elif trend.get("trend") == "degrading":
            status = HealthStatusEnum.DEGRADED
            message = f"{basic_health.message} (Performance degrading)"
        else:
            status = basic_health.status
            message = basic_health.message
        
        # Enhanced details with performance data
        enhanced_details = basic_health.details or {}
        enhanced_details.update({
            "performance_metrics": current_metrics.to_dict(),
            "sla_compliance": sla_compliance,
            "performance_trend": trend,
            "recent_alerts": self.degradation_alerts[-3:],  # Last 3 alerts
            "alert_count": len(self.degradation_alerts)
        })
        
        return HealthStatus(
            status=status,
            message=message,
            details=enhanced_details,
            performance_metrics=current_metrics
        )
    
    def get_performance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        enhanced_health = self.get_enhanced_health()
        
        dashboard = {
            "agent_name": self.name,
            "overall_health": enhanced_health.to_dict(),
            "performance_summary": {
                "current_metrics": self.performance_tracker.get_current_metrics().to_dict(),
                "sla_compliance": self.performance_tracker.check_sla_compliance(),
                "trend_analysis": self.performance_tracker.get_performance_trend()
            },
            "health_checks": {},
            "alerts": {
                "recent": self.degradation_alerts[-5:],  # Last 5 alerts
                "total_count": len(self.degradation_alerts),
                "active_issues": len([a for a in self.degradation_alerts 
                                   if a.get("severity") in ["high", "critical"]])
            },
            "recommendations": self._generate_recommendations()
        }
        
        # Add individual health check details with performance data
        for name, health_check in self.health_checks.items():
            dashboard["health_checks"][name] = {
                "description": health_check.description,
                "critical": health_check.critical,
                "stats": health_check.get_stats(),
                "last_status": health_check.last_status,
                "last_executed": health_check.last_executed.isoformat() if health_check.last_executed else None
            }
        
        return dashboard
    
    def _generate_recommendations(self) -> List[str]:
        """Generate actionable recommendations based on health data."""
        recommendations = []
        
        sla_compliance = self.performance_tracker.check_sla_compliance()
        trend = self.performance_tracker.get_performance_trend()
        metrics = self.performance_tracker.get_current_metrics()
        
        # Response time recommendations
        if not sla_compliance["response_time_sla"]["compliant"]:
            recommendations.append(
                f"Response time ({metrics.response_time_ms:.0f}ms) exceeds SLA "
                f"({sla_compliance['response_time_sla']['threshold_ms']}ms). "
                "Consider optimizing performance or scaling resources."
            )
        
        # Success rate recommendations  
        if not sla_compliance["success_rate_sla"]["compliant"]:
            recommendations.append(
                f"Success rate ({metrics.success_rate_percent:.1f}%) below SLA "
                f"({sla_compliance['success_rate_sla']['threshold_percent']}%). "
                "Investigate error patterns and implement error handling improvements."
            )
        
        # Trend-based recommendations
        if trend.get("trend") == "degrading":
            recommendations.append(
                f"Performance degrading by {trend.get('change_percent', 0):.1f}%. "
                "Monitor resource usage and consider proactive scaling."
            )
        
        # Error rate recommendations
        if metrics.error_count > 10:
            recommendations.append(
                f"High error count ({metrics.error_count}) detected. "
                "Review logs and implement error prevention measures."
            )
        
        return recommendations
