import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import uvicorn
import json
import os

from registry import AgentRegistry
from schemas import (
    AgentRegistration, AgentStatus, CapabilityInfo, 
    HealthCheckResponse, AgentManifest
)

# Try to import tracing and alerting from agent SDK
try:
    from kenny_agent.tracing import TraceCollector, TraceSpan
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

try:
    from kenny_agent.alerting import init_alerting, get_alert_engine, AlertEngine, Alert
    ALERTING_AVAILABLE = True
except ImportError:
    ALERTING_AVAILABLE = False

try:
    from kenny_agent.analytics import init_analytics, get_analytics_engine, PerformanceAnalytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

try:
    from kenny_agent.security import init_security, get_security_monitor, SecurityMonitor, SecurityEvent
    SECURITY_AVAILABLE = True
except ImportError:
    SECURITY_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global registry, trace collector, alert engine, analytics, and security instances
registry: AgentRegistry = None
trace_collector: Optional[TraceCollector] = None
alert_engine: Optional[AlertEngine] = None
analytics_engine: Optional[PerformanceAnalytics] = None
security_monitor: Optional[SecurityMonitor] = None

# Pydantic models for trace endpoints
class TraceSpanModel(BaseModel):
    span_id: str
    correlation_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: str
    service_name: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    status: str
    attributes: Dict[str, Any] = {}
    events: List[Dict[str, Any]] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global registry, trace_collector, alert_engine, analytics_engine, security_monitor
    
    # Startup
    logger.info("Starting Agent Registry Service")
    registry = AgentRegistry()
    
    # Initialize trace collector if tracing is available
    if TRACING_AVAILABLE:
        trace_collector = TraceCollector()
        logger.info("Trace collector initialized")
    else:
        logger.warning("Tracing not available - traces will not be collected")
    
    # Initialize alert engine if alerting is available  
    if ALERTING_AVAILABLE:
        alert_engine = init_alerting()
        logger.info("Alert engine initialized with default rules")
        
        # Set up background task to monitor health metrics and generate alerts
        asyncio.create_task(alert_monitoring_loop())
    else:
        logger.warning("Alerting not available - no alert monitoring")
    
    # Initialize analytics engine if analytics is available
    if ANALYTICS_AVAILABLE:
        analytics_engine = init_analytics()
        logger.info("Analytics engine initialized")
        
        # Set up background task to collect performance metrics
        asyncio.create_task(analytics_collection_loop())
    else:
        logger.warning("Analytics not available - no performance trending")
    
    # Initialize security monitor if security is available
    if SECURITY_AVAILABLE:
        security_monitor = init_security()
        logger.info("Security monitor initialized with default rules")
    else:
        logger.warning("Security monitoring not available - no security controls")
    
    logger.info("Agent Registry Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Registry Service")
    if registry:
        # Stop all health monitoring tasks
        for agent_id in list(registry.agents.keys()):
            await registry.unregister_agent(agent_id)
    logger.info("Agent Registry Service shutdown complete")


async def alert_monitoring_loop():
    """Background task to monitor system health and generate alerts."""
    global registry, alert_engine
    
    logger.info("Starting alert monitoring loop")
    
    while True:
        try:
            if registry and alert_engine:
                # Get system health data
                health_dashboard = await registry.get_enhanced_health_dashboard()
                
                # Evaluate system-level metrics
                system_data = {
                    "service_name": "agent_registry",
                    "component": "system_monitor"
                }
                
                system_overview = health_dashboard.get("system_overview", {})
                perf_overview = health_dashboard.get("performance_overview", {})
                
                # Add system-level metrics
                if "average_response_time_ms" in perf_overview:
                    system_data["response_time_ms"] = perf_overview["average_response_time_ms"]
                
                if "average_success_rate_percent" in perf_overview:
                    system_data["success_rate_percent"] = perf_overview["average_success_rate_percent"]
                
                if "total_error_count" in perf_overview:
                    system_data["error_count"] = perf_overview["total_error_count"]
                
                # Evaluate system-level alerts
                alert_engine.evaluate_data(system_data)
                
                # Evaluate agent-specific metrics
                agent_details = health_dashboard.get("agent_details", {})
                for agent_id, agent_data in agent_details.items():
                    if "performance_summary" in agent_data:
                        perf_summary = agent_data["performance_summary"]
                        current_metrics = perf_summary.get("current_metrics", {})
                        sla_compliance = perf_summary.get("sla_compliance", {})
                        trend_analysis = perf_summary.get("trend_analysis", {})
                        
                        # Prepare agent data for evaluation
                        agent_eval_data = {
                            "service_name": agent_id,
                            "component": "agent_performance",
                            "agent_id": agent_id
                        }
                        
                        # Add performance metrics
                        agent_eval_data.update(current_metrics)
                        
                        # Add SLA compliance status
                        agent_eval_data["sla_compliant"] = sla_compliance.get("overall_compliant", True)
                        
                        # Add trend information
                        if "trend" in trend_analysis:
                            agent_eval_data["trend"] = trend_analysis["trend"]
                            agent_eval_data["change_percent"] = trend_analysis.get("change_percent", 0.0)
                        
                        # Add health status
                        agent_status = registry.agents.get(agent_id)
                        if agent_status:
                            agent_eval_data["is_healthy"] = agent_status.is_healthy
                            if not agent_status.is_healthy and agent_status.last_error:
                                agent_eval_data["error_message"] = agent_status.last_error
                        
                        # Evaluate agent alerts
                        alert_engine.evaluate_data(agent_eval_data)
                
            # Wait before next evaluation cycle
            await asyncio.sleep(30)  # Check every 30 seconds
            
        except Exception as e:
            logger.error(f"Error in alert monitoring loop: {e}")
            await asyncio.sleep(60)  # Wait longer on error


