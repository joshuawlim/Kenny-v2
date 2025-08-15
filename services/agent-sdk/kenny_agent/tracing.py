"""
Request tracing utilities for the Kenny v2 multi-agent system.

This module provides utilities for distributed tracing across coordinator
and agents, enabling end-to-end request observability with minimal overhead.
"""

import uuid
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable, AsyncGenerator
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field
from contextvars import ContextVar
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Context variable for correlation ID propagation
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class SpanType(str, Enum):
    """Types of trace spans."""
    REQUEST = "request"
    COORDINATOR_NODE = "coordinator_node"
    AGENT_CAPABILITY = "agent_capability"
    TOOL_EXECUTION = "tool_execution"
    EXTERNAL_CALL = "external_call"


class SpanStatus(str, Enum):
    """Span execution status."""
    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"


@dataclass
class TraceSpan:
    """Represents a single span in a distributed trace."""
    span_id: str
    correlation_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: SpanType
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: SpanStatus = SpanStatus.OK
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    def finish(self, status: SpanStatus = SpanStatus.OK):
        """Finish the span with a status."""
        self.end_time = datetime.now(timezone.utc)
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span."""
        event = {
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attributes": attributes or {}
        }
        self.events.append(event)
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value
    
    def set_error(self, error: Exception):
        """Mark span as error with exception details."""
        self.status = SpanStatus.ERROR
        self.set_attribute("error.type", type(error).__name__)
        self.set_attribute("error.message", str(error))
        self.add_event("exception", {
            "exception.type": type(error).__name__,
            "exception.message": str(error)
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary representation."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        data["span_type"] = self.span_type.value
        data["status"] = self.status.value
        return data


class Tracer:
    """Distributed tracer for Kenny v2 multi-agent system."""
    
    def __init__(self, service_name: str):
        """Initialize tracer for a service."""
        self.service_name = service_name
        self.spans: Dict[str, TraceSpan] = {}
        self.span_exporters: List[Callable[[TraceSpan], None]] = []
    
    def add_span_exporter(self, exporter: Callable[[TraceSpan], None]):
        """Add a span exporter for sending traces to collection service."""
        self.span_exporters.append(exporter)
    
    def start_span(
        self,
        name: str,
        span_type: SpanType = SpanType.REQUEST,
        parent_span_id: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> TraceSpan:
        """Start a new trace span."""
        # Generate or get correlation ID
        if correlation_id is None:
            correlation_id = self.get_correlation_id()
        
        # Generate unique span ID
        span_id = str(uuid.uuid4())
        
        # Create span
        span = TraceSpan(
            span_id=span_id,
            correlation_id=correlation_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            service_name=self.service_name,
            start_time=datetime.now(timezone.utc)
        )
        
        # Store span
        self.spans[span_id] = span
        
        logger.debug(f"Started span {span_id} ({name}) in {self.service_name}")
        return span
    
    def finish_span(self, span: TraceSpan, status: SpanStatus = SpanStatus.OK):
        """Finish a span and export it."""
        span.finish(status)
        
        # Export span to registered exporters
        for exporter in self.span_exporters:
            try:
                exporter(span)
            except Exception as e:
                logger.error(f"Error exporting span: {e}")
        
        logger.debug(f"Finished span {span.span_id} ({span.name}) - {span.duration_ms:.2f}ms")
    
    def get_correlation_id(self) -> str:
        """Get or generate correlation ID."""
        corr_id = correlation_id.get()
        if corr_id is None:
            corr_id = str(uuid.uuid4())
            correlation_id.set(corr_id)
        return corr_id
    
    def set_correlation_id(self, corr_id: str):
        """Set correlation ID for current context."""
        correlation_id.set(corr_id)
    
    def get_span(self, span_id: str) -> Optional[TraceSpan]:
        """Get a span by ID."""
        return self.spans.get(span_id)
    
    def get_active_spans(self) -> List[TraceSpan]:
        """Get all active (unfinished) spans."""
        return [span for span in self.spans.values() if span.end_time is None]


class TracingMiddleware:
    """FastAPI middleware for automatic request tracing."""
    
    def __init__(self, tracer: Tracer):
        """Initialize tracing middleware."""
        self.tracer = tracer
    
    async def __call__(self, request, call_next):
        """Process request with tracing."""
        # Extract correlation ID from headers
        corr_id = request.headers.get("X-Correlation-ID")
        if corr_id:
            self.tracer.set_correlation_id(corr_id)
        else:
            corr_id = self.tracer.get_correlation_id()
        
        # Start request span
        span = self.tracer.start_span(
            name=f"{request.method} {request.url.path}",
            span_type=SpanType.REQUEST,
            correlation_id=corr_id
        )
        
        # Set span attributes
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.url", str(request.url))
        span.set_attribute("http.route", request.url.path)
        
        try:
            # Process request
            start_time = time.time()
            response = await call_next(request)
            
            # Set response attributes
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("http.response_size", len(response.body) if hasattr(response, 'body') else 0)
            
            # Finish span
            self.tracer.finish_span(span, SpanStatus.OK)
            
            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = corr_id
            
            return response
            
        except Exception as e:
            # Mark span as error
            span.set_error(e)
            self.tracer.finish_span(span, SpanStatus.ERROR)
            raise


class SpanContext:
    """Context manager for trace spans."""
    
    def __init__(self, tracer: Tracer, name: str, span_type: SpanType = SpanType.REQUEST):
        """Initialize span context."""
        self.tracer = tracer
        self.name = name
        self.span_type = span_type
        self.span: Optional[TraceSpan] = None
    
    def __enter__(self) -> TraceSpan:
        """Start span."""
        self.span = self.tracer.start_span(self.name, self.span_type)
        return self.span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish span."""
        if self.span:
            if exc_type is not None:
                self.span.set_error(exc_val)
                self.tracer.finish_span(self.span, SpanStatus.ERROR)
            else:
                self.tracer.finish_span(self.span, SpanStatus.OK)


