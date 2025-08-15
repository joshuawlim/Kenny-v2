"""
Performance analytics and trending module for Kenny v2.

This module provides comprehensive analytics capabilities including
historical data collection, trend analysis, capacity planning,
and performance forecasting.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import statistics
import json

logger = logging.getLogger(__name__)


@dataclass
class DataPoint:
    """Represents a single metric data point."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "value": self.value,
            "metadata": self.metadata
        }


@dataclass
class TrendAnalysis:
    """Results of trend analysis."""
    trend_direction: str  # "increasing", "decreasing", "stable"
    slope: float
    r_squared: float  # Correlation coefficient
    confidence: float  # 0-1 confidence in trend
    forecast_value: Optional[float] = None
    forecast_period_hours: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


class MetricCollector:
    """Collects and stores historical performance metrics."""
    
    def __init__(self, max_data_points: int = 10000, retention_hours: int = 168):
        """Initialize metric collector."""
        self.max_data_points = max_data_points
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_data_points))
    
    def record_metric(self, metric_name: str, value: float, metadata: Optional[Dict[str, Any]] = None):
        """Record a metric value."""
        data_point = DataPoint(
            timestamp=datetime.now(timezone.utc),
            value=value,
            metadata=metadata or {}
        )
        self.metrics[metric_name].append(data_point)
        
        # Clean old data periodically
        if len(self.metrics[metric_name]) % 100 == 0:
            self._cleanup_old_data(metric_name)
    
    def get_metric_history(self, metric_name: str, hours: int = 24) -> List[DataPoint]:
        """Get historical data for a metric."""
        if metric_name not in self.metrics:
            return []
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        return [dp for dp in self.metrics[metric_name] if dp.timestamp >= cutoff_time]
    
    def get_metric_summary(self, metric_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get summary statistics for a metric."""
        data_points = self.get_metric_history(metric_name, hours)
        if not data_points:
            return {"error": "No data available"}
        
        values = [dp.value for dp in data_points]
        
        return {
            "count": len(values),
            "min": min(values),
            "max": max(values),
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0,
            "first_timestamp": data_points[0].timestamp.isoformat(),
            "last_timestamp": data_points[-1].timestamp.isoformat(),
            "time_period_hours": hours
        }
    
    def _cleanup_old_data(self, metric_name: str):
        """Remove old data points to prevent memory growth."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.retention_hours)
        
        # Convert deque to list, filter, then back to deque
        data_points = list(self.metrics[metric_name])
        filtered_points = [dp for dp in data_points if dp.timestamp >= cutoff_time]
        
        # Clear and repopulate deque
        self.metrics[metric_name].clear()
        self.metrics[metric_name].extend(filtered_points)


class TrendAnalyzer:
    """Analyzes trends in performance metrics."""
    
    def __init__(self):
        """Initialize trend analyzer."""
        pass
    
    def analyze_trend(self, data_points: List[DataPoint], min_points: int = 10) -> TrendAnalysis:
        """Analyze trend in data points using linear regression."""
        if len(data_points) < min_points:
            return TrendAnalysis(
                trend_direction="insufficient_data",
                slope=0.0,
                r_squared=0.0,
                confidence=0.0
            )
        
        # Prepare data for linear regression
        timestamps = [(dp.timestamp - data_points[0].timestamp).total_seconds() for dp in data_points]
        values = [dp.value for dp in data_points]
        
        # Calculate linear regression
        slope, r_squared = self._linear_regression(timestamps, values)
        
        # Determine trend direction
        if abs(slope) < 0.001:  # Very small slope
            trend_direction = "stable"
            confidence = min(r_squared, 0.8)
        elif slope > 0:
            trend_direction = "increasing"
            confidence = r_squared
        else:
            trend_direction = "decreasing"  
            confidence = r_squared
        
        return TrendAnalysis(
            trend_direction=trend_direction,
            slope=slope,
            r_squared=r_squared,
            confidence=confidence
        )
    
    def forecast_value(self, data_points: List[DataPoint], hours_ahead: int = 1) -> Optional[float]:
        """Forecast a metric value using trend analysis."""
        if len(data_points) < 10:
            return None
        
        trend = self.analyze_trend(data_points)
        if trend.confidence < 0.5:  # Low confidence in trend
            return None
        
        # Use linear extrapolation
        last_point = data_points[-1]
        seconds_ahead = hours_ahead * 3600
        forecasted_value = last_point.value + (trend.slope * seconds_ahead)
        
        return max(0, forecasted_value)  # Don't forecast negative values for most metrics
    
    def _linear_regression(self, x: List[float], y: List[float]) -> Tuple[float, float]:
        """Calculate linear regression slope and R-squared."""
        n = len(x)
        if n < 2:
            return 0.0, 0.0
        
        # Calculate means
        x_mean = statistics.mean(x)
        y_mean = statistics.mean(y)
        
        # Calculate slope
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            return 0.0, 0.0
        
        slope = numerator / denominator
        
        # Calculate R-squared
        y_pred = [slope * (x[i] - x_mean) + y_mean for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))
        
        if ss_tot == 0:
            r_squared = 1.0 if ss_res == 0 else 0.0
        else:
            r_squared = 1 - (ss_res / ss_tot)
        
        return slope, max(0.0, min(1.0, r_squared))