async def analytics_collection_loop():
    """Background task to collect performance metrics for analytics."""
    global registry, analytics_engine
    
    logger.info("Starting analytics collection loop")
    
    while True:
        try:
            if registry and analytics_engine:
                # Get system health data
                health_dashboard = await registry.get_enhanced_health_dashboard()
                
                # Collect system-level metrics
                system_overview = health_dashboard.get("system_overview", {})
                perf_overview = health_dashboard.get("performance_overview", {})
                
                # Record system metrics
                if "average_response_time_ms" in perf_overview:
                    analytics_engine.record_performance_metric(
                        "system_response_time_ms",
                        perf_overview["average_response_time_ms"],
                        {"component": "system"}
                    )
                
                if "average_success_rate_percent" in perf_overview:
                    analytics_engine.record_performance_metric(
                        "system_success_rate_percent", 
                        perf_overview["average_success_rate_percent"],
                        {"component": "system"}
                    )
                
                if "total_error_count" in perf_overview:
                    analytics_engine.record_performance_metric(
                        "system_error_count",
                        perf_overview["total_error_count"],
                        {"component": "system"}
                    )
                
                # Record system health status
                healthy_agents = system_overview.get("healthy_agents", 0)
                total_agents = system_overview.get("total_agents", 0)
                
                if total_agents > 0:
                    health_percentage = (healthy_agents / total_agents) * 100
                    analytics_engine.record_performance_metric(
                        "system_health_percent",
                        health_percentage,
                        {"component": "system", "healthy_agents": healthy_agents, "total_agents": total_agents}
                    )
                
                # Collect agent-specific metrics
                agent_details = health_dashboard.get("agent_details", {})
                for agent_id, agent_data in agent_details.items():
                    if "performance_summary" in agent_data:
                        perf_summary = agent_data["performance_summary"]
                        current_metrics = perf_summary.get("current_metrics", {})
                        
                        # Record agent metrics
                        for metric_name, value in current_metrics.items():
                            analytics_engine.record_performance_metric(
                                f"agent_{metric_name}",
                                value,
                                {"component": "agent", "agent_id": agent_id}
                            )
                
            # Wait before next collection cycle
            await asyncio.sleep(60)  # Collect every minute
            
        except Exception as e:
            logger.error(f"Error in analytics collection loop: {e}")
            await asyncio.sleep(120)  # Wait longer on error


# Create FastAPI app
app = FastAPI(
    title="Kenny Agent Registry",
    description="Central service for agent registration and capability discovery",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict to local domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for security dashboard
static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.get("/health")
async def health_check() -> HealthCheckResponse:
    """Health check endpoint for the registry service"""
    if registry is None:
        return HealthCheckResponse(
            status="starting",
            timestamp="unknown"
        )
    
    try:
        system_health = await registry.get_system_health()
        return HealthCheckResponse(
            status="healthy",
            timestamp=system_health["timestamp"]
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp="unknown"
        )


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Kenny Agent Registry",
        "version": "1.0.0",
        "status": "operational" if registry else "starting",
        "endpoints": {
            "health": "/health",
            "agents": "/agents",
            "capabilities": "/capabilities",
            "system_health": "/system/health",
            "performance_dashboard": "/system/health/dashboard",
            "dashboard_streaming": "/system/health/dashboard/stream",
            "traces": "/traces",
            "trace_collection": "/traces/collect",
            "trace_streaming": "/traces/stream/live",
            "alerts": "/alerts",
            "alert_summary": "/alerts/summary",
            "alert_streaming": "/alerts/stream/live",
            "analytics": "/analytics",
            "analytics_dashboard": "/analytics/dashboard",
            "security": "/security",
            "security_dashboard": "/security/dashboard",
            "security_events": "/security/events",
            "security_events_streaming": "/security/events/stream",
            "security_incidents": "/security/incidents",
            "incident_management": "/security/incidents/management/dashboard",
            "compliance_summary": "/security/compliance/summary",
            "security_analytics": "/security/analytics/dashboard",
            "security_metrics": "/security/metrics/collect",
            "security_trends": "/security/trends",
            "security_forecast": "/security/forecast",
            "response_rules": "/security/response/rules",
            "response_actions": "/security/response/actions/history",
            "response_dashboard": "/security/response/dashboard",
            "security_dashboard_ui": "/security/ui",
            "enforcement_status": "/security/enforcement/status",
            "enforcement_block_service": "/security/enforcement/block/service",
            "enforcement_block_destination": "/security/enforcement/block/destination",
            "enforcement_unblock_service": "/security/enforcement/unblock/service/{service_id}",
            "enforcement_unblock_destination": "/security/enforcement/unblock/destination",
            "enforcement_bypass_request": "/security/enforcement/bypass/request",
            "enforcement_bypass_approve": "/security/enforcement/bypass/{bypass_id}/approve"
        }
    }


