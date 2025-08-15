import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
import httpx
from .schemas import (
    AgentManifest, AgentRegistration, AgentStatus, 
    CapabilityInfo, HealthCheckResponse
)

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Core registry for managing agent registrations and health monitoring"""
    
    def __init__(self):
        self.agents: Dict[str, AgentStatus] = {}
        self.capabilities: Dict[str, List[CapabilityInfo]] = {}
        self.health_check_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
    
    async def register_agent(self, registration: AgentRegistration) -> AgentStatus:
        """Register a new agent with the registry"""
        async with self._lock:
            agent_id = registration.manifest.agent_id
            
            # Check for duplicate registration
            if agent_id in self.agents:
                raise ValueError(f"Agent {agent_id} is already registered")
            
            # Validate egress domains against allowlist
            await self._validate_egress_domains(registration.manifest.egress_domains)
            
            # Create agent status
            now = datetime.now(timezone.utc).isoformat()
            agent_status = AgentStatus(
                agent_id=agent_id,
                manifest=registration.manifest,
                health_endpoint=registration.health_endpoint,
                last_seen=now,
                is_healthy=False
            )
            
            # Store agent
            self.agents[agent_id] = agent_status
            
            # Index capabilities
            await self._index_capabilities(agent_status)
            
            # Start health monitoring
            await self._start_health_monitoring(agent_status)
            
            logger.info(f"Registered agent {agent_id} with {len(registration.manifest.capabilities)} capabilities")
            return agent_status
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent from the registry"""
        async with self._lock:
            if agent_id not in self.agents:
                return False
            
            # Stop health monitoring
            await self._stop_health_monitoring(agent_id)
            
            # Remove from capabilities index
            await self._remove_capabilities(agent_id)
            
            # Remove agent
            del self.agents[agent_id]
            
            logger.info(f"Unregistered agent {agent_id}")
            return True
    
    async def get_agent(self, agent_id: str) -> Optional[AgentStatus]:
        """Get agent status by ID"""
        return self.agents.get(agent_id)
    
    async def list_agents(self) -> List[AgentStatus]:
        """List all registered agents"""
        return list(self.agents.values())
    
    async def get_capabilities(self) -> Dict[str, List[CapabilityInfo]]:
        """Get all available capabilities indexed by verb"""
        return self.capabilities.copy()
    
    async def get_capability(self, verb: str) -> List[CapabilityInfo]:
        """Get all agents that provide a specific capability"""
        return self.capabilities.get(verb, [])
    
    async def find_agents_for_capability(self, verb: str, data_scope: Optional[str] = None) -> List[CapabilityInfo]:
        """Find agents that can handle a specific capability and optionally data scope"""
        capabilities = await self.get_capability(verb)
        
        if not data_scope:
            return capabilities
        
        # Filter by data scope
        matching_capabilities = []
        for cap in capabilities:
            agent = self.agents.get(cap.agent_id)
            if agent and data_scope in agent.manifest.data_scopes:
                matching_capabilities.append(cap)
        
        return matching_capabilities
    
    async def _validate_egress_domains(self, egress_domains: List[str]) -> None:
        """Validate egress domains against allowlist policy"""
        # TODO: Implement allowlist validation per ADR-0012
        # For now, only allow local domains
        allowed_domains = {
            "localhost", "127.0.0.1", "::1",
            "kenny.local", "*.kenny.local"  # Local development domains
        }
        
        for domain in egress_domains:
            if not any(self._domain_matches(domain, allowed) for allowed in allowed_domains):
                raise ValueError(f"Egress domain {domain} not in allowlist")
    
    def _domain_matches(self, domain: str, pattern: str) -> bool:
        """Check if domain matches pattern (supports wildcards)"""
        if pattern.startswith("*."):
            return domain.endswith(pattern[1:])
        return domain == pattern
    
    async def _index_capabilities(self, agent_status: AgentStatus) -> None:
        """Index agent capabilities for discovery"""
        for capability in agent_status.manifest.capabilities:
            cap_info = CapabilityInfo(
                verb=capability.verb,
                agent_id=agent_status.agent_id,
                agent_name=agent_status.manifest.display_name or agent_status.agent_id,
                description=capability.description,
                safety_annotations=capability.safety_annotations,
                sla=capability.sla
            )
            
            if capability.verb not in self.capabilities:
                self.capabilities[capability.verb] = []
            
            self.capabilities[capability.verb].append(cap_info)
    
    async def _remove_capabilities(self, agent_id: str) -> None:
        """Remove agent capabilities from index"""
        for verb in list(self.capabilities.keys()):
            self.capabilities[verb] = [
                cap for cap in self.capabilities[verb] 
                if cap.agent_id != agent_id
            ]
            
            # Remove empty capability lists
            if not self.capabilities[verb]:
                del self.capabilities[verb]
    
    async def _start_health_monitoring(self, agent_status: AgentStatus) -> None:
        """Start health monitoring for an agent"""
        if agent_status.agent_id in self.health_check_tasks:
            await self._stop_health_monitoring(agent_status.agent_id)
        
        # Start health check task
        task = asyncio.create_task(
            self._health_monitor_loop(agent_status.agent_id)
        )
        self.health_check_tasks[agent_status.agent_id] = task
    
    async def _stop_health_monitoring(self, agent_id: str) -> None:
        """Stop health monitoring for an agent"""
        if agent_id in self.health_check_tasks:
            task = self.health_check_tasks[agent_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.health_check_tasks[agent_id]
    
    async def _health_monitor_loop(self, agent_id: str) -> None:
        """Health monitoring loop for an agent"""
        while True:
            try:
                await self._perform_health_check(agent_id)
                
                # Get next check interval
                agent = self.agents.get(agent_id)
                if not agent:
                    break
                
                interval = agent.manifest.health_check.interval_seconds if agent.manifest.health_check else 60
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring error for {agent_id}: {e}")
                await asyncio.sleep(30)  # Retry after 30 seconds
    
    async def _perform_health_check(self, agent_id: str) -> None:
        """Perform a single health check for an agent"""
        agent = self.agents.get(agent_id)
        if not agent:
            return
        
        try:
            # Determine health check endpoint
            health_endpoint = agent.manifest.health_check.endpoint if agent.manifest.health_check else "/health"
            health_url = f"{agent.health_endpoint.rstrip('/')}/{health_endpoint.lstrip('/')}"
            
            # Perform health check
            timeout = agent.manifest.health_check.timeout_seconds if agent.manifest.health_check else 10
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(health_url)
                
                if response.status_code == 200:
                    # Parse health response
                    try:
                        health_data = response.json()
                        health_response = HealthCheckResponse(**health_data)
                        
                        # Update agent status
                        now = datetime.now(timezone.utc).isoformat()
                        agent.is_healthy = health_response.status.lower() == "healthy"
                        agent.last_health_check = now
                        agent.error_count = 0
                        agent.last_error = None
                        
                        logger.debug(f"Health check for {agent_id}: {health_response.status}")
                        
                    except Exception as e:
                        logger.warning(f"Invalid health response from {agent_id}: {e}")
                        agent.is_healthy = False
                        agent.last_error = str(e)
                else:
                    agent.is_healthy = False
                    agent.last_error = f"HTTP {response.status_code}"
                    agent.error_count += 1
                    
        except Exception as e:
            now = datetime.now(timezone.utc).isoformat()
            agent.is_healthy = False
            agent.last_error = str(e)
            agent.error_count += 1
            logger.warning(f"Health check failed for {agent_id}: {e}")
        
        # Update last seen timestamp
        agent.last_seen = datetime.now(timezone.utc).isoformat()
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        total_agents = len(self.agents)
        healthy_agents = sum(1 for agent in self.agents.values() if agent.is_healthy)
        
        return {
            "status": "healthy" if healthy_agents == total_agents else "degraded",
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "unhealthy_agents": total_agents - healthy_agents,
            "total_capabilities": len(self.capabilities),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def get_enhanced_health_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive health dashboard with performance metrics from all agents."""
        # Collect enhanced health data from all agents
        agent_health_data = {}
        performance_summary = {
            "total_response_time_ms": 0,
            "total_success_rate": 0,
            "total_error_count": 0,
            "agent_count": 0,
            "sla_violations": 0,
            "degrading_agents": 0
        }
        
        for agent_id, agent_status in self.agents.items():
            try:
                # Fetch enhanced health data from agent's performance endpoint
                enhanced_health = await self._fetch_agent_performance_metrics(agent_status)
                agent_health_data[agent_id] = enhanced_health
                
                # Aggregate performance metrics
                if enhanced_health and "performance_summary" in enhanced_health:
                    perf = enhanced_health["performance_summary"]["current_metrics"]
                    sla = enhanced_health["performance_summary"]["sla_compliance"]
                    
                    performance_summary["total_response_time_ms"] += perf.get("response_time_ms", 0)
                    performance_summary["total_success_rate"] += perf.get("success_rate_percent", 100)
                    performance_summary["total_error_count"] += perf.get("error_count", 0)
                    performance_summary["agent_count"] += 1
                    
                    if not sla.get("overall_compliant", True):
                        performance_summary["sla_violations"] += 1
                    
                    if enhanced_health["performance_summary"]["trend_analysis"].get("trend") == "degrading":
                        performance_summary["degrading_agents"] += 1
                        
            except Exception as e:
                logger.warning(f"Failed to fetch enhanced health for {agent_id}: {e}")
                agent_health_data[agent_id] = {"error": str(e)}
        
        # Calculate system-wide averages
        if performance_summary["agent_count"] > 0:
            avg_response_time = performance_summary["total_response_time_ms"] / performance_summary["agent_count"]
            avg_success_rate = performance_summary["total_success_rate"] / performance_summary["agent_count"]
        else:
            avg_response_time = 0
            avg_success_rate = 100
        
        # Determine overall system health status
        basic_health = await self.get_system_health()
        
        if performance_summary["sla_violations"] > 0:
            system_status = "degraded"
            system_message = f"SLA violations in {performance_summary['sla_violations']} agents"
        elif performance_summary["degrading_agents"] > 0:
            system_status = "degraded"
            system_message = f"{performance_summary['degrading_agents']} agents showing performance degradation"
        else:
            system_status = basic_health["status"]
            system_message = "All agents operating within performance parameters"
        
        return {
            "system_overview": {
                "status": system_status,
                "message": system_message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **basic_health
            },
            "performance_overview": {
                "average_response_time_ms": avg_response_time,
                "average_success_rate_percent": avg_success_rate,
                "total_error_count": performance_summary["total_error_count"],
                "sla_violations": performance_summary["sla_violations"],
                "degrading_agents": performance_summary["degrading_agents"],
                "monitored_agents": performance_summary["agent_count"]
            },
            "agent_details": agent_health_data,
            "system_recommendations": self._generate_system_recommendations(performance_summary, agent_health_data)
        }
    
    async def _fetch_agent_performance_metrics(self, agent_status: AgentStatus) -> Optional[Dict[str, Any]]:
        """Fetch enhanced performance metrics from an agent."""
        if not agent_status.health_endpoint:
            return None
        
        try:
            # Try to fetch from enhanced performance endpoint first
            perf_endpoint = agent_status.health_endpoint.replace("/health", "/health/performance")
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(perf_endpoint)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    # Fallback to basic health endpoint
                    response = await client.get(agent_status.health_endpoint)
                    if response.status_code == 200:
                        return {"basic_health": response.json()}
                
        except Exception as e:
            logger.debug(f"Failed to fetch performance metrics for {agent_status.agent_id}: {e}")
        
        return None
    
    def _generate_system_recommendations(self, performance_summary: Dict[str, Any], agent_health_data: Dict[str, Any]) -> List[str]:
        """Generate system-wide recommendations based on aggregated health data."""
        recommendations = []
        
        # SLA violation recommendations
        if performance_summary["sla_violations"] > 0:
            recommendations.append(
                f"{performance_summary['sla_violations']} agents have SLA violations. "
                "Review individual agent performance and consider scaling or optimization."
            )
        
        # Performance degradation recommendations
        if performance_summary["degrading_agents"] > 0:
            recommendations.append(
                f"{performance_summary['degrading_agents']} agents showing performance degradation. "
                "Monitor resource usage and consider proactive intervention."
            )
        
        # High error rate recommendations
        if performance_summary["total_error_count"] > 50:
            recommendations.append(
                f"High system error count ({performance_summary['total_error_count']}). "
                "Review error patterns across agents and implement error prevention measures."
            )
        
        # Agent availability recommendations
        total_agents = len(self.agents)
        healthy_agents = sum(1 for agent in self.agents.values() if agent.is_healthy)
        if healthy_agents < total_agents:
            unhealthy_count = total_agents - healthy_agents
            recommendations.append(
                f"{unhealthy_count} agents are unhealthy. "
                "Check agent connectivity and resolve health issues."
            )
        
        return recommendations