class AsyncSpanContext:
    """Async context manager for trace spans."""
    
    def __init__(self, tracer: Tracer, name: str, span_type: SpanType = SpanType.REQUEST):
        """Initialize async span context."""
        self.tracer = tracer
        self.name = name
        self.span_type = span_type
        self.span: Optional[TraceSpan] = None
    
    async def __aenter__(self) -> TraceSpan:
        """Start span."""
        self.span = self.tracer.start_span(self.name, self.span_type)
        return self.span
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Finish span."""
        if self.span:
            if exc_type is not None:
                self.span.set_error(exc_val)
                self.tracer.finish_span(self.span, SpanStatus.ERROR)
            else:
                self.tracer.finish_span(self.span, SpanStatus.OK)


def trace_function(tracer: Tracer, name: Optional[str] = None, span_type: SpanType = SpanType.REQUEST):
    """Decorator for tracing function calls."""
    def decorator(func):
        function_name = name or f"{func.__module__}.{func.__name__}"
        
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                async with AsyncSpanContext(tracer, function_name, span_type) as span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                with SpanContext(tracer, function_name, span_type) as span:
                    span.set_attribute("function.name", func.__name__)
                    span.set_attribute("function.module", func.__module__)
                    return func(*args, **kwargs)
            return sync_wrapper
    
    return decorator


class TraceCollector:
    """Central collector for distributed traces."""
    
    def __init__(self):
        """Initialize trace collector."""
        self.traces: Dict[str, List[TraceSpan]] = {}
        self.max_traces = 10000  # Keep last 10k traces
        self.trace_retention_hours = 24
    
    def collect_span(self, span: TraceSpan):
        """Collect a span from a distributed service."""
        correlation_id = span.correlation_id
        
        if correlation_id not in self.traces:
            self.traces[correlation_id] = []
        
        self.traces[correlation_id].append(span)
        
        # Cleanup old traces
        self._cleanup_old_traces()
    
    def get_trace(self, correlation_id: str) -> List[TraceSpan]:
        """Get all spans for a correlation ID."""
        return self.traces.get(correlation_id, [])
    
    def get_recent_traces(self, limit: int = 100) -> Dict[str, List[TraceSpan]]:
        """Get recent traces."""
        # Sort by most recent first
        sorted_traces = sorted(
            self.traces.items(),
            key=lambda x: max(span.start_time for span in x[1]) if x[1] else datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )
        
        return dict(sorted_traces[:limit])
    
    def get_trace_summary(self, correlation_id: str) -> Optional[Dict[str, Any]]:
        """Get summary of a trace."""
        spans = self.get_trace(correlation_id)
        if not spans:
            return None
        
        # Calculate trace metrics
        start_time = min(span.start_time for span in spans)
        end_times = [span.end_time for span in spans if span.end_time]
        end_time = max(end_times) if end_times else None
        
        total_duration = (end_time - start_time).total_seconds() * 1000 if end_time else None
        
        # Count spans by status
        status_counts = {}
        for span in spans:
            status = span.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count spans by service
        service_counts = {}
        for span in spans:
            service = span.service_name
            service_counts[service] = service_counts.get(service, 0) + 1
        
        return {
            "correlation_id": correlation_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat() if end_time else None,
            "duration_ms": total_duration,
            "span_count": len(spans),
            "service_count": len(service_counts),
            "status_breakdown": status_counts,
            "service_breakdown": service_counts,
            "has_errors": status_counts.get("error", 0) > 0
        }
    
    def _cleanup_old_traces(self):
        """Remove old traces to prevent memory growth."""
        if len(self.traces) <= self.max_traces:
            return
        
        # Sort traces by age and keep only recent ones
        cutoff_time = datetime.now(timezone.utc) - timezone.timedelta(hours=self.trace_retention_hours)
        
        old_traces = []
        for correlation_id, spans in self.traces.items():
            if spans and max(span.start_time for span in spans) < cutoff_time:
                old_traces.append(correlation_id)
        
        # Remove old traces
        for correlation_id in old_traces:
            del self.traces[correlation_id]
        
        logger.debug(f"Cleaned up {len(old_traces)} old traces")


# Global tracer instances (will be initialized by services)
tracer: Optional[Tracer] = None
trace_collector: Optional[TraceCollector] = None


def init_tracing(service_name: str) -> Tracer:
    """Initialize tracing for a service."""
    global tracer
    tracer = Tracer(service_name)
    return tracer


def get_tracer() -> Optional[Tracer]:
    """Get the global tracer instance."""
    return tracer