@app.post("/agents/register", response_model=AgentStatus, status_code=status.HTTP_201_CREATED)
async def register_agent(registration: AgentRegistration) -> AgentStatus:
    """Register a new agent with the registry"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        agent_status = await registry.register_agent(registration)
        logger.info(f"Agent {registration.manifest.agent_id} registered successfully")
        return agent_status
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to register agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during agent registration"
        )


@app.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unregister_agent(agent_id: str):
    """Unregister an agent from the registry"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        success = await registry.unregister_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        logger.info(f"Agent {agent_id} unregistered successfully")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unregister agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during agent unregistration"
        )


@app.get("/agents", response_model=list[AgentStatus])
async def list_agents():
    """List all registered agents"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        agents = await registry.list_agents()
        return agents
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while listing agents"
        )


@app.get("/agents/{agent_id}", response_model=AgentStatus)
async def get_agent(agent_id: str) -> AgentStatus:
    """Get details of a specific agent"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent {agent_id} not found"
            )
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving agent"
        )


@app.get("/capabilities", response_model=dict[str, list[CapabilityInfo]])
async def get_capabilities():
    """Get all available capabilities indexed by verb"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        capabilities = await registry.get_capabilities()
        return capabilities
    except Exception as e:
        logger.error(f"Failed to get capabilities: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving capabilities"
        )


@app.get("/capabilities/{verb}", response_model=list[CapabilityInfo])
async def get_capability(verb: str):
    """Get all agents that provide a specific capability"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        capabilities = await registry.get_capability(verb)
        return capabilities
    except Exception as e:
        logger.error(f"Failed to get capability {verb}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving capability"
        )


@app.get("/capabilities/{verb}/find")
async def find_agents_for_capability(
    verb: str, 
    data_scope: str = None
) -> list[CapabilityInfo]:
    """Find agents that can handle a specific capability and optionally data scope"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        capabilities = await registry.find_agents_for_capability(verb, data_scope)
        return capabilities
    except Exception as e:
        logger.error(f"Failed to find agents for capability {verb}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while finding agents for capability"
        )


@app.get("/system/health")
async def get_system_health():
    """Get overall system health status"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        health = await registry.get_system_health()
        return health
    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving system health"
        )


@app.get("/system/health/dashboard")
async def get_enhanced_health_dashboard():
    """Get comprehensive health dashboard with performance metrics from all agents"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    try:
        dashboard = await registry.get_enhanced_health_dashboard()
        return dashboard
    except Exception as e:
        logger.error(f"Failed to get enhanced health dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving health dashboard"
        )


@app.get("/system/health/dashboard/stream")
async def stream_health_dashboard():
    """Stream live health dashboard updates as Server-Sent Events"""
    if registry is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Registry service is starting up"
        )
    
    async def generate_dashboard_updates():
        """Generate live dashboard updates"""
        import asyncio
        
        last_update_time = 0.0
        
        while True:
            try:
                current_time = asyncio.get_event_loop().time()
                
                # Get enhanced dashboard data
                dashboard = await registry.get_enhanced_health_dashboard()
                
                # Add streaming metadata
                dashboard["streaming_info"] = {
                    "last_update": current_time,
                    "update_interval_seconds": 5.0,
                    "is_live": True
                }
                
                # Send dashboard update
                event_data = {
                    "type": "dashboard_update",
                    "data": dashboard,
                    "timestamp": current_time
                }
                
                yield f"data: {json.dumps(event_data)}\n\n"
                
                last_update_time = current_time
                
                # Wait before next update
                await asyncio.sleep(5.0)  # Update every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in dashboard streaming: {e}")
                error_event = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await asyncio.sleep(10.0)  # Wait longer on error
    
    return StreamingResponse(
        generate_dashboard_updates(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# Security endpoints
@app.get("/security/dashboard")
async def get_security_dashboard(hours: int = 24):
    """Get comprehensive security compliance dashboard"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        dashboard = security_monitor.get_security_dashboard(hours)
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving security dashboard"
        )


@app.get("/security/events")
async def get_security_events(hours: int = 24, severity: Optional[str] = None, event_type: Optional[str] = None):
    """Get security events with optional filtering"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        # Parse filters
        severity_filter = None
        if severity:
            from kenny_agent.security import SecuritySeverity
            try:
                severity_filter = SecuritySeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity level: {severity}"
                )
        
        event_type_filter = None
        if event_type:
            from kenny_agent.security import SecurityEventType
            try:
                event_type_filter = SecurityEventType(event_type.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}"
                )
        
        events = security_monitor.event_collector.get_events(hours, severity_filter, event_type_filter)
        event_dicts = [event.to_dict() for event in events]
        
        return {
            "events": event_dicts,
            "total_count": len(event_dicts),
            "time_period_hours": hours,
            "severity_filter": severity,
            "event_type_filter": event_type
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security events: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving security events"
        )


@app.get("/security/egress/rules")
async def get_egress_rules():
    """Get network egress rules configuration"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        rules = []
        for rule in security_monitor.egress_monitor.rules.values():
            rules.append({
                "rule_id": rule.rule_id,
                "name": rule.name,
                "enabled": rule.enabled,
                "allowed_domains": rule.allowed_domains,
                "allowed_ips": rule.allowed_ips,
                "ports": rule.ports
            })
        
        return {
            "rules": rules,
            "total_count": len(rules),
            "enabled_count": len([r for r in security_monitor.egress_monitor.rules.values() if r.enabled])
        }
    except Exception as e:
        logger.error(f"Failed to get egress rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving egress rules"
        )