class CapacityPlanner:
    """Provides capacity planning insights based on performance trends."""
    
    def __init__(self):
        """Initialize capacity planner."""
        self.trend_analyzer = TrendAnalyzer()
    
    def analyze_capacity(self, metric_data: Dict[str, List[DataPoint]], 
                        thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Analyze capacity and predict when thresholds will be reached."""
        results = {}
        
        for metric_name, data_points in metric_data.items():
            if metric_name not in thresholds:
                continue
            
            threshold = thresholds[metric_name]
            current_value = data_points[-1].value if data_points else 0
            
            # Analyze trend
            trend = self.trend_analyzer.analyze_trend(data_points)
            
            # Calculate time to threshold
            time_to_threshold = None
            if trend.slope > 0 and trend.confidence > 0.5:
                remaining_capacity = threshold - current_value
                if remaining_capacity > 0:
                    # Time in seconds to reach threshold
                    time_seconds = remaining_capacity / trend.slope
                    time_to_threshold = time_seconds / 3600  # Convert to hours
            
            results[metric_name] = {
                "current_value": current_value,
                "threshold": threshold,
                "utilization_percent": (current_value / threshold * 100) if threshold > 0 else 0,
                "trend": trend.to_dict(),
                "time_to_threshold_hours": time_to_threshold,
                "capacity_status": self._get_capacity_status(current_value, threshold, time_to_threshold)
            }
        
        return results
    
    def _get_capacity_status(self, current_value: float, threshold: float, 
                           time_to_threshold: Optional[float]) -> str:
        """Determine capacity status."""
        utilization = (current_value / threshold) if threshold > 0 else 0
        
        if utilization >= 0.9:
            return "critical"
        elif utilization >= 0.8:
            return "warning"
        elif time_to_threshold and time_to_threshold < 24:
            return "approaching_limit"
        else:
            return "healthy"


class PerformanceAnalytics:
    """Main analytics engine combining metrics collection, trend analysis, and capacity planning."""
    
    def __init__(self):
        """Initialize performance analytics."""
        self.metric_collector = MetricCollector()
        self.trend_analyzer = TrendAnalyzer()
        self.capacity_planner = CapacityPlanner()
        
        # Default metric thresholds
        self.thresholds = {
            "response_time_ms": 2000.0,
            "error_rate_percent": 5.0,
            "memory_usage_percent": 85.0,
            "cpu_usage_percent": 80.0,
            "disk_usage_percent": 90.0
        }
    
    def record_performance_metric(self, metric_name: str, value: float, 
                                metadata: Optional[Dict[str, Any]] = None):
        """Record a performance metric."""
        self.metric_collector.record_metric(metric_name, value, metadata)
    
    def get_performance_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive performance dashboard data."""
        dashboard = {
            "summary": {},
            "trends": {},
            "forecasts": {},
            "capacity_analysis": {},
            "time_period_hours": hours
        }
        
        # Get all available metrics
        available_metrics = list(self.metric_collector.metrics.keys())
        
        for metric_name in available_metrics:
            # Get metric summary
            summary = self.metric_collector.get_metric_summary(metric_name, hours)
            dashboard["summary"][metric_name] = summary
            
            # Get historical data for analysis
            data_points = self.metric_collector.get_metric_history(metric_name, hours)
            
            if len(data_points) >= 10:
                # Analyze trend
                trend = self.trend_analyzer.analyze_trend(data_points)
                dashboard["trends"][metric_name] = trend.to_dict()
                
                # Generate forecast
                forecast_1h = self.trend_analyzer.forecast_value(data_points, 1)
                forecast_24h = self.trend_analyzer.forecast_value(data_points, 24)
                
                dashboard["forecasts"][metric_name] = {
                    "1_hour": forecast_1h,
                    "24_hours": forecast_24h
                }
        
        # Capacity analysis
        metric_data = {name: self.metric_collector.get_metric_history(name, hours) 
                      for name in available_metrics}
        capacity_analysis = self.capacity_planner.analyze_capacity(metric_data, self.thresholds)
        dashboard["capacity_analysis"] = capacity_analysis
        
        return dashboard
    
    def get_metric_chart_data(self, metric_name: str, hours: int = 24, 
                             resolution_minutes: int = 5) -> Dict[str, Any]:
        """Get metric data formatted for charting."""
        data_points = self.metric_collector.get_metric_history(metric_name, hours)
        if not data_points:
            return {"error": "No data available"}
        
        # Group data points by time buckets for aggregation
        bucket_size = timedelta(minutes=resolution_minutes)
        buckets = defaultdict(list)
        
        start_time = data_points[0].timestamp
        for dp in data_points:
            bucket_index = int((dp.timestamp - start_time).total_seconds() / bucket_size.total_seconds())
            buckets[bucket_index].append(dp.value)
        
        # Aggregate buckets
        chart_data = []
        for bucket_index in sorted(buckets.keys()):
            bucket_time = start_time + (bucket_index * bucket_size)
            bucket_values = buckets[bucket_index]
            
            chart_data.append({
                "timestamp": bucket_time.isoformat(),
                "value": statistics.mean(bucket_values),
                "min": min(bucket_values),
                "max": max(bucket_values),
                "count": len(bucket_values)
            })
        
        return {
            "metric_name": metric_name,
            "time_period_hours": hours,
            "resolution_minutes": resolution_minutes,
            "data_points": chart_data,
            "total_samples": len(data_points)
        }
    
    def set_threshold(self, metric_name: str, threshold_value: float):
        """Set threshold for a metric."""
        self.thresholds[metric_name] = threshold_value
    
    def get_anomalies(self, metric_name: str, hours: int = 24, 
                     std_dev_threshold: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalies in metric data."""
        data_points = self.metric_collector.get_metric_history(metric_name, hours)
        if len(data_points) < 10:
            return []
        
        values = [dp.value for dp in data_points]
        mean_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        
        if std_dev == 0:
            return []
        
        threshold_upper = mean_value + (std_dev_threshold * std_dev)
        threshold_lower = mean_value - (std_dev_threshold * std_dev)
        
        anomalies = []
        for dp in data_points:
            if dp.value > threshold_upper or dp.value < threshold_lower:
                anomalies.append({
                    "timestamp": dp.timestamp.isoformat(),
                    "value": dp.value,
                    "expected_range": [threshold_lower, threshold_upper],
                    "deviation_factor": abs(dp.value - mean_value) / std_dev,
                    "metadata": dp.metadata
                })
        
        return anomalies


# Global analytics instance
analytics_engine: Optional[PerformanceAnalytics] = None


def init_analytics() -> PerformanceAnalytics:
    """Initialize the global analytics engine."""
    global analytics_engine
    analytics_engine = PerformanceAnalytics()
    return analytics_engine


def get_analytics_engine() -> Optional[PerformanceAnalytics]:
    """Get the global analytics engine instance."""
    return analytics_engine