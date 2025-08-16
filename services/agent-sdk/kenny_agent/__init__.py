"""
Kenny Agent SDK - Base framework for building agents in the Kenny v2 system.

This package provides the foundational classes and utilities for creating
agents that can register with the agent registry and execute capabilities.
"""

from .base_agent import BaseAgent
from .agent_service_base import AgentServiceBase, SemanticCache, LLMQueryProcessor
from .base_handler import BaseCapabilityHandler
from .base_tool import BaseTool
from .health import HealthStatus, HealthCheck, HealthMonitor, AgentHealthMonitor
from .registry import AgentRegistryClient
from .tracing import Tracer, TracingMiddleware, SpanContext, AsyncSpanContext, trace_function, TraceCollector, init_tracing, get_tracer
from .alerting import AlertEngine, Alert, AlertRule, AlertSeverity, AlertType, AlertStatus, AlertNotifier, init_alerting, get_alert_engine
from .analytics import PerformanceAnalytics, MetricCollector, TrendAnalyzer, CapacityPlanner, init_analytics, get_analytics_engine
from .security import SecurityMonitor, SecurityEvent, SecurityEventType, SecuritySeverity, EgressMonitor, DataAccessMonitor, init_security, get_security_monitor

__version__ = "0.1.0"
__all__ = [
    "BaseAgent",
    "AgentServiceBase",
    "SemanticCache", 
    "LLMQueryProcessor",
    "BaseCapabilityHandler", 
    "BaseTool",
    "HealthStatus",
    "HealthCheck",
    "HealthMonitor",
    "AgentHealthMonitor",
    "AgentRegistryClient",
    "Tracer",
    "TracingMiddleware", 
    "SpanContext",
    "AsyncSpanContext",
    "trace_function",
    "TraceCollector",
    "init_tracing",
    "get_tracer",
    "AlertEngine",
    "Alert",
    "AlertRule",
    "AlertSeverity",
    "AlertType",
    "AlertStatus",
    "AlertNotifier",
    "init_alerting",
    "get_alert_engine",
    "PerformanceAnalytics",
    "MetricCollector",
    "TrendAnalyzer",
    "CapacityPlanner",
    "init_analytics",
    "get_analytics_engine",
    "SecurityMonitor",
    "SecurityEvent",
    "SecurityEventType",
    "SecuritySeverity",
    "EgressMonitor",
    "DataAccessMonitor",
    "init_security",
    "get_security_monitor"
]