@app.post("/security/egress/check")
async def check_egress_request(egress_data: Dict[str, Any]):
    """Check if network egress request is allowed"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    source_service = egress_data.get("source_service")
    destination = egress_data.get("destination")
    port = egress_data.get("port")
    correlation_id = egress_data.get("correlation_id")
    
    if not source_service or not destination:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_service and destination are required"
        )
    
    try:
        allowed = security_monitor.check_network_egress(source_service, destination, port, correlation_id)
        
        return {
            "allowed": allowed,
            "source_service": source_service,
            "destination": destination,
            "port": port,
            "correlation_id": correlation_id,
            "checked_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to check egress request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while checking egress request"
        )


@app.post("/security/data-access/log")
async def log_data_access(access_data: Dict[str, Any]):
    """Log data access operation for security monitoring"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    service_name = access_data.get("service_name")
    resource = access_data.get("resource")
    operation = access_data.get("operation")
    user_id = access_data.get("user_id")
    data_size = access_data.get("data_size")
    correlation_id = access_data.get("correlation_id")
    
    if not service_name or not resource or not operation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="service_name, resource, and operation are required"
        )
    
    try:
        security_monitor.log_data_access(service_name, resource, operation, user_id, data_size, correlation_id)
        
        return {
            "status": "logged",
            "service_name": service_name,
            "resource": resource,
            "operation": operation,
            "logged_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to log data access: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while logging data access"
        )


