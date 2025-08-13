"""
Health check utilities for the Kenny v2 multi-agent system.

This module provides classes and utilities for monitoring and reporting
agent health status.
"""

from typing import Dict, Any, Callable, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from enum import Enum


class HealthStatusEnum(str, Enum):
    """Enumeration of possible health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthStatus:
    """
    Represents the health status of an agent or component.
    
    Attributes:
        status: Health status (healthy, degraded, unhealthy, unknown)
        message: Human-readable description of the health status
        details: Additional health information
        timestamp: When this health status was recorded
    """
    status: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
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