@app.get("/security/compliance/summary")
async def get_security_compliance_summary():
    """Get security compliance summary and status"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        event_summary = security_monitor.event_collector.get_event_summary()
        
        # Calculate compliance metrics
        total_critical_high = event_summary.get("critical_count", 0) + event_summary.get("high_count", 0)
        total_events = event_summary.get("total_events_24h", 0)
        
        # Simple compliance scoring (fewer critical/high events = better compliance)
        if total_critical_high == 0:
            compliance_score = 100
            compliance_status = "compliant"
        elif total_critical_high <= 5:
            compliance_score = max(70, 100 - (total_critical_high * 6))
            compliance_status = "mostly_compliant"
        elif total_critical_high <= 15:
            compliance_score = max(40, 70 - ((total_critical_high - 5) * 3))
            compliance_status = "partially_compliant"
        else:
            compliance_score = max(0, 40 - ((total_critical_high - 15) * 2))
            compliance_status = "non_compliant"
        
        return {
            "compliance_score": compliance_score,
            "compliance_status": compliance_status,
            "event_summary": event_summary,
            "egress_rules_count": len(security_monitor.egress_monitor.rules),
            "egress_rules_enabled": len([r for r in security_monitor.egress_monitor.rules.values() if r.enabled]),
            "assessment_timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get compliance summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving compliance summary"
        )


@app.get("/security/events/stream")
async def stream_live_security_events():
    """Stream live security events as Server-Sent Events"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    async def generate_live_security_events():
        """Generate live security event updates"""
        import asyncio
        
        last_event_count = 0
        last_incident_count = 0
        
        while True:
            try:
                # Get recent security events
                recent_events = security_monitor.event_collector.get_events(hours=1)
                current_event_count = len(recent_events)
                
                # Get recent incidents
                recent_incidents = security_monitor.event_collector.get_incidents(hours=1)
                current_incident_count = len(recent_incidents)
                
                # Check for new security events
                if current_event_count > last_event_count:
                    new_events = recent_events[:current_event_count - last_event_count]
                    new_event_dicts = [event.to_dict() for event in new_events]
                    
                    if new_event_dicts:
                        event_data = {
                            "type": "new_security_events",
                            "events": new_event_dicts,
                            "count": len(new_event_dicts),
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                    
                    last_event_count = current_event_count
                
                # Check for new incidents
                if current_incident_count > last_incident_count:
                    new_incidents = recent_incidents[:current_incident_count - last_incident_count]
                    new_incident_dicts = [incident.to_dict() for incident in new_incidents]
                    
                    if new_incident_dicts:
                        incident_data = {
                            "type": "new_security_incidents",
                            "incidents": new_incident_dicts,
                            "count": len(new_incident_dicts),
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        yield f"data: {json.dumps(incident_data)}\n\n"
                    
                    last_incident_count = current_incident_count
                
                # Send periodic security status updates
                if int(asyncio.get_event_loop().time()) % 30 == 0:  # Every 30 seconds
                    security_status = {
                        "type": "security_status_update",
                        "status": {
                            "total_events_1h": current_event_count,
                            "total_incidents_1h": current_incident_count,
                            "compliance_summary": security_monitor.validate_privacy_compliance("status_check", {})
                        },
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    yield f"data: {json.dumps(security_status)}\n\n"
                
                # Wait before next check
                await asyncio.sleep(3.0)  # Check every 3 seconds for rapid security response
                
            except Exception as e:
                logger.error(f"Error in live security event streaming: {e}")
                error_event = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await asyncio.sleep(10.0)  # Wait longer on error
    
    return StreamingResponse(
        generate_live_security_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/security/incidents")
async def get_security_incidents(hours: int = 24, status: Optional[str] = None):
    """Get security incidents with optional filtering"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        incidents = security_monitor.event_collector.get_incidents(hours=hours, status=status)
        incident_dicts = [incident.to_dict() for incident in incidents]
        
        return {
            "incidents": incident_dicts,
            "total_count": len(incident_dicts),
            "time_period_hours": hours,
            "status_filter": status
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security incidents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving security incidents"
        )


@app.get("/security/incidents/management/dashboard")
async def get_incident_management_dashboard(hours: int = 24):
    """Get incident management dashboard"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        dashboard = security_monitor.get_incident_management_dashboard(hours)
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get incident management dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving incident management dashboard"
        )


@app.get("/security/analytics/dashboard")
async def get_security_analytics_dashboard(hours: int = 24):
    """Get comprehensive security analytics dashboard with metrics and trends"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        dashboard = security_monitor.get_security_analytics_dashboard(hours)
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security analytics dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving security analytics dashboard"
        )


@app.get("/security/metrics/collect")
async def collect_security_metrics():
    """Collect current security metrics snapshot"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        metrics = security_monitor.collect_security_metrics()
        return {
            "status": "collected",
            "metrics": metrics,
            "collected_at": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to collect security metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while collecting security metrics"
        )


@app.get("/security/trends")
async def get_security_trends(hours: int = 24):
    """Get security trends analysis"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        trends = security_monitor.get_security_trends(hours)
        return trends
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security trends: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving security trends"
        )


@app.get("/security/forecast")
async def get_security_forecast(hours_ahead: int = 24):
    """Get security forecast based on current trends"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours_ahead < 1 or hours_ahead > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours ahead must be between 1 and 168"
            )
        
        forecast = security_monitor.get_security_forecast(hours_ahead)
        return forecast
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get security forecast: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving security forecast"
        )


@app.post("/security/incidents/{incident_id}/update")
async def update_security_incident(incident_id: str, update_data: Dict[str, Any]):
    """Update security incident status and details"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    status_value = update_data.get("status")
    assigned_to = update_data.get("assigned_to")
    resolution_notes = update_data.get("resolution_notes")
    
    if not status_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="status is required"
        )
    
    valid_statuses = ["open", "investigating", "resolved", "false_positive"]
    if status_value not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"status must be one of: {', '.join(valid_statuses)}"
        )
    
    try:
        success = security_monitor.event_collector.update_incident_status(
            incident_id, status_value, assigned_to, resolution_notes
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )
        
        return {
            "status": "updated",
            "incident_id": incident_id,
            "new_status": status_value,
            "assigned_to": assigned_to,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update incident {incident_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while updating incident"
        )


@app.get("/security/incidents/{incident_id}")
async def get_security_incident_details(incident_id: str):
    """Get detailed information about a specific security incident"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        incident = security_monitor.event_collector.get_incident(incident_id)
        
        if not incident:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Incident {incident_id} not found"
            )
        
        # Get related events
        related_events = []
        for event_id in incident.event_ids:
            for event in security_monitor.event_collector.get_events(hours=168):  # Look back 1 week
                if event.event_id == event_id:
                    related_events.append(event.to_dict())
                    break
        
        return {
            "incident": incident.to_dict(),
            "related_events": related_events,
            "event_count": len(related_events)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get incident details for {incident_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving incident details"
        )


@app.get("/security/response/rules")
async def get_automated_response_rules():
    """Get all automated response rules"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        rules = security_monitor.response_engine.get_response_rules()
        rule_dicts = []
        
        for rule in rules:
            rule_dict = {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "priority": rule.priority,
                "triggers": rule.triggers,
                "actions": [
                    {
                        "action_id": action.action_id,
                        "action_type": action.action_type,
                        "description": action.description,
                        "enabled": action.enabled,
                        "cooldown_minutes": action.cooldown_minutes,
                        "parameters": action.parameters
                    }
                    for action in rule.actions
                ]
            }
            rule_dicts.append(rule_dict)
        
        return {
            "rules": rule_dicts,
            "total_count": len(rule_dicts),
            "enabled_count": len([r for r in rules if r.enabled])
        }
    except Exception as e:
        logger.error(f"Failed to get response rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving response rules"
        )


@app.get("/security/response/actions/history")
async def get_response_action_history(hours: int = 24):
    """Get automated response action execution history"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        action_history = security_monitor.get_response_action_history(hours)
        
        return {
            "actions": action_history,
            "total_count": len(action_history),
            "time_period_hours": hours,
            "successful_count": len([a for a in action_history if a.get("status") == "completed"]),
            "failed_count": len([a for a in action_history if a.get("status") == "failed"])
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get response action history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving response action history"
        )


@app.get("/security/response/dashboard")
async def get_automated_response_dashboard(hours: int = 24):
    """Get automated response dashboard"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        dashboard = security_monitor.get_automated_response_dashboard(hours)
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get automated response dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving automated response dashboard"
        )


@app.get("/security/enforcement/status")
async def get_network_enforcement_status():
    """Get network enforcement status and statistics"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        status = security_monitor.egress_monitor.get_enforcement_status()
        return {
            "enforcement_status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get network enforcement status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving enforcement status"
        )


@app.post("/security/enforcement/block/service")
async def block_service_egress(block_data: Dict[str, Any]):
    """Block a service from making egress connections"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        service_id = block_data.get("service_id")
        duration_minutes = block_data.get("duration_minutes", 60)
        reason = block_data.get("reason", "Manual block")
        triggered_by = block_data.get("triggered_by", "admin")
        
        if not service_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id is required"
            )
        
        if duration_minutes < 1 or duration_minutes > 1440:  # Max 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duration_minutes must be between 1 and 1440"
            )
        
        block_id = security_monitor.egress_monitor.block_service(
            service_id, duration_minutes, reason, triggered_by
        )
        
        return {
            "status": "service_blocked",
            "service_id": service_id,
            "block_id": block_id,
            "duration_minutes": duration_minutes,
            "reason": reason,
            "blocked_at": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to block service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while blocking service"
        )


@app.post("/security/enforcement/block/destination")
async def block_destination_egress(block_data: Dict[str, Any]):
    """Block access to a specific destination"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        destination = block_data.get("destination")
        port = block_data.get("port")
        duration_minutes = block_data.get("duration_minutes", 30)
        reason = block_data.get("reason", "Manual block")
        triggered_by = block_data.get("triggered_by", "admin")
        
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="destination is required"
            )
        
        if duration_minutes < 1 or duration_minutes > 1440:  # Max 24 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duration_minutes must be between 1 and 1440"
            )
        
        block_id = security_monitor.egress_monitor.block_destination(
            destination, port, duration_minutes, reason, triggered_by
        )
        
        return {
            "status": "destination_blocked",
            "destination": destination,
            "port": port,
            "block_id": block_id,
            "duration_minutes": duration_minutes,
            "reason": reason,
            "blocked_at": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to block destination: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while blocking destination"
        )


@app.post("/security/enforcement/unblock/service/{service_id}")
async def unblock_service_egress(service_id: str):
    """Manually unblock a service"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        success = security_monitor.egress_monitor.unblock_service(service_id)
        
        if success:
            return {
                "status": "service_unblocked",
                "service_id": service_id,
                "unblocked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Service {service_id} is not currently blocked"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unblock service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while unblocking service"
        )


@app.post("/security/enforcement/unblock/destination")
async def unblock_destination_egress(unblock_data: Dict[str, Any]):
    """Manually unblock a destination"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        destination = unblock_data.get("destination")
        port = unblock_data.get("port")
        
        if not destination:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="destination is required"
            )
        
        success = security_monitor.egress_monitor.unblock_destination(destination, port)
        
        if success:
            return {
                "status": "destination_unblocked",
                "destination": destination,
                "port": port,
                "unblocked_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            destination_key = f"{destination}:{port or 'any'}"
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Destination {destination_key} is not currently blocked"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unblock destination: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while unblocking destination"
        )


@app.post("/security/enforcement/bypass/request")
async def create_bypass_request(request_data: Dict[str, Any]):
    """Create a bypass request for blocked destinations"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        service_id = request_data.get("service_id")
        destination = request_data.get("destination")
        port = request_data.get("port")
        justification = request_data.get("justification", "")
        duration_hours = request_data.get("duration_hours", 1)
        
        if not service_id or not destination:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="service_id and destination are required"
            )
        
        if duration_hours < 1 or duration_hours > 72:  # Max 3 days
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="duration_hours must be between 1 and 72"
            )
        
        bypass_id = security_monitor.egress_monitor.create_bypass_request(
            service_id, destination, port, justification, duration_hours
        )
        
        return {
            "status": "bypass_request_created",
            "bypass_id": bypass_id,
            "service_id": service_id,
            "destination": destination,
            "port": port,
            "justification": justification,
            "duration_hours": duration_hours,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create bypass request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while creating bypass request"
        )


@app.post("/security/enforcement/bypass/{bypass_id}/approve")
async def approve_bypass_request(bypass_id: str, approval_data: Dict[str, Any]):
    """Approve a bypass request"""
    if not SECURITY_AVAILABLE or security_monitor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Security monitoring service not available"
        )
    
    try:
        approved_by = approval_data.get("approved_by", "admin")
        
        success = security_monitor.egress_monitor.approve_bypass_request(bypass_id, approved_by)
        
        if success:
            return {
                "status": "bypass_request_approved",
                "bypass_id": bypass_id,
                "approved_by": approved_by,
                "approved_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bypass request {bypass_id} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve bypass request: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while approving bypass request"
        )


# Analytics endpoints
@app.get("/analytics/dashboard")
async def get_analytics_dashboard(hours: int = 24):
    """Get comprehensive performance analytics dashboard"""
    if not ANALYTICS_AVAILABLE or analytics_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service not available"
        )
    
    try:
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        dashboard = analytics_engine.get_performance_dashboard(hours)
        return dashboard
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analytics dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving analytics dashboard"
        )


@app.get("/analytics/metrics/{metric_name}")
async def get_metric_data(metric_name: str, hours: int = 24, resolution_minutes: int = 5):
    """Get historical data for a specific metric"""
    if not ANALYTICS_AVAILABLE or analytics_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        if resolution_minutes < 1 or resolution_minutes > 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Resolution must be between 1 and 60 minutes"
            )
        
        chart_data = analytics_engine.get_metric_chart_data(metric_name, hours, resolution_minutes)
        return chart_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get metric data for {metric_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving metric data"
        )


@app.get("/analytics/anomalies/{metric_name}")
async def get_metric_anomalies(metric_name: str, hours: int = 24, std_dev_threshold: float = 2.0):
    """Detect anomalies in metric data"""
    if not ANALYTICS_AVAILABLE or analytics_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        if std_dev_threshold < 1.0 or std_dev_threshold > 5.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Standard deviation threshold must be between 1.0 and 5.0"
            )
        
        anomalies = analytics_engine.get_anomalies(metric_name, hours, std_dev_threshold)
        return {
            "metric_name": metric_name,
            "time_period_hours": hours,
            "std_dev_threshold": std_dev_threshold,
            "anomalies": anomalies,
            "anomaly_count": len(anomalies)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get anomalies for {metric_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while detecting anomalies"
        )


@app.post("/analytics/thresholds/{metric_name}")
async def set_metric_threshold(metric_name: str, threshold_data: Dict[str, float]):
    """Set threshold for a performance metric"""
    if not ANALYTICS_AVAILABLE or analytics_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service not available"
        )
    
    threshold_value = threshold_data.get("threshold")
    if threshold_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold is required"
        )
    
    if threshold_value <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="threshold must be greater than 0"
        )
    
    try:
        analytics_engine.set_threshold(metric_name, threshold_value)
        return {
            "metric_name": metric_name,
            "threshold": threshold_value,
            "status": "updated"
        }
    except Exception as e:
        logger.error(f"Failed to set threshold for {metric_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while setting threshold"
        )


@app.get("/analytics/capacity")
async def get_capacity_analysis(hours: int = 24):
    """Get capacity planning analysis"""
    if not ANALYTICS_AVAILABLE or analytics_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Analytics service not available"
        )
    
    try:
        if hours < 1 or hours > 168:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        dashboard = analytics_engine.get_performance_dashboard(hours)
        capacity_analysis = dashboard.get("capacity_analysis", {})
        
        return {
            "time_period_hours": hours,
            "capacity_analysis": capacity_analysis,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get capacity analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving capacity analysis"
        )


# Alert endpoints
@app.get("/alerts")
async def get_active_alerts(severity: Optional[str] = None):
    """Get active alerts, optionally filtered by severity"""
    if not ALERTING_AVAILABLE or alert_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerting service not available"
        )
    
    try:
        from kenny_agent.alerting import AlertSeverity
        
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity level: {severity}"
                )
        
        alerts = alert_engine.get_active_alerts(severity_filter)
        alert_dicts = [alert.to_dict() for alert in alerts]
        
        return {
            "alerts": alert_dicts,
            "total_count": len(alert_dicts),
            "severity_filter": severity
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving alerts"
        )


@app.get("/alerts/summary") 
async def get_alert_summary():
    """Get summary of alert statistics"""
    if not ALERTING_AVAILABLE or alert_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerting service not available"
        )
    
    try:
        summary = alert_engine.get_alert_summary()
        return summary
    except Exception as e:
        logger.error(f"Failed to get alert summary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving alert summary"
        )


@app.get("/alerts/history")
async def get_alert_history(hours: int = 24, severity: Optional[str] = None):
    """Get alert history for the specified time period"""
    if not ALERTING_AVAILABLE or alert_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerting service not available"
        )
    
    try:
        from kenny_agent.alerting import AlertSeverity
        
        if hours < 1 or hours > 168:  # Max 1 week
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hours must be between 1 and 168"
            )
        
        severity_filter = None
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid severity level: {severity}"
                )
        
        alerts = alert_engine.get_alert_history(hours, severity_filter)
        alert_dicts = [alert.to_dict() for alert in alerts]
        
        return {
            "alerts": alert_dicts,
            "total_count": len(alert_dicts),
            "time_period_hours": hours,
            "severity_filter": severity
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get alert history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving alert history"
        )


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, acknowledge_data: Dict[str, str]):
    """Acknowledge an alert"""
    if not ALERTING_AVAILABLE or alert_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerting service not available"
        )
    
    acknowledged_by = acknowledge_data.get("acknowledged_by")
    notes = acknowledge_data.get("notes")
    
    if not acknowledged_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="acknowledged_by is required"
        )
    
    try:
        success = alert_engine.acknowledge_alert(alert_id, acknowledged_by, notes)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        return {
            "status": "acknowledged",
            "alert_id": alert_id,
            "acknowledged_by": acknowledged_by
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while acknowledging alert"
        )


@app.post("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str, resolve_data: Dict[str, str]):
    """Resolve an alert"""
    if not ALERTING_AVAILABLE or alert_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerting service not available"
        )
    
    resolved_by = resolve_data.get("resolved_by")
    resolution_notes = resolve_data.get("resolution_notes")
    
    if not resolved_by or not resolution_notes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resolved_by and resolution_notes are required"
        )
    
    try:
        success = alert_engine.resolve_alert(alert_id, resolved_by, resolution_notes)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Alert {alert_id} not found"
            )
        
        return {
            "status": "resolved",
            "alert_id": alert_id,
            "resolved_by": resolved_by
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while resolving alert"
        )


@app.get("/alerts/stream/live")
async def stream_live_alerts():
    """Stream live alerts as Server-Sent Events"""
    if not ALERTING_AVAILABLE or alert_engine is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alerting service not available"
        )
    
    async def generate_live_alerts():
        """Generate live alert updates"""
        import asyncio
        
        last_alert_count = 0
        
        while True:
            try:
                # Get recent alerts
                alerts = alert_engine.get_active_alerts()
                current_count = len(alerts)
                
                # Check for new alerts
                if current_count > last_alert_count:
                    # Send new alerts
                    new_alerts = alerts[:current_count - last_alert_count]
                    new_alert_dicts = [alert.to_dict() for alert in new_alerts]
                    
                    if new_alert_dicts:
                        event_data = {
                            "type": "new_alerts",
                            "alerts": new_alert_dicts,
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                    
                    last_alert_count = current_count
                elif current_count < last_alert_count:
                    # Some alerts were resolved/acknowledged
                    event_data = {
                        "type": "alerts_updated",
                        "active_count": current_count,
                        "timestamp": asyncio.get_event_loop().time()
                    }
                    yield f"data: {json.dumps(event_data)}\n\n"
                    last_alert_count = current_count
                
                # Wait before next check
                await asyncio.sleep(2.0)
                
            except Exception as e:
                logger.error(f"Error in live alert streaming: {e}")
                error_event = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await asyncio.sleep(10.0)  # Wait longer on error
    
    return StreamingResponse(
        generate_live_alerts(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


# Tracing endpoints
@app.post("/traces/collect", status_code=status.HTTP_202_ACCEPTED)
async def collect_trace_span(span_data: TraceSpanModel):
    """Collect a trace span from distributed services"""
    if not TRACING_AVAILABLE or trace_collector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tracing service not available"
        )
    
    try:
        # Convert span data to TraceSpan object
        from kenny_agent.tracing import TraceSpan, SpanType, SpanStatus
        from datetime import datetime, timezone
        
        span = TraceSpan(
            span_id=span_data.span_id,
            correlation_id=span_data.correlation_id,
            parent_span_id=span_data.parent_span_id,
            name=span_data.name,
            span_type=SpanType(span_data.span_type),
            service_name=span_data.service_name,
            start_time=datetime.fromisoformat(span_data.start_time.replace("Z", "+00:00")),
            end_time=datetime.fromisoformat(span_data.end_time.replace("Z", "+00:00")) if span_data.end_time else None,
            duration_ms=span_data.duration_ms,
            status=SpanStatus(span_data.status),
            attributes=span_data.attributes,
            events=span_data.events
        )
        
        # Collect the span
        trace_collector.collect_span(span)
        
        logger.debug(f"Collected trace span {span_data.span_id} from {span_data.service_name}")
        return {"status": "accepted", "span_id": span_data.span_id}
        
    except Exception as e:
        logger.error(f"Failed to collect trace span: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid span data: {str(e)}"
        )


@app.get("/traces")
async def get_recent_traces(limit: int = 50):
    """Get recent traces with summary information"""
    if not TRACING_AVAILABLE or trace_collector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tracing service not available"
        )
    
    try:
        traces = trace_collector.get_recent_traces(limit)
        
        # Generate summaries for each trace
        trace_summaries = []
        for correlation_id, spans in traces.items():
            summary = trace_collector.get_trace_summary(correlation_id)
            if summary:
                trace_summaries.append(summary)
        
        return {
            "traces": trace_summaries,
            "total_count": len(trace_summaries)
        }
    except Exception as e:
        logger.error(f"Failed to get traces: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving traces"
        )


@app.get("/traces/{correlation_id}")
async def get_trace_details(correlation_id: str):
    """Get detailed information about a specific trace"""
    if not TRACING_AVAILABLE or trace_collector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tracing service not available"
        )
    
    try:
        spans = trace_collector.get_trace(correlation_id)
        if not spans:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trace {correlation_id} not found"
            )
        
        # Convert spans to dictionaries
        span_dicts = [span.to_dict() for span in spans]
        
        # Get trace summary
        summary = trace_collector.get_trace_summary(correlation_id)
        
        return {
            "summary": summary,
            "spans": span_dicts,
            "span_count": len(spans)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trace details for {correlation_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving trace details"
        )


@app.get("/traces/stream/live")
async def stream_live_traces():
    """Stream live trace summaries as Server-Sent Events"""
    if not TRACING_AVAILABLE or trace_collector is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tracing service not available"
        )
    
    async def generate_live_traces():
        """Generate live trace updates"""
        import asyncio
        
        last_trace_count = 0
        
        while True:
            try:
                # Get recent traces
                traces = trace_collector.get_recent_traces(10)
                current_count = len(traces)
                
                # Check for new traces
                if current_count > last_trace_count:
                    # Send new traces
                    trace_summaries = []
                    for correlation_id, spans in list(traces.items())[:current_count - last_trace_count]:
                        summary = trace_collector.get_trace_summary(correlation_id)
                        if summary:
                            trace_summaries.append(summary)
                    
                    if trace_summaries:
                        event_data = {
                            "type": "new_traces",
                            "traces": trace_summaries,
                            "timestamp": asyncio.get_event_loop().time()
                        }
                        yield f"data: {json.dumps(event_data)}\n\n"
                    
                    last_trace_count = current_count
                
                # Wait before next check
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in live trace streaming: {e}")
                error_event = {
                    "type": "error",
                    "message": str(e),
                    "timestamp": asyncio.get_event_loop().time()
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await asyncio.sleep(5.0)  # Wait longer on error
    
    return StreamingResponse(
        generate_live_traces(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
        }
    )


@app.get("/security/ui")
async def get_security_dashboard_ui():
    """Serve the security dashboard UI"""
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
    dashboard_file = os.path.join(static_path, "security-dashboard.html")
    
    if os.path.exists(dashboard_file):
        return FileResponse(
            dashboard_file, 
            media_type="text/html",
            headers={"Cache-Control": "no-cache"}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security dashboard UI not found"
        )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
