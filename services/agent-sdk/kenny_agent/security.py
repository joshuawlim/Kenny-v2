"""
Security monitoring and controls for Kenny v2.

This module provides comprehensive security monitoring capabilities including
network egress monitoring, data access auditing, security incident tracking,
and policy compliance validation.
"""

import asyncio
import logging
import ipaddress
import re
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class SecurityEventType(str, Enum):
    """Types of security events."""
    EGRESS_VIOLATION = "egress_violation"
    DATA_ACCESS_VIOLATION = "data_access_violation"
    POLICY_VIOLATION = "policy_violation"
    AUTHENTICATION_FAILURE = "authentication_failure"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    CONFIGURATION_CHANGE = "configuration_change"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class SecuritySeverity(str, Enum):
    """Security event severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SecurityEvent:
    """Represents a security event."""
    event_id: str
    event_type: SecurityEventType
    severity: SecuritySeverity
    title: str
    description: str
    source_service: str
    source_ip: Optional[str] = None
    target_resource: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    remediation_status: str = "pending"  # pending, investigating, resolved
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["event_type"] = self.event_type.value
        data["severity"] = self.severity.value
        return data


class EgressRule:
    """Network egress rule definition."""
    
    def __init__(self, rule_id: str, name: str, allowed_domains: List[str], 
                 allowed_ips: List[str] = None, ports: List[int] = None):
        """Initialize egress rule."""
        self.rule_id = rule_id
        self.name = name
        self.allowed_domains = allowed_domains
        self.allowed_ips = allowed_ips or []
        self.ports = ports or []
        self.enabled = True
    
    def is_allowed(self, destination: str, port: Optional[int] = None) -> bool:
        """Check if destination is allowed by this rule."""
        if not self.enabled:
            return False
        
        # Check domain patterns
        for domain in self.allowed_domains:
            if self._matches_domain(destination, domain):
                return self._check_port(port)
        
        # Check IP addresses
        for allowed_ip in self.allowed_ips:
            if self._matches_ip(destination, allowed_ip):
                return self._check_port(port)
        
        return False
    
    def _matches_domain(self, destination: str, pattern: str) -> bool:
        """Check if destination matches domain pattern."""
        if pattern.startswith("*."):
            # Wildcard subdomain matching
            domain_suffix = pattern[2:]
            return destination.endswith(domain_suffix) or destination == domain_suffix[1:]
        else:
            return destination == pattern
    
    def _matches_ip(self, destination: str, allowed_ip: str) -> bool:
        """Check if destination matches IP pattern."""
        try:
            if "/" in allowed_ip:
                # CIDR notation
                network = ipaddress.ip_network(allowed_ip, strict=False)
                dest_ip = ipaddress.ip_address(destination)
                return dest_ip in network
            else:
                # Exact IP match
                return destination == allowed_ip
        except (ipaddress.AddressValueError, ValueError):
            return False
    
    def _check_port(self, port: Optional[int]) -> bool:
        """Check if port is allowed."""
        if not self.ports:  # No port restrictions
            return True
        return port in self.ports if port else True


class EgressMonitor:
    """Monitors network egress traffic for policy violations with real-time enforcement."""
    
    def __init__(self):
        """Initialize egress monitor."""
        self.rules: Dict[str, EgressRule] = {}
        self.violation_handlers: List[Callable[[SecurityEvent], None]] = []
        self.blocked_services: Dict[str, Dict[str, Any]] = {}  # service_id -> block_info
        self.blocked_destinations: Dict[str, Dict[str, Any]] = {}  # destination -> block_info
        self.enforcement_enabled = True
        self.bypass_requests: Dict[str, Dict[str, Any]] = {}  # bypass_id -> request_info
        self.load_default_rules()
    
    def add_rule(self, rule: EgressRule):
        """Add an egress rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added egress rule: {rule.name} ({rule.rule_id})")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an egress rule."""
        if rule_id in self.rules:
            rule = self.rules[rule_id]
            del self.rules[rule_id]
            logger.info(f"Removed egress rule: {rule.name} ({rule_id})")
            return True
        return False
    
    def check_egress(self, source_service: str, destination: str, port: Optional[int] = None,
                    correlation_id: Optional[str] = None) -> bool:
        """Check if egress connection is allowed with real-time enforcement."""
        
        # Check if service is blocked
        if self.enforcement_enabled and source_service in self.blocked_services:
            block_info = self.blocked_services[source_service]
            if self._is_block_active(block_info):
                logger.warning(f"Egress blocked: Service {source_service} is currently blocked")
                self._log_blocked_attempt(source_service, destination, port, "service_blocked", correlation_id)
                return False
        
        # Check if destination is blocked
        destination_key = f"{destination}:{port or 'any'}"
        if self.enforcement_enabled and destination_key in self.blocked_destinations:
            block_info = self.blocked_destinations[destination_key]
            if self._is_block_active(block_info):
                logger.warning(f"Egress blocked: Destination {destination_key} is currently blocked")
                self._log_blocked_attempt(source_service, destination, port, "destination_blocked", correlation_id)
                return False
        
        # Check against egress rules
        for rule in self.rules.values():
            if rule.is_allowed(destination, port):
                logger.debug(f"Egress allowed: {source_service} -> {destination}:{port or 'any'}")
                return True
        
        # Egress violation detected - apply enforcement if enabled
        if self.enforcement_enabled:
            self._enforce_egress_violation(source_service, destination, port, correlation_id)
        
        self._handle_egress_violation(source_service, destination, port, correlation_id)
        return False
    
    def _handle_egress_violation(self, source_service: str, destination: str, 
                               port: Optional[int], correlation_id: Optional[str]):
        """Handle egress policy violation."""
        import uuid
        
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=SecurityEventType.EGRESS_VIOLATION,
            severity=SecuritySeverity.HIGH,
            title="Unauthorized Network Egress Detected",
            description=f"Service {source_service} attempted connection to unauthorized destination {destination}:{port or 'unknown'}",
            source_service=source_service,
            target_resource=f"{destination}:{port or 'unknown'}",
            correlation_id=correlation_id,
            metadata={
                "destination": destination,
                "port": port,
                "violation_type": "egress_policy"
            }
        )
        
        # Notify handlers
        for handler in self.violation_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in egress violation handler: {e}")
        
        logger.warning(f"SECURITY VIOLATION: Unauthorized egress from {source_service} to {destination}:{port or 'any'}")
    
    def add_violation_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add handler for egress violations."""
        self.violation_handlers.append(handler)
    
    def load_default_rules(self):
        """Load default egress rules."""
        # Local-first Kenny v2 allowlist
        kenny_rule = EgressRule(
            rule_id="kenny_local",
            name="Kenny v2 Local Services",
            allowed_domains=[
                "localhost",
                "127.0.0.1", 
                "kenny.local",
                "*.kenny.local"
            ],
            allowed_ips=[
                "127.0.0.1",
                "::1",
                "10.0.0.0/8",
                "172.16.0.0/12",
                "192.168.0.0/16"
            ],
            ports=[5100, 8000, 8001, 8002, 8003, 8004, 8005, 8006, 8007]  # Kenny service ports
        )
        self.add_rule(kenny_rule)
        
        # Essential system services (very restricted)
        system_rule = EgressRule(
            rule_id="system_essential",
            name="Essential System Services",
            allowed_domains=[
                "time.apple.com",  # Time sync
                "ntp.pool.org"     # Network time
            ],
            ports=[123]  # NTP only
        )
        self.add_rule(system_rule)
    
    def _enforce_egress_violation(self, source_service: str, destination: str, 
                                port: Optional[int], correlation_id: Optional[str]):
        """Apply real-time enforcement for egress violations."""
        import uuid
        
        destination_key = f"{destination}:{port or 'any'}"
        
        # Block the destination temporarily (5 minutes by default)
        block_duration_minutes = 5
        block_info = {
            "blocked_at": datetime.now(timezone.utc),
            "duration_minutes": block_duration_minutes,
            "triggered_by": f"{source_service}:{correlation_id or 'unknown'}",
            "violation_count": 1,
            "block_id": str(uuid.uuid4())
        }
        
        # Check if destination already blocked and increment violation count
        if destination_key in self.blocked_destinations:
            existing_block = self.blocked_destinations[destination_key]
            if self._is_block_active(existing_block):
                existing_block["violation_count"] += 1
                # Extend block duration for repeated violations
                existing_block["duration_minutes"] = min(existing_block["duration_minutes"] * 2, 60)
                logger.critical(f"EXTENDED BLOCK: {destination_key} - violation count: {existing_block['violation_count']}")
            else:
                self.blocked_destinations[destination_key] = block_info
        else:
            self.blocked_destinations[destination_key] = block_info
        
        logger.critical(f"REAL-TIME ENFORCEMENT: Blocked destination {destination_key} for {block_info['duration_minutes']} minutes")
    
    def block_service(self, service_id: str, duration_minutes: int = 60, reason: str = "Security violation",
                     triggered_by: Optional[str] = None) -> str:
        """Block a service from making any egress connections."""
        import uuid
        
        block_info = {
            "blocked_at": datetime.now(timezone.utc),
            "duration_minutes": duration_minutes,
            "reason": reason,
            "triggered_by": triggered_by or "manual",
            "block_id": str(uuid.uuid4()),
            "type": "service_block"
        }
        
        self.blocked_services[service_id] = block_info
        logger.critical(f"SERVICE BLOCKED: {service_id} for {duration_minutes} minutes - {reason}")
        
        return block_info["block_id"]
    
    def block_destination(self, destination: str, port: Optional[int] = None, 
                         duration_minutes: int = 30, reason: str = "Security violation",
                         triggered_by: Optional[str] = None) -> str:
        """Block access to a specific destination."""
        import uuid
        
        destination_key = f"{destination}:{port or 'any'}"
        block_info = {
            "blocked_at": datetime.now(timezone.utc),
            "duration_minutes": duration_minutes,
            "reason": reason,
            "triggered_by": triggered_by or "manual",
            "block_id": str(uuid.uuid4()),
            "type": "destination_block"
        }
        
        self.blocked_destinations[destination_key] = block_info
        logger.critical(f"DESTINATION BLOCKED: {destination_key} for {duration_minutes} minutes - {reason}")
        
        return block_info["block_id"]
    
    def unblock_service(self, service_id: str) -> bool:
        """Manually unblock a service."""
        if service_id in self.blocked_services:
            block_info = self.blocked_services[service_id]
            del self.blocked_services[service_id]
            logger.info(f"SERVICE UNBLOCKED: {service_id} (block_id: {block_info.get('block_id', 'unknown')})")
            return True
        return False
    
    def unblock_destination(self, destination: str, port: Optional[int] = None) -> bool:
        """Manually unblock a destination."""
        destination_key = f"{destination}:{port or 'any'}"
        if destination_key in self.blocked_destinations:
            block_info = self.blocked_destinations[destination_key]
            del self.blocked_destinations[destination_key]
            logger.info(f"DESTINATION UNBLOCKED: {destination_key} (block_id: {block_info.get('block_id', 'unknown')})")
            return True
        return False
    
    def create_bypass_request(self, service_id: str, destination: str, port: Optional[int] = None,
                            justification: str = "", duration_hours: int = 1) -> str:
        """Create a temporary bypass request for blocked destinations."""
        import uuid
        
        bypass_id = str(uuid.uuid4())
        destination_key = f"{destination}:{port or 'any'}"
        
        bypass_info = {
            "bypass_id": bypass_id,
            "service_id": service_id,
            "destination": destination_key,
            "justification": justification,
            "duration_hours": duration_hours,
            "created_at": datetime.now(timezone.utc),
            "approved": False,
            "approved_by": None,
            "approved_at": None,
            "status": "pending"
        }
        
        self.bypass_requests[bypass_id] = bypass_info
        logger.info(f"BYPASS REQUEST CREATED: {bypass_id} for {service_id} -> {destination_key}")
        
        return bypass_id
    
    def approve_bypass_request(self, bypass_id: str, approved_by: str = "admin") -> bool:
        """Approve a bypass request."""
        if bypass_id in self.bypass_requests:
            bypass_info = self.bypass_requests[bypass_id]
            bypass_info["approved"] = True
            bypass_info["approved_by"] = approved_by
            bypass_info["approved_at"] = datetime.now(timezone.utc)
            bypass_info["status"] = "approved"
            
            logger.info(f"BYPASS REQUEST APPROVED: {bypass_id} by {approved_by}")
            return True
        return False
    
    def _is_block_active(self, block_info: Dict[str, Any]) -> bool:
        """Check if a block is still active based on its duration."""
        blocked_at = datetime.fromisoformat(block_info["blocked_at"].replace("Z", "+00:00")) if isinstance(block_info["blocked_at"], str) else block_info["blocked_at"]
        duration = timedelta(minutes=block_info["duration_minutes"])
        return datetime.now(timezone.utc) < blocked_at + duration
    
    def _log_blocked_attempt(self, source_service: str, destination: str, port: Optional[int],
                           block_reason: str, correlation_id: Optional[str]):
        """Log blocked egress attempts for audit purposes."""
        logger.warning(f"BLOCKED EGRESS ATTEMPT: {source_service} -> {destination}:{port or 'any'} ({block_reason})")
        
        # Create audit event for blocked attempt
        import uuid
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=SecurityEventType.EGRESS_VIOLATION,
            severity=SecuritySeverity.MEDIUM,
            title="Blocked Egress Attempt",
            description=f"Service {source_service} attempted connection to blocked destination {destination}:{port or 'unknown'}",
            source_service=source_service,
            target_resource=f"{destination}:{port or 'unknown'}",
            correlation_id=correlation_id,
            metadata={
                "destination": destination,
                "port": port,
                "block_reason": block_reason,
                "enforcement_action": "blocked"
            }
        )
        
        # Notify violation handlers
        for handler in self.violation_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in blocked attempt handler: {e}")
    
    def get_enforcement_status(self) -> Dict[str, Any]:
        """Get current enforcement status and statistics."""
        # Clean up expired blocks
        self._cleanup_expired_blocks()
        
        active_service_blocks = len([b for b in self.blocked_services.values() if self._is_block_active(b)])
        active_destination_blocks = len([b for b in self.blocked_destinations.values() if self._is_block_active(b)])
        
        return {
            "enforcement_enabled": self.enforcement_enabled,
            "active_service_blocks": active_service_blocks,
            "active_destination_blocks": active_destination_blocks,
            "total_service_blocks": len(self.blocked_services),
            "total_destination_blocks": len(self.blocked_destinations),
            "pending_bypass_requests": len([r for r in self.bypass_requests.values() if r["status"] == "pending"]),
            "approved_bypass_requests": len([r for r in self.bypass_requests.values() if r["status"] == "approved"]),
            "blocked_services": list(self.blocked_services.keys()),
            "blocked_destinations": list(self.blocked_destinations.keys())
        }
    
    def _cleanup_expired_blocks(self):
        """Remove expired blocks from tracking."""
        current_time = datetime.now(timezone.utc)
        
        # Clean up expired service blocks
        expired_services = []
        for service_id, block_info in self.blocked_services.items():
            if not self._is_block_active(block_info):
                expired_services.append(service_id)
        
        for service_id in expired_services:
            del self.blocked_services[service_id]
            logger.info(f"EXPIRED BLOCK REMOVED: Service {service_id}")
        
        # Clean up expired destination blocks
        expired_destinations = []
        for dest_key, block_info in self.blocked_destinations.items():
            if not self._is_block_active(block_info):
                expired_destinations.append(dest_key)
        
        for dest_key in expired_destinations:
            del self.blocked_destinations[dest_key]
            logger.info(f"EXPIRED BLOCK REMOVED: Destination {dest_key}")
        
        # Clean up old bypass requests (older than 7 days)
        cutoff_time = current_time - timedelta(days=7)
        expired_bypasses = []
        for bypass_id, bypass_info in self.bypass_requests.items():
            created_at = datetime.fromisoformat(bypass_info["created_at"].replace("Z", "+00:00")) if isinstance(bypass_info["created_at"], str) else bypass_info["created_at"]
            if created_at < cutoff_time:
                expired_bypasses.append(bypass_id)
        
        for bypass_id in expired_bypasses:
            del self.bypass_requests[bypass_id]


class DataAccessMonitor:
    """Monitors data access patterns for security violations."""
    
    def __init__(self):
        """Initialize data access monitor."""
        self.access_log: List[Dict[str, Any]] = []
        self.sensitive_patterns: List[str] = [
            r"password", r"secret", r"key", r"token", 
            r"credential", r"auth", r"private", r"confidential"
        ]
        self.access_handlers: List[Callable[[SecurityEvent], None]] = []
        self.max_log_entries = 10000
    
    def log_data_access(self, service_name: str, resource: str, operation: str,
                       user_id: Optional[str] = None, data_size: Optional[int] = None,
                       correlation_id: Optional[str] = None):
        """Log data access operation."""
        access_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service_name": service_name,
            "resource": resource,
            "operation": operation,
            "user_id": user_id,
            "data_size": data_size,
            "correlation_id": correlation_id
        }
        
        self.access_log.append(access_entry)
        
        # Check for suspicious patterns
        self._check_suspicious_access(access_entry)
        
        # Trim log if needed
        if len(self.access_log) > self.max_log_entries:
            self.access_log = self.access_log[-self.max_log_entries:]
    
    def _check_suspicious_access(self, access_entry: Dict[str, Any]):
        """Check for suspicious data access patterns."""
        resource = access_entry["resource"].lower()
        
        # Check for sensitive data access
        for pattern in self.sensitive_patterns:
            if re.search(pattern, resource, re.IGNORECASE):
                self._handle_sensitive_access(access_entry, pattern)
                break
        
        # Check for unusual volume
        if access_entry.get("data_size", 0) > 100 * 1024 * 1024:  # 100MB
            self._handle_large_access(access_entry)
    
    def _handle_sensitive_access(self, access_entry: Dict[str, Any], pattern: str):
        """Handle access to sensitive data."""
        import uuid
        
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=SecurityEventType.DATA_ACCESS_VIOLATION,
            severity=SecuritySeverity.MEDIUM,
            title="Sensitive Data Access",
            description=f"Service {access_entry['service_name']} accessed sensitive resource matching pattern '{pattern}'",
            source_service=access_entry["service_name"],
            target_resource=access_entry["resource"],
            user_id=access_entry.get("user_id"),
            correlation_id=access_entry.get("correlation_id"),
            metadata={
                "operation": access_entry["operation"],
                "pattern_matched": pattern,
                "data_size": access_entry.get("data_size")
            }
        )
        
        # Notify handlers
        for handler in self.access_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in data access handler: {e}")
        
        logger.info(f"SENSITIVE ACCESS: {access_entry['service_name']} accessed {access_entry['resource']}")
    
    def _handle_large_access(self, access_entry: Dict[str, Any]):
        """Handle large data access."""
        import uuid
        
        event = SecurityEvent(
            event_id=str(uuid.uuid4()),
            event_type=SecurityEventType.SUSPICIOUS_ACTIVITY,
            severity=SecuritySeverity.LOW,
            title="Large Data Access",
            description=f"Service {access_entry['service_name']} accessed large amount of data ({access_entry['data_size']} bytes)",
            source_service=access_entry["service_name"],
            target_resource=access_entry["resource"],
            user_id=access_entry.get("user_id"),
            correlation_id=access_entry.get("correlation_id"),
            metadata={
                "operation": access_entry["operation"],
                "data_size": access_entry["data_size"],
                "threshold_exceeded": "large_data_access"
            }
        )
        
        # Notify handlers
        for handler in self.access_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in data access handler: {e}")
    
    def add_access_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add handler for data access events."""
        self.access_handlers.append(handler)
    
    def get_access_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get data access history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_access = []
        for entry in self.access_log:
            entry_time = datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00"))
            if entry_time >= cutoff_time:
                recent_access.append(entry)
        
        return recent_access


class SecurityIncident:
    """Represents a security incident with multiple related events."""
    
    def __init__(self, incident_id: str, event_ids: List[str], severity: SecuritySeverity, 
                 title: str, description: str):
        """Initialize security incident."""
        self.incident_id = incident_id
        self.event_ids = event_ids
        self.severity = severity
        self.title = title
        self.description = description
        self.created_at = datetime.now(timezone.utc)
        self.status = "open"  # open, investigating, resolved, false_positive
        self.assigned_to: Optional[str] = None
        self.resolution_notes: Optional[str] = None
        self.resolved_at: Optional[datetime] = None
        self.escalated = False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert incident to dictionary representation."""
        return {
            "incident_id": self.incident_id,
            "event_ids": self.event_ids,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "assigned_to": self.assigned_to,
            "resolution_notes": self.resolution_notes,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "escalated": self.escalated
        }


class SecurityEventCollector:
    """Central collector for security events with incident management."""
    
    def __init__(self):
        """Initialize security event collector."""
        self.events: List[SecurityEvent] = []
        self.incidents: List[SecurityIncident] = []
        self.max_events = 10000
        self.max_incidents = 1000
        self.event_handlers: List[Callable[[SecurityEvent], None]] = []
        self.incident_handlers: List[Callable[[SecurityIncident], None]] = []
        self.correlation_window_minutes = 30  # Group related events within 30 minutes
    
    def collect_event(self, event: SecurityEvent):
        """Collect a security event and potentially create incidents."""
        self.events.append(event)
        
        # Check for incident creation/correlation
        self._check_incident_correlation(event)
        
        # Notify handlers
        for handler in self.event_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in security event handler: {e}")
        
        # Trim events if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        logger.warning(f"SECURITY EVENT [{event.severity.value.upper()}]: {event.title}")
    
    def _check_incident_correlation(self, new_event: SecurityEvent):
        """Check if event should create or correlate with existing incidents."""
        # Check for similar events within correlation window
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=self.correlation_window_minutes)
        
        related_events = []
        for event in self.events:
            if (event.timestamp >= cutoff_time and
                event.event_type == new_event.event_type and
                event.source_service == new_event.source_service and
                event.severity in [SecuritySeverity.CRITICAL, SecuritySeverity.HIGH]):
                related_events.append(event)
        
        # If we have multiple related high-severity events, create incident
        if len(related_events) >= 2:  # Including the new event
            self._create_incident(related_events + [new_event])
    
    def _create_incident(self, events: List[SecurityEvent]):
        """Create a security incident from related events."""
        import uuid
        
        # Check if incident already exists for these events
        event_ids = {e.event_id for e in events}
        for incident in self.incidents:
            if event_ids.intersection(set(incident.event_ids)):
                # Update existing incident with new events
                new_event_ids = event_ids - set(incident.event_ids)
                incident.event_ids.extend(list(new_event_ids))
                logger.warning(f"Updated security incident {incident.incident_id} with {len(new_event_ids)} new events")
                return incident
        
        # Create new incident
        incident_id = str(uuid.uuid4())
        
        # Determine incident severity (highest event severity)
        max_severity = max(events, key=lambda e: [s for s in SecuritySeverity][::-1].index(e.severity)).severity
        
        # Generate incident title and description
        event_type = events[0].event_type.value.replace("_", " ").title()
        service = events[0].source_service
        
        title = f"Multiple {event_type} Events from {service}"
        description = f"Detected {len(events)} related {event_type.lower()} events from {service} within {self.correlation_window_minutes} minutes"
        
        incident = SecurityIncident(
            incident_id=incident_id,
            event_ids=[e.event_id for e in events],
            severity=max_severity,
            title=title,
            description=description
        )
        
        # Auto-escalate critical incidents
        if max_severity == SecuritySeverity.CRITICAL:
            incident.escalated = True
            incident.status = "investigating"
        
        self.incidents.append(incident)
        
        # Trim incidents if needed
        if len(self.incidents) > self.max_incidents:
            self.incidents = self.incidents[-self.max_incidents:]
        
        # Notify incident handlers
        for handler in self.incident_handlers:
            try:
                handler(incident)
            except Exception as e:
                logger.error(f"Error in incident handler: {e}")
        
        logger.critical(f"SECURITY INCIDENT CREATED: {incident.title} ({incident.incident_id})")
        return incident
    
    def add_event_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add handler for security events."""
        self.event_handlers.append(handler)
    
    def add_incident_handler(self, handler: Callable[[SecurityIncident], None]):
        """Add handler for security incidents."""
        self.incident_handlers.append(handler)
    
    def get_incidents(self, status: Optional[str] = None, severity: Optional[SecuritySeverity] = None,
                     hours: int = 24) -> List[SecurityIncident]:
        """Get security incidents with optional filtering."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered_incidents = []
        for incident in self.incidents:
            if incident.created_at >= cutoff_time:
                if status and incident.status != status:
                    continue
                if severity and incident.severity != severity:
                    continue
                filtered_incidents.append(incident)
        
        # Sort by creation time (most recent first)
        filtered_incidents.sort(key=lambda i: i.created_at, reverse=True)
        return filtered_incidents
    
    def get_incident(self, incident_id: str) -> Optional[SecurityIncident]:
        """Get a specific incident by ID."""
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                return incident
        return None
    
    def update_incident_status(self, incident_id: str, status: str, assigned_to: Optional[str] = None,
                              resolution_notes: Optional[str] = None) -> bool:
        """Update incident status and assignment."""
        incident = self.get_incident(incident_id)
        if not incident:
            return False
        
        incident.status = status
        if assigned_to:
            incident.assigned_to = assigned_to
        if resolution_notes:
            incident.resolution_notes = resolution_notes
        
        if status in ["resolved", "false_positive"]:
            incident.resolved_at = datetime.now(timezone.utc)
        
        logger.info(f"Updated incident {incident_id} status to {status}")
        return True
    
    def get_incident_summary(self) -> Dict[str, Any]:
        """Get summary of security incidents."""
        recent_incidents = self.get_incidents(hours=24)
        
        # Count by status
        status_counts = {}
        for incident in recent_incidents:
            status = incident.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for severity in SecuritySeverity:
            severity_counts[severity.value] = len([i for i in recent_incidents if i.severity == severity])
        
        # Calculate metrics
        open_incidents = len([i for i in recent_incidents if i.status == "open"])
        escalated_incidents = len([i for i in recent_incidents if i.escalated])
        
        return {
            "total_incidents_24h": len(recent_incidents),
            "open_incidents": open_incidents,
            "escalated_incidents": escalated_incidents,
            "by_status": status_counts,
            "by_severity": severity_counts,
            "critical_incidents": severity_counts.get("critical", 0),
            "high_incidents": severity_counts.get("high", 0)
        }
    
    def get_events(self, hours: int = 24, severity: Optional[SecuritySeverity] = None,
                  event_type: Optional[SecurityEventType] = None) -> List[SecurityEvent]:
        """Get security events with optional filtering."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered_events = []
        for event in self.events:
            if event.timestamp >= cutoff_time:
                if severity and event.severity != severity:
                    continue
                if event_type and event.event_type != event_type:
                    continue
                filtered_events.append(event)
        
        # Sort by timestamp (most recent first)
        filtered_events.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered_events
    
    def get_event_summary(self) -> Dict[str, Any]:
        """Get summary of security events."""
        recent_events = self.get_events(hours=24)
        
        # Count by severity
        severity_counts = {}
        for severity in SecuritySeverity:
            severity_counts[severity.value] = len([e for e in recent_events if e.severity == severity])
        
        # Count by type
        type_counts = {}
        for event_type in SecurityEventType:
            type_counts[event_type.value] = len([e for e in recent_events if e.event_type == event_type])
        
        return {
            "total_events_24h": len(recent_events),
            "by_severity": severity_counts,
            "by_type": type_counts,
            "critical_count": severity_counts.get("critical", 0),
            "high_count": severity_counts.get("high", 0)
        }


@dataclass
class ResponseAction:
    """Represents an automated response action."""
    action_id: str
    action_type: str  # "isolate", "alert", "block", "quarantine", "notify"
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    cooldown_minutes: int = 60  # Minimum time between same actions


@dataclass
class ResponseRule:
    """Represents an automated incident response rule."""
    rule_id: str
    name: str
    description: str
    triggers: Dict[str, Any]  # Conditions that trigger this rule
    actions: List[ResponseAction]
    enabled: bool = True
    priority: int = 100  # Lower numbers = higher priority


class AutomatedResponseEngine:
    """Handles automated incident response workflows."""
    
    def __init__(self):
        """Initialize automated response engine."""
        self.rules: Dict[str, ResponseRule] = {}
        self.action_history: List[Dict[str, Any]] = []
        self.response_handlers: Dict[str, Callable] = {}
        self.max_history = 1000
        
        # Initialize default response rules
        self._initialize_default_rules()
        
        logger.info("Automated response engine initialized")
    
    def _initialize_default_rules(self):
        """Initialize default automated response rules."""
        
        # Critical egress violation rule
        critical_egress_rule = ResponseRule(
            rule_id="critical_egress_response",
            name="Critical Network Egress Response",
            description="Automated response for critical network egress violations",
            triggers={
                "event_type": SecurityEventType.EGRESS_VIOLATION,
                "severity": SecuritySeverity.CRITICAL,
                "max_events_per_hour": 3
            },
            actions=[
                ResponseAction(
                    action_id="block_egress",
                    action_type="block",
                    description="Block network egress for violating service",
                    parameters={"scope": "service_level"},
                    cooldown_minutes=30
                ),
                ResponseAction(
                    action_id="alert_admins",
                    action_type="alert",
                    description="Send critical alert to administrators",
                    parameters={"urgency": "critical", "channels": ["email", "logging"]},
                    cooldown_minutes=15
                )
            ],
            priority=10
        )
        self.rules[critical_egress_rule.rule_id] = critical_egress_rule
        
        # Data access violation rule
        data_access_rule = ResponseRule(
            rule_id="data_access_response",
            name="Data Access Violation Response",
            description="Automated response for suspicious data access patterns",
            triggers={
                "event_type": SecurityEventType.DATA_ACCESS_VIOLATION,
                "severity": [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL],
                "max_events_per_hour": 5
            },
            actions=[
                ResponseAction(
                    action_id="audit_access",
                    action_type="audit",
                    description="Trigger enhanced audit logging",
                    parameters={"audit_level": "detailed"},
                    cooldown_minutes=60
                ),
                ResponseAction(
                    action_id="notify_security",
                    action_type="notify",
                    description="Notify security team of suspicious access",
                    parameters={"priority": "high"},
                    cooldown_minutes=30
                )
            ],
            priority=20
        )
        self.rules[data_access_rule.rule_id] = data_access_rule
        
        # Incident escalation rule
        incident_escalation_rule = ResponseRule(
            rule_id="incident_escalation_response",
            name="Critical Incident Auto-Escalation",
            description="Automatically escalate critical security incidents",
            triggers={
                "incident_severity": SecuritySeverity.CRITICAL,
                "incident_age_minutes": 15,
                "incident_status": "open"
            },
            actions=[
                ResponseAction(
                    action_id="escalate_incident",
                    action_type="escalate",
                    description="Auto-escalate unassigned critical incidents",
                    parameters={"escalation_level": "security_team"},
                    cooldown_minutes=120
                ),
                ResponseAction(
                    action_id="notify_escalation",
                    action_type="notify",
                    description="Send escalation notifications",
                    parameters={"urgency": "critical", "escalated": True},
                    cooldown_minutes=60
                )
            ],
            priority=5
        )
        self.rules[incident_escalation_rule.rule_id] = incident_escalation_rule
        
        # Service isolation rule for repeated violations
        service_isolation_rule = ResponseRule(
            rule_id="service_isolation_response",
            name="Service Isolation for Repeated Violations",
            description="Isolate services with multiple security violations",
            triggers={
                "event_type": [SecurityEventType.EGRESS_VIOLATION, SecurityEventType.DATA_ACCESS_VIOLATION],
                "severity": [SecuritySeverity.HIGH, SecuritySeverity.CRITICAL],
                "max_events_per_hour": 5,
                "service_repeat_violations": True
            },
            actions=[
                ResponseAction(
                    action_id="isolate_service",
                    action_type="isolate",
                    description="Isolate service from network and data access",
                    parameters={"isolation_level": "full", "duration_minutes": 60},
                    cooldown_minutes=180
                ),
                ResponseAction(
                    action_id="quarantine_data",
                    action_type="quarantine",
                    description="Quarantine data accessed by compromised service",
                    parameters={"quarantine_scope": "service_data", "review_required": True},
                    cooldown_minutes=120
                ),
                ResponseAction(
                    action_id="alert_critical_isolation",
                    action_type="alert",
                    description="Send critical alert for service isolation",
                    parameters={"urgency": "critical", "channels": ["logging", "notification"]},
                    cooldown_minutes=10
                )
            ],
            priority=5
        )
        self.rules[service_isolation_rule.rule_id] = service_isolation_rule
        
        # Data exfiltration prevention rule
        data_exfiltration_rule = ResponseRule(
            rule_id="data_exfiltration_prevention",
            name="Data Exfiltration Prevention",
            description="Automated response for potential data exfiltration attempts",
            triggers={
                "event_type": SecurityEventType.POLICY_VIOLATION,
                "severity": SecuritySeverity.CRITICAL,
                "violation_pattern": "external_data_transfer"
            },
            actions=[
                ResponseAction(
                    action_id="block_data_transfer",
                    action_type="block",
                    description="Block all data transfer operations for service",
                    parameters={"scope": "data_operations", "block_type": "immediate"},
                    cooldown_minutes=5
                ),
                ResponseAction(
                    action_id="freeze_service",
                    action_type="freeze",
                    description="Freeze service operations pending investigation",
                    parameters={"freeze_level": "all_operations", "require_manual_unfreeze": True},
                    cooldown_minutes=30
                ),
                ResponseAction(
                    action_id="emergency_audit",
                    action_type="audit",
                    description="Trigger emergency audit of all service activities",
                    parameters={"audit_level": "emergency", "scope": "full_history"},
                    cooldown_minutes=60
                )
            ],
            priority=1
        )
        self.rules[data_exfiltration_rule.rule_id] = data_exfiltration_rule
        
        # Suspicious activity containment rule
        suspicious_activity_rule = ResponseRule(
            rule_id="suspicious_activity_containment",
            name="Suspicious Activity Containment",
            description="Contain services showing suspicious behavioral patterns",
            triggers={
                "event_type": SecurityEventType.SUSPICIOUS_ACTIVITY,
                "severity": [SecuritySeverity.MEDIUM, SecuritySeverity.HIGH, SecuritySeverity.CRITICAL],
                "pattern_score": 0.7  # Behavioral analysis threshold
            },
            actions=[
                ResponseAction(
                    action_id="rate_limit_service",
                    action_type="rate_limit",
                    description="Apply rate limiting to suspicious service",
                    parameters={"limit_type": "requests_per_minute", "limit_value": 10},
                    cooldown_minutes=45
                ),
                ResponseAction(
                    action_id="enhance_monitoring",
                    action_type="monitor",
                    description="Enable enhanced monitoring for suspicious service",
                    parameters={"monitoring_level": "detailed", "duration_hours": 24},
                    cooldown_minutes=60
                ),
                ResponseAction(
                    action_id="review_access",
                    action_type="review",
                    description="Schedule access review for suspicious service",
                    parameters={"review_type": "access_permissions", "priority": "high"},
                    cooldown_minutes=120
                )
            ],
            priority=15
        )
        self.rules[suspicious_activity_rule.rule_id] = suspicious_activity_rule
        
        logger.info(f"Initialized {len(self.rules)} default response rules with enhanced containment workflows")
    
    def add_response_handler(self, action_type: str, handler: Callable):
        """Add handler for specific response action types."""
        self.response_handlers[action_type] = handler
        logger.info(f"Added response handler for action type: {action_type}")
    
    def evaluate_event_response(self, event: SecurityEvent) -> List[Dict[str, Any]]:
        """Evaluate if an event should trigger automated responses."""
        triggered_actions = []
        
        for rule in sorted(self.rules.values(), key=lambda r: r.priority):
            if not rule.enabled:
                continue
            
            if self._event_matches_rule(event, rule):
                # Check if actions should be triggered based on recent history
                if self._should_trigger_actions(rule, event):
                    actions = self._execute_rule_actions(rule, event)
                    triggered_actions.extend(actions)
        
        return triggered_actions
    
    def evaluate_incident_response(self, incident: SecurityIncident) -> List[Dict[str, Any]]:
        """Evaluate if an incident should trigger automated responses."""
        triggered_actions = []
        
        for rule in sorted(self.rules.values(), key=lambda r: r.priority):
            if not rule.enabled:
                continue
            
            if self._incident_matches_rule(incident, rule):
                if self._should_trigger_incident_actions(rule, incident):
                    actions = self._execute_incident_rule_actions(rule, incident)
                    triggered_actions.extend(actions)
        
        return triggered_actions
    
    def _event_matches_rule(self, event: SecurityEvent, rule: ResponseRule) -> bool:
        """Check if an event matches rule triggers."""
        triggers = rule.triggers
        
        # Check event type
        if "event_type" in triggers:
            if triggers["event_type"] != event.event_type:
                return False
        
        # Check severity
        if "severity" in triggers:
            severity_trigger = triggers["severity"]
            if isinstance(severity_trigger, list):
                if event.severity not in severity_trigger:
                    return False
            else:
                if event.severity != severity_trigger:
                    return False
        
        # Check event frequency (max events per hour)
        if "max_events_per_hour" in triggers:
            recent_events = self._count_recent_events(event.event_type, event.severity, hours=1)
            if recent_events < triggers["max_events_per_hour"]:
                return False
        
        return True
    
    def _incident_matches_rule(self, incident: SecurityIncident, rule: ResponseRule) -> bool:
        """Check if an incident matches rule triggers."""
        triggers = rule.triggers
        
        # Check incident severity
        if "incident_severity" in triggers:
            if incident.severity != triggers["incident_severity"]:
                return False
        
        # Check incident age
        if "incident_age_minutes" in triggers:
            age_minutes = (datetime.now(timezone.utc) - incident.created_at).total_seconds() / 60
            if age_minutes < triggers["incident_age_minutes"]:
                return False
        
        # Check incident status
        if "incident_status" in triggers:
            if incident.status != triggers["incident_status"]:
                return False
        
        return True
    
    def _should_trigger_actions(self, rule: ResponseRule, event: SecurityEvent) -> bool:
        """Check if actions should be triggered based on cooldown periods."""
        for action in rule.actions:
            if not action.enabled:
                continue
            
            # Check cooldown period
            last_action_time = self._get_last_action_time(action.action_id, event.source_service)
            if last_action_time:
                time_since_last = (datetime.now(timezone.utc) - last_action_time).total_seconds() / 60
                if time_since_last < action.cooldown_minutes:
                    return False
        
        return True
    
    def _should_trigger_incident_actions(self, rule: ResponseRule, incident: SecurityIncident) -> bool:
        """Check if incident actions should be triggered based on cooldown periods."""
        for action in rule.actions:
            if not action.enabled:
                continue
            
            # Check cooldown period for incident-based actions
            last_action_time = self._get_last_incident_action_time(action.action_id, incident.incident_id)
            if last_action_time:
                time_since_last = (datetime.now(timezone.utc) - last_action_time).total_seconds() / 60
                if time_since_last < action.cooldown_minutes:
                    return False
        
        return True
    
    def _execute_rule_actions(self, rule: ResponseRule, event: SecurityEvent) -> List[Dict[str, Any]]:
        """Execute actions for a triggered rule."""
        executed_actions = []
        
        for action in rule.actions:
            if not action.enabled:
                continue
            
            try:
                # Record action execution
                action_record = {
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "rule_id": rule.rule_id,
                    "event_id": event.event_id,
                    "source_service": event.source_service,
                    "executed_at": datetime.now(timezone.utc),
                    "parameters": action.parameters,
                    "status": "executed"
                }
                
                # Execute handler if available
                if action.action_type in self.response_handlers:
                    handler = self.response_handlers[action.action_type]
                    result = handler(action, event)
                    action_record["result"] = result
                    action_record["status"] = "completed"
                else:
                    # Log action for external processing
                    logger.warning(f"No handler for action type {action.action_type}, logging for external processing")
                    action_record["status"] = "logged"
                
                self.action_history.append(action_record)
                executed_actions.append(action_record)
                
                logger.info(f"Executed automated response action: {action.action_id} for event {event.event_id}")
                
            except Exception as e:
                logger.error(f"Failed to execute response action {action.action_id}: {e}")
                action_record = {
                    "action_id": action.action_id,
                    "rule_id": rule.rule_id,
                    "event_id": event.event_id,
                    "executed_at": datetime.now(timezone.utc),
                    "status": "failed",
                    "error": str(e)
                }
                self.action_history.append(action_record)
        
        # Trim action history if needed
        if len(self.action_history) > self.max_history:
            self.action_history = self.action_history[-self.max_history:]
        
        return executed_actions
    
    def _execute_incident_rule_actions(self, rule: ResponseRule, incident: SecurityIncident) -> List[Dict[str, Any]]:
        """Execute actions for a triggered incident rule."""
        executed_actions = []
        
        for action in rule.actions:
            if not action.enabled:
                continue
            
            try:
                # Record action execution
                action_record = {
                    "action_id": action.action_id,
                    "action_type": action.action_type,
                    "rule_id": rule.rule_id,
                    "incident_id": incident.incident_id,
                    "executed_at": datetime.now(timezone.utc),
                    "parameters": action.parameters,
                    "status": "executed"
                }
                
                # Execute handler if available
                if action.action_type in self.response_handlers:
                    handler = self.response_handlers[action.action_type]
                    result = handler(action, incident)
                    action_record["result"] = result
                    action_record["status"] = "completed"
                else:
                    # Log action for external processing
                    logger.warning(f"No handler for action type {action.action_type}, logging for external processing")
                    action_record["status"] = "logged"
                
                self.action_history.append(action_record)
                executed_actions.append(action_record)
                
                logger.info(f"Executed automated response action: {action.action_id} for incident {incident.incident_id}")
                
            except Exception as e:
                logger.error(f"Failed to execute response action {action.action_id}: {e}")
                action_record = {
                    "action_id": action.action_id,
                    "rule_id": rule.rule_id,
                    "incident_id": incident.incident_id,
                    "executed_at": datetime.now(timezone.utc),
                    "status": "failed",
                    "error": str(e)
                }
                self.action_history.append(action_record)
        
        return executed_actions
    
    def _count_recent_events(self, event_type: SecurityEventType, severity: SecuritySeverity, hours: int = 1) -> int:
        """Count recent events of specified type and severity."""
        # This would typically query the event collector
        # For now, return a placeholder count
        return 1
    
    def _get_last_action_time(self, action_id: str, source_service: str) -> Optional[datetime]:
        """Get the last time a specific action was executed for a service."""
        for record in reversed(self.action_history):
            if (record.get("action_id") == action_id and 
                record.get("source_service") == source_service):
                return record.get("executed_at")
        return None
    
    def _get_last_incident_action_time(self, action_id: str, incident_id: str) -> Optional[datetime]:
        """Get the last time a specific action was executed for an incident."""
        for record in reversed(self.action_history):
            if (record.get("action_id") == action_id and 
                record.get("incident_id") == incident_id):
                return record.get("executed_at")
        return None
    
    def add_response_rule(self, rule: ResponseRule):
        """Add a new automated response rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added response rule: {rule.name}")
    
    def remove_response_rule(self, rule_id: str) -> bool:
        """Remove an automated response rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed response rule: {rule_id}")
            return True
        return False
    
    def get_response_rules(self) -> List[ResponseRule]:
        """Get all response rules."""
        return list(self.rules.values())
    
    def get_action_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent action execution history."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        filtered_history = []
        for record in self.action_history:
            if record.get("executed_at", datetime.min.replace(tzinfo=timezone.utc)) >= cutoff_time:
                filtered_history.append(record)
        
        return sorted(filtered_history, key=lambda r: r.get("executed_at", datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
    
    def get_response_summary(self) -> Dict[str, Any]:
        """Get summary of automated response activities."""
        recent_actions = self.get_action_history(hours=24)
        
        # Count by action type
        action_type_counts = {}
        for record in recent_actions:
            action_type = record.get("action_type", "unknown")
            action_type_counts[action_type] = action_type_counts.get(action_type, 0) + 1
        
        # Count by status
        status_counts = {}
        for record in recent_actions:
            status = record.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_actions_24h": len(recent_actions),
            "by_action_type": action_type_counts,
            "by_status": status_counts,
            "active_rules": len([r for r in self.rules.values() if r.enabled]),
            "total_rules": len(self.rules),
            "successful_actions": status_counts.get("completed", 0),
            "failed_actions": status_counts.get("failed", 0)
        }


class PrivacyComplianceValidator:
    """Validates privacy compliance for Kenny v2 operations."""
    
    def __init__(self):
        """Initialize privacy compliance validator."""
        self.audit_log: List[Dict[str, Any]] = []
        self.compliance_rules = self._load_privacy_rules()
        self.violations: List[Dict[str, Any]] = []
        self.max_audit_entries = 10000
    
    def _load_privacy_rules(self) -> Dict[str, Any]:
        """Load ADR-0019 privacy compliance rules."""
        return {
            "network_egress": {
                "description": "No unauthorized network egress allowed",
                "allowed_domains": [
                    "localhost", "127.0.0.1", "*.kenny.local",
                    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"
                ],
                "violation_severity": "CRITICAL"
            },
            "data_retention": {
                "description": "Data must be retained locally with user control",
                "max_retention_days": 365,
                "user_controlled": True,
                "violation_severity": "HIGH"
            },
            "external_apis": {
                "description": "No external API calls without explicit user consent",
                "allowed_services": ["local_ollama", "local_chromadb"],
                "violation_severity": "CRITICAL"
            },
            "data_minimization": {
                "description": "Only necessary data should be processed",
                "sensitive_patterns": [
                    r"password", r"secret", r"token", r"key",
                    r"ssn", r"credit_card", r"phone", r"email"
                ],
                "violation_severity": "MEDIUM"
            },
            "user_consent": {
                "description": "User consent required for all data operations",
                "consent_required_operations": [
                    "data_export", "data_sharing", "external_processing"
                ],
                "violation_severity": "HIGH"
            }
        }
    
    def validate_operation(self, operation: str, data: Dict[str, Any],
                          correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate operation against privacy compliance rules."""
        import uuid
        
        validation_result = {
            "operation": operation,
            "compliant": True,
            "violations": [],
            "warnings": [],
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id
        }
        
        # Check network egress compliance
        if "destination" in data:
            egress_result = self._validate_network_egress(data["destination"])
            if not egress_result["compliant"]:
                validation_result["compliant"] = False
                validation_result["violations"].append(egress_result)
        
        # Check data minimization
        if "data_content" in data:
            data_result = self._validate_data_minimization(data["data_content"])
            if data_result["warnings"]:
                validation_result["warnings"].extend(data_result["warnings"])
        
        # Check external API usage
        if "service_name" in data:
            api_result = self._validate_external_api_usage(data["service_name"])
            if not api_result["compliant"]:
                validation_result["compliant"] = False
                validation_result["violations"].append(api_result)
        
        # Log audit entry
        self._log_audit_entry(validation_result)
        
        return validation_result
    
    def _validate_network_egress(self, destination: str) -> Dict[str, Any]:
        """Validate network egress against allowed domains."""
        import ipaddress
        
        allowed_domains = self.compliance_rules["network_egress"]["allowed_domains"]
        
        # Check if destination is allowed
        for allowed in allowed_domains:
            if allowed.startswith("*.") and destination.endswith(allowed[2:]):
                return {"compliant": True, "rule": "network_egress"}
            elif "/" in allowed:  # CIDR notation
                try:
                    network = ipaddress.ip_network(allowed, strict=False)
                    if ipaddress.ip_address(destination) in network:
                        return {"compliant": True, "rule": "network_egress"}
                except ValueError:
                    continue
            elif destination == allowed:
                return {"compliant": True, "rule": "network_egress"}
        
        return {
            "compliant": False,
            "rule": "network_egress",
            "violation_type": "unauthorized_egress",
            "destination": destination,
            "severity": self.compliance_rules["network_egress"]["violation_severity"]
        }
    
    def _validate_data_minimization(self, content: str) -> Dict[str, Any]:
        """Validate data minimization principles."""
        warnings = []
        sensitive_patterns = self.compliance_rules["data_minimization"]["sensitive_patterns"]
        
        for pattern in sensitive_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append({
                    "rule": "data_minimization",
                    "pattern": pattern,
                    "severity": "MEDIUM",
                    "recommendation": f"Consider anonymizing or removing {pattern} references"
                })
        
        return {"warnings": warnings}
    
    def _validate_external_api_usage(self, service_name: str) -> Dict[str, Any]:
        """Validate external API usage compliance."""
        allowed_services = self.compliance_rules["external_apis"]["allowed_services"]
        
        # Check if it's a local service (Kenny v2 services)
        if any(local in service_name for local in ["kenny", "localhost", "127.0.0.1"]):
            return {"compliant": True, "rule": "external_apis"}
        
        # Check allowed external services
        if service_name in allowed_services:
            return {"compliant": True, "rule": "external_apis"}
        
        return {
            "compliant": False,
            "rule": "external_apis", 
            "violation_type": "unauthorized_external_api",
            "service_name": service_name,
            "severity": self.compliance_rules["external_apis"]["violation_severity"]
        }
    
    def _log_audit_entry(self, validation_result: Dict[str, Any]):
        """Log privacy compliance audit entry."""
        self.audit_log.append(validation_result)
        
        # Record violations
        if not validation_result["compliant"]:
            self.violations.append(validation_result)
        
        # Trim audit log if needed
        if len(self.audit_log) > self.max_audit_entries:
            self.audit_log = self.audit_log[-self.max_audit_entries:]
    
    def get_compliance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate privacy compliance report."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_audits = [
            entry for entry in self.audit_log
            if datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) >= cutoff_time
        ]
        
        recent_violations = [
            entry for entry in recent_audits
            if not entry["compliant"]
        ]
        
        # Calculate compliance metrics
        total_operations = len(recent_audits)
        compliant_operations = total_operations - len(recent_violations)
        compliance_rate = (compliant_operations / total_operations * 100) if total_operations > 0 else 100
        
        # Group violations by type
        violation_types = {}
        for violation in recent_violations:
            for v in violation["violations"]:
                v_type = v.get("violation_type", "unknown")
                violation_types[v_type] = violation_types.get(v_type, 0) + 1
        
        return {
            "compliance_rate_percent": compliance_rate,
            "total_operations": total_operations,
            "compliant_operations": compliant_operations,
            "violations": len(recent_violations),
            "violation_types": violation_types,
            "time_period_hours": hours,
            "adr_0019_compliant": len(recent_violations) == 0,
            "report_timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def get_audit_trail(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get privacy audit trail."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        return [
            entry for entry in self.audit_log
            if datetime.fromisoformat(entry["timestamp"].replace("Z", "+00:00")) >= cutoff_time
        ]


class SecurityMonitor:
    """Main security monitoring engine."""
    
    def __init__(self):
        """Initialize security monitor."""
        self.egress_monitor = EgressMonitor()
        self.data_access_monitor = DataAccessMonitor()
        self.event_collector = SecurityEventCollector()
        self.privacy_validator = PrivacyComplianceValidator()
        self.response_engine = AutomatedResponseEngine()
        self.analytics = SecurityAnalytics(self)
        
        # Connect monitors to event collector
        self.egress_monitor.add_violation_handler(self.event_collector.collect_event)
        self.data_access_monitor.add_access_handler(self.event_collector.collect_event)
        
        # Add default event handler
        self.event_collector.add_event_handler(self._log_security_event)
        self.event_collector.add_incident_handler(self._handle_security_incident)
        
        # Add automated response handlers
        self.event_collector.add_event_handler(self._evaluate_automated_response)
        self.event_collector.add_incident_handler(self._evaluate_incident_response)
        
        # Initialize default response handlers
        self._initialize_response_handlers()
    
    def _log_security_event(self, event: SecurityEvent):
        """Log security event to application logs."""
        log_level = {
            SecuritySeverity.CRITICAL: logging.CRITICAL,
            SecuritySeverity.HIGH: logging.ERROR,
            SecuritySeverity.MEDIUM: logging.WARNING,
            SecuritySeverity.LOW: logging.INFO,
            SecuritySeverity.INFO: logging.INFO
        }.get(event.severity, logging.INFO)
        
        logger.log(log_level, f"SECURITY [{event.event_type.value}] {event.title}: {event.description}")
    
    def _handle_security_incident(self, incident: SecurityIncident):
        """Handle security incident with automated response."""
        logger.critical(f"SECURITY INCIDENT: {incident.title} - {incident.description}")
        
        # Auto-escalate critical incidents
        if incident.severity == SecuritySeverity.CRITICAL and not incident.escalated:
            incident.escalated = True
    
    def _evaluate_automated_response(self, event: SecurityEvent):
        """Evaluate and execute automated responses for security events."""
        try:
            triggered_actions = self.response_engine.evaluate_event_response(event)
            if triggered_actions:
                logger.info(f"Triggered {len(triggered_actions)} automated response actions for event {event.event_id}")
        except Exception as e:
            logger.error(f"Error evaluating automated response for event {event.event_id}: {e}")
    
    def _evaluate_incident_response(self, incident: SecurityIncident):
        """Evaluate and execute automated responses for security incidents."""
        try:
            triggered_actions = self.response_engine.evaluate_incident_response(incident)
            if triggered_actions:
                logger.info(f"Triggered {len(triggered_actions)} automated response actions for incident {incident.incident_id}")
        except Exception as e:
            logger.error(f"Error evaluating automated incident response for incident {incident.incident_id}: {e}")
    
    def _initialize_response_handlers(self):
        """Initialize default response action handlers."""
        
        def handle_alert_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle alert response actions."""
            logger.critical(f"AUTOMATED ALERT: {action.description}")
            urgency = action.parameters.get("urgency", "medium")
            channels = action.parameters.get("channels", ["logging"])
            
            # Create enhanced log entry for critical alerts
            if urgency == "critical":
                if isinstance(context, SecurityEvent):
                    logger.critical(f"CRITICAL SECURITY ALERT - Event: {context.title} | Service: {context.source_service}")
                elif isinstance(context, SecurityIncident):
                    logger.critical(f"CRITICAL SECURITY ALERT - Incident: {context.title} | Severity: {context.severity}")
            
            return {"status": "alert_sent", "urgency": urgency, "channels": channels}
        
        def handle_notify_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle notification response actions."""
            priority = action.parameters.get("priority", "medium")
            escalated = action.parameters.get("escalated", False)
            
            if escalated:
                logger.error(f"SECURITY ESCALATION NOTIFICATION: {action.description}")
            else:
                logger.warning(f"SECURITY NOTIFICATION: {action.description}")
            
            return {"status": "notification_sent", "priority": priority, "escalated": escalated}
        
        def handle_audit_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle audit response actions."""
            audit_level = action.parameters.get("audit_level", "standard")
            logger.info(f"ENHANCED AUDIT TRIGGERED: {action.description} (Level: {audit_level})")
            
            # Record enhanced audit entry
            if isinstance(context, SecurityEvent):
                audit_data = {
                    "event_id": context.event_id,
                    "audit_level": audit_level,
                    "triggered_at": datetime.now(timezone.utc).isoformat(),
                    "source_service": context.source_service
                }
            else:
                audit_data = {
                    "audit_level": audit_level,
                    "triggered_at": datetime.now(timezone.utc).isoformat()
                }
            
            return {"status": "audit_enhanced", "audit_level": audit_level, "data": audit_data}
        
        def handle_escalate_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle escalation response actions."""
            escalation_level = action.parameters.get("escalation_level", "security_team")
            
            if isinstance(context, SecurityIncident):
                # Update incident escalation status
                context.escalated = True
                context.escalation_level = escalation_level
                logger.critical(f"INCIDENT AUTO-ESCALATED: {context.title} to {escalation_level}")
                
                return {
                    "status": "incident_escalated",
                    "escalation_level": escalation_level,
                    "incident_id": context.incident_id
                }
            else:
                logger.error(f"SECURITY AUTO-ESCALATION: {action.description} to {escalation_level}")
                return {"status": "escalated", "escalation_level": escalation_level}
        
        def handle_block_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle blocking response actions."""
            scope = action.parameters.get("scope", "service_level")
            
            if isinstance(context, SecurityEvent):
                logger.critical(f"AUTOMATED SECURITY BLOCK: {context.source_service} - {action.description}")
                
                # For network egress violations, mark service for blocking
                if context.event_type == SecurityEventType.EGRESS_VIOLATION:
                    # This would integrate with actual blocking mechanisms
                    logger.critical(f"NETWORK EGRESS BLOCKED for service: {context.source_service}")
                
                return {
                    "status": "blocked",
                    "scope": scope,
                    "service": context.source_service,
                    "block_type": "network_egress"
                }
            else:
                logger.critical(f"AUTOMATED SECURITY BLOCK: {action.description}")
                return {"status": "blocked", "scope": scope}
        
        def handle_isolate_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle service isolation response actions."""
            isolation_level = action.parameters.get("isolation_level", "network")
            duration_minutes = action.parameters.get("duration_minutes", 60)
            
            if isinstance(context, SecurityEvent):
                service = context.source_service
                logger.critical(f"SERVICE ISOLATION TRIGGERED: {service} - {action.description}")
                logger.critical(f"Isolation Level: {isolation_level}, Duration: {duration_minutes} minutes")
                
                # Record isolation action for tracking
                isolation_data = {
                    "service": service,
                    "isolation_level": isolation_level,
                    "duration_minutes": duration_minutes,
                    "triggered_by": context.event_id,
                    "isolation_start": datetime.now(timezone.utc).isoformat()
                }
                
                return {
                    "status": "service_isolated",
                    "service": service,
                    "isolation_level": isolation_level,
                    "duration_minutes": duration_minutes,
                    "isolation_data": isolation_data
                }
            else:
                logger.critical(f"SERVICE ISOLATION: {action.description}")
                return {"status": "isolation_initiated", "isolation_level": isolation_level}
        
        def handle_quarantine_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle data quarantine response actions."""
            quarantine_scope = action.parameters.get("quarantine_scope", "service_data")
            review_required = action.parameters.get("review_required", True)
            
            if isinstance(context, SecurityEvent):
                service = context.source_service
                logger.critical(f"DATA QUARANTINE TRIGGERED: {service} - {action.description}")
                logger.critical(f"Quarantine Scope: {quarantine_scope}, Review Required: {review_required}")
                
                import uuid
                quarantine_data = {
                    "service": service,
                    "quarantine_scope": quarantine_scope,
                    "review_required": review_required,
                    "triggered_by": context.event_id,
                    "quarantine_start": datetime.now(timezone.utc).isoformat(),
                    "quarantine_id": str(uuid.uuid4())
                }
                
                return {
                    "status": "data_quarantined",
                    "service": service,
                    "quarantine_scope": quarantine_scope,
                    "quarantine_data": quarantine_data
                }
            else:
                logger.critical(f"DATA QUARANTINE: {action.description}")
                return {"status": "quarantine_initiated", "scope": quarantine_scope}
        
        def handle_freeze_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle service freeze response actions."""
            freeze_level = action.parameters.get("freeze_level", "all_operations")
            manual_unfreeze = action.parameters.get("require_manual_unfreeze", False)
            
            if isinstance(context, SecurityEvent):
                service = context.source_service
                logger.critical(f"SERVICE FREEZE TRIGGERED: {service} - {action.description}")
                logger.critical(f"Freeze Level: {freeze_level}, Manual Unfreeze Required: {manual_unfreeze}")
                
                import uuid
                freeze_data = {
                    "service": service,
                    "freeze_level": freeze_level,
                    "manual_unfreeze_required": manual_unfreeze,
                    "triggered_by": context.event_id,
                    "freeze_start": datetime.now(timezone.utc).isoformat(),
                    "freeze_id": str(uuid.uuid4())
                }
                
                return {
                    "status": "service_frozen",
                    "service": service,
                    "freeze_level": freeze_level,
                    "freeze_data": freeze_data
                }
            else:
                logger.critical(f"SERVICE FREEZE: {action.description}")
                return {"status": "freeze_initiated", "freeze_level": freeze_level}
        
        def handle_rate_limit_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle rate limiting response actions."""
            limit_type = action.parameters.get("limit_type", "requests_per_minute")
            limit_value = action.parameters.get("limit_value", 10)
            
            if isinstance(context, SecurityEvent):
                service = context.source_service
                logger.warning(f"RATE LIMITING APPLIED: {service} - {action.description}")
                logger.warning(f"Limit: {limit_value} {limit_type}")
                
                rate_limit_data = {
                    "service": service,
                    "limit_type": limit_type,
                    "limit_value": limit_value,
                    "triggered_by": context.event_id,
                    "rate_limit_start": datetime.now(timezone.utc).isoformat()
                }
                
                return {
                    "status": "rate_limited",
                    "service": service,
                    "limit_type": limit_type,
                    "limit_value": limit_value,
                    "rate_limit_data": rate_limit_data
                }
            else:
                logger.warning(f"RATE LIMITING: {action.description}")
                return {"status": "rate_limit_applied", "limit_type": limit_type}
        
        def handle_monitor_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle enhanced monitoring response actions."""
            monitoring_level = action.parameters.get("monitoring_level", "standard")
            duration_hours = action.parameters.get("duration_hours", 24)
            
            if isinstance(context, SecurityEvent):
                service = context.source_service
                logger.info(f"ENHANCED MONITORING ENABLED: {service} - {action.description}")
                logger.info(f"Monitoring Level: {monitoring_level}, Duration: {duration_hours} hours")
                
                monitoring_data = {
                    "service": service,
                    "monitoring_level": monitoring_level,
                    "duration_hours": duration_hours,
                    "triggered_by": context.event_id,
                    "monitoring_start": datetime.now(timezone.utc).isoformat()
                }
                
                return {
                    "status": "monitoring_enhanced",
                    "service": service,
                    "monitoring_level": monitoring_level,
                    "monitoring_data": monitoring_data
                }
            else:
                logger.info(f"ENHANCED MONITORING: {action.description}")
                return {"status": "monitoring_enabled", "monitoring_level": monitoring_level}
        
        def handle_review_action(action: ResponseAction, context) -> Dict[str, Any]:
            """Handle access review response actions."""
            review_type = action.parameters.get("review_type", "access_permissions")
            priority = action.parameters.get("priority", "medium")
            
            if isinstance(context, SecurityEvent):
                service = context.source_service
                logger.info(f"ACCESS REVIEW SCHEDULED: {service} - {action.description}")
                logger.info(f"Review Type: {review_type}, Priority: {priority}")
                
                import uuid
                review_data = {
                    "service": service,
                    "review_type": review_type,
                    "priority": priority,
                    "triggered_by": context.event_id,
                    "review_scheduled": datetime.now(timezone.utc).isoformat(),
                    "review_id": str(uuid.uuid4())
                }
                
                return {
                    "status": "review_scheduled",
                    "service": service,
                    "review_type": review_type,
                    "review_data": review_data
                }
            else:
                logger.info(f"ACCESS REVIEW: {action.description}")
                return {"status": "review_initiated", "review_type": review_type}
        
        # Register all response handlers
        self.response_engine.add_response_handler("alert", handle_alert_action)
        self.response_engine.add_response_handler("notify", handle_notify_action)
        self.response_engine.add_response_handler("audit", handle_audit_action)
        self.response_engine.add_response_handler("escalate", handle_escalate_action)
        self.response_engine.add_response_handler("block", handle_block_action)
        self.response_engine.add_response_handler("isolate", handle_isolate_action)
        self.response_engine.add_response_handler("quarantine", handle_quarantine_action)
        self.response_engine.add_response_handler("freeze", handle_freeze_action)
        self.response_engine.add_response_handler("rate_limit", handle_rate_limit_action)
        self.response_engine.add_response_handler("monitor", handle_monitor_action)
        self.response_engine.add_response_handler("review", handle_review_action)
        
        logger.info("Initialized automated response handlers with advanced containment capabilities")
    
    def check_network_egress(self, source_service: str, destination: str, port: Optional[int] = None,
                           correlation_id: Optional[str] = None) -> bool:
        """Check if network egress is allowed."""
        return self.egress_monitor.check_egress(source_service, destination, port, correlation_id)
    
    def log_data_access(self, service_name: str, resource: str, operation: str,
                       user_id: Optional[str] = None, data_size: Optional[int] = None,
                       correlation_id: Optional[str] = None):
        """Log data access operation."""
        self.data_access_monitor.log_data_access(
            service_name, resource, operation, user_id, data_size, correlation_id
        )
    
    def validate_privacy_compliance(self, operation: str, data: Dict[str, Any],
                                  correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Validate operation against privacy compliance rules."""
        return self.privacy_validator.validate_operation(operation, data, correlation_id)
    
    def get_privacy_compliance_report(self, hours: int = 24) -> Dict[str, Any]:
        """Get privacy compliance report."""
        return self.privacy_validator.get_compliance_report(hours)
    
    def get_privacy_audit_trail(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get privacy compliance audit trail."""
        return self.privacy_validator.get_audit_trail(hours)
    
    def get_incident_management_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get incident management dashboard."""
        return {
            "incident_summary": self.event_collector.get_incident_summary(),
            "recent_incidents": [i.to_dict() for i in self.event_collector.get_incidents(hours=hours)],
            "open_incidents": [i.to_dict() for i in self.event_collector.get_incidents(status="open", hours=hours)],
            "escalated_incidents": len([i for i in self.event_collector.get_incidents(hours=hours) if i.escalated]),
            "time_period_hours": hours
        }
    
    def get_security_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive security dashboard."""
        return {
            "event_summary": self.event_collector.get_event_summary(),
            "incident_summary": self.event_collector.get_incident_summary(),
            "privacy_compliance": self.privacy_validator.get_compliance_report(hours),
            "automated_response_summary": self.response_engine.get_response_summary(),
            "recent_events": [e.to_dict() for e in self.event_collector.get_events(hours)],
            "recent_incidents": [i.to_dict() for i in self.event_collector.get_incidents(hours=hours)],
            "recent_response_actions": self.response_engine.get_action_history(hours),
            "data_access_log": self.data_access_monitor.get_access_history(hours),
            "egress_rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "enabled": rule.enabled,
                    "allowed_domains": rule.allowed_domains,
                    "allowed_ips": rule.allowed_ips,
                    "ports": rule.ports
                }
                for rule in self.egress_monitor.rules.values()
            ],
            "response_rules": [
                {
                    "rule_id": rule.rule_id,
                    "name": rule.name,
                    "description": rule.description,
                    "enabled": rule.enabled,
                    "priority": rule.priority,
                    "action_count": len(rule.actions)
                }
                for rule in self.response_engine.get_response_rules()
            ],
            "time_period_hours": hours
        }
    
    def get_automated_response_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get automated response dashboard."""
        return {
            "response_summary": self.response_engine.get_response_summary(),
            "action_history": self.response_engine.get_action_history(hours),
            "response_rules": [
                {
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
                            "cooldown_minutes": action.cooldown_minutes
                        }
                        for action in rule.actions
                    ]
                }
                for rule in self.response_engine.get_response_rules()
            ],
            "time_period_hours": hours
        }
    
    def add_response_rule(self, rule: ResponseRule):
        """Add a new automated response rule."""
        self.response_engine.add_response_rule(rule)
    
    def remove_response_rule(self, rule_id: str) -> bool:
        """Remove an automated response rule."""
        return self.response_engine.remove_response_rule(rule_id)
    
    def get_response_action_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get automated response action history."""
        return self.response_engine.get_action_history(hours)
    
    def collect_security_metrics(self) -> Dict[str, Any]:
        """Collect current security metrics snapshot."""
        return self.analytics.collect_security_metrics()
    
    def get_security_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get security trends analysis."""
        return self.analytics.get_security_trends(hours)
    
    def get_security_forecast(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Get security forecast based on trends."""
        return self.analytics.get_security_forecast(hours_ahead)
    
    def get_security_analytics_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive security analytics dashboard."""
        return self.analytics.get_security_metrics_dashboard(hours)


class SecurityAnalytics:
    """Provides security metrics and trend analysis capabilities."""
    
    def __init__(self, security_monitor: SecurityMonitor):
        """Initialize security analytics."""
        self.security_monitor = security_monitor
        self.metrics_history: List[Dict[str, Any]] = []
        self.max_history = 10000  # Store up to 10k metric points
        
        logger.info("Security analytics initialized")
    
    def collect_security_metrics(self) -> Dict[str, Any]:
        """Collect current security metrics snapshot."""
        current_time = datetime.now(timezone.utc)
        
        # Get current event and incident counts
        event_summary = self.security_monitor.event_collector.get_event_summary()
        incident_summary = self.security_monitor.event_collector.get_incident_summary()
        response_summary = self.security_monitor.response_engine.get_response_summary()
        
        # Calculate security health score (0-100)
        security_score = self._calculate_security_score(event_summary, incident_summary, response_summary)
        
        metrics = {
            "timestamp": current_time.isoformat(),
            "security_score": security_score,
            "events": {
                "total_24h": event_summary.get("total_events_24h", 0),
                "critical_count": event_summary.get("critical_count", 0),
                "high_count": event_summary.get("high_count", 0),
                "medium_count": event_summary.get("by_severity", {}).get("medium", 0),
                "low_count": event_summary.get("by_severity", {}).get("low", 0),
                "by_type": event_summary.get("by_type", {})
            },
            "incidents": {
                "total_24h": incident_summary.get("total_incidents_24h", 0),
                "open_incidents": incident_summary.get("open_incidents", 0),
                "escalated_incidents": incident_summary.get("escalated_incidents", 0),
                "critical_incidents": incident_summary.get("critical_incidents", 0),
                "high_incidents": incident_summary.get("high_incidents", 0),
                "by_status": incident_summary.get("by_status", {})
            },
            "automated_response": {
                "total_actions_24h": response_summary.get("total_actions_24h", 0),
                "successful_actions": response_summary.get("successful_actions", 0),
                "failed_actions": response_summary.get("failed_actions", 0),
                "active_rules": response_summary.get("active_rules", 0),
                "by_action_type": response_summary.get("by_action_type", {})
            },
            "compliance": {
                "privacy_score": self._get_privacy_compliance_score(),
                "egress_violations_24h": len([
                    e for e in self.security_monitor.event_collector.get_events(hours=24)
                    if e.event_type == SecurityEventType.EGRESS_VIOLATION
                ]),
                "data_access_violations_24h": len([
                    e for e in self.security_monitor.event_collector.get_events(hours=24)
                    if e.event_type == SecurityEventType.DATA_ACCESS_VIOLATION
                ])
            }
        }
        
        # Store metrics in history
        self.metrics_history.append(metrics)
        
        # Trim history if needed
        if len(self.metrics_history) > self.max_history:
            self.metrics_history = self.metrics_history[-self.max_history:]
        
        return metrics
    
    def _calculate_security_score(self, event_summary: Dict[str, Any], 
                                incident_summary: Dict[str, Any], 
                                response_summary: Dict[str, Any]) -> float:
        """Calculate overall security health score (0-100)."""
        
        # Base score starts at 100
        score = 100.0
        
        # Deduct points for events (more critical = higher deduction)
        critical_events = event_summary.get("critical_count", 0)
        high_events = event_summary.get("high_count", 0)
        medium_events = event_summary.get("by_severity", {}).get("medium", 0)
        
        score -= critical_events * 10  # 10 points per critical event
        score -= high_events * 5       # 5 points per high event
        score -= medium_events * 2     # 2 points per medium event
        
        # Deduct points for incidents
        critical_incidents = incident_summary.get("critical_incidents", 0)
        open_incidents = incident_summary.get("open_incidents", 0)
        
        score -= critical_incidents * 15  # 15 points per critical incident
        score -= open_incidents * 3       # 3 points per open incident
        
        # Deduct points for failed automated responses
        failed_actions = response_summary.get("failed_actions", 0)
        score -= failed_actions * 2  # 2 points per failed response
        
        # Add points for successful automated responses (up to 10 bonus points)
        successful_actions = response_summary.get("successful_actions", 0)
        score += min(successful_actions * 0.5, 10)
        
        # Ensure score is between 0 and 100
        return max(0.0, min(100.0, score))
    
    def _get_privacy_compliance_score(self) -> float:
        """Get privacy compliance score from validator."""
        try:
            compliance_report = self.security_monitor.get_privacy_compliance_report(hours=24)
            return compliance_report.get("compliance_rate_percent", 100.0)
        except Exception as e:
            logger.error(f"Error getting privacy compliance score: {e}")
            return 100.0
    
    def get_security_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Analyze security trends over time."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Filter metrics to time window
        recent_metrics = [
            m for m in self.metrics_history
            if datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")) >= cutoff_time
        ]
        
        if len(recent_metrics) < 2:
            return {
                "trend_analysis": "insufficient_data",
                "data_points": len(recent_metrics),
                "message": "Need at least 2 data points for trend analysis"
            }
        
        # Analyze trends
        first_point = recent_metrics[0]
        last_point = recent_metrics[-1]
        
        trends = {
            "time_period_hours": hours,
            "data_points": len(recent_metrics),
            "security_score": {
                "current": last_point["security_score"],
                "previous": first_point["security_score"],
                "change": last_point["security_score"] - first_point["security_score"],
                "trend": self._determine_trend(first_point["security_score"], last_point["security_score"])
            },
            "events": {
                "critical_trend": self._analyze_metric_trend(recent_metrics, ["events", "critical_count"]),
                "high_trend": self._analyze_metric_trend(recent_metrics, ["events", "high_count"]),
                "total_trend": self._analyze_metric_trend(recent_metrics, ["events", "total_24h"])
            },
            "incidents": {
                "open_trend": self._analyze_metric_trend(recent_metrics, ["incidents", "open_incidents"]),
                "escalated_trend": self._analyze_metric_trend(recent_metrics, ["incidents", "escalated_incidents"]),
                "total_trend": self._analyze_metric_trend(recent_metrics, ["incidents", "total_24h"])
            },
            "compliance": {
                "privacy_trend": self._analyze_metric_trend(recent_metrics, ["compliance", "privacy_score"]),
                "egress_violations_trend": self._analyze_metric_trend(recent_metrics, ["compliance", "egress_violations_24h"])
            },
            "automated_response": {
                "success_rate_trend": self._analyze_success_rate_trend(recent_metrics),
                "total_actions_trend": self._analyze_metric_trend(recent_metrics, ["automated_response", "total_actions_24h"])
            }
        }
        
        # Generate trend summary
        trends["summary"] = self._generate_trend_summary(trends)
        
        return trends
    
    def _analyze_metric_trend(self, metrics: List[Dict[str, Any]], metric_path: List[str]) -> Dict[str, Any]:
        """Analyze trend for a specific metric."""
        values = []
        timestamps = []
        
        for m in metrics:
            value = m
            for key in metric_path:
                value = value.get(key, 0)
            values.append(value)
            timestamps.append(datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00")))
        
        if len(values) < 2:
            return {"trend": "insufficient_data", "values": values}
        
        first_value = values[0]
        last_value = values[-1]
        change = last_value - first_value
        percent_change = (change / first_value * 100) if first_value > 0 else 0
        
        # Calculate simple moving average if we have enough points
        avg_value = sum(values) / len(values)
        
        return {
            "current": last_value,
            "previous": first_value,
            "change": change,
            "percent_change": percent_change,
            "average": avg_value,
            "trend": self._determine_trend(first_value, last_value),
            "volatility": self._calculate_volatility(values)
        }
    
    def _analyze_success_rate_trend(self, metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze automated response success rate trend."""
        success_rates = []
        
        for m in metrics:
            total_actions = m.get("automated_response", {}).get("total_actions_24h", 0)
            successful_actions = m.get("automated_response", {}).get("successful_actions", 0)
            
            if total_actions > 0:
                success_rate = (successful_actions / total_actions) * 100
            else:
                success_rate = 100.0  # No actions = 100% success rate
            
            success_rates.append(success_rate)
        
        if len(success_rates) < 2:
            return {"trend": "insufficient_data", "values": success_rates}
        
        return self._analyze_metric_trend(metrics, ["success_rate"])  # Will be computed differently
    
    def _determine_trend(self, first_value: float, last_value: float, threshold: float = 5.0) -> str:
        """Determine trend direction."""
        change = last_value - first_value
        percent_change = (change / first_value * 100) if first_value > 0 else 0
        
        if abs(percent_change) < threshold:
            return "stable"
        elif percent_change > 0:
            return "increasing"
        else:
            return "decreasing"
    
    def _calculate_volatility(self, values: List[float]) -> float:
        """Calculate volatility (standard deviation) of values."""
        if len(values) < 2:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
    
    def _generate_trend_summary(self, trends: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable trend summary."""
        security_score_trend = trends.get("security_score", {}).get("trend", "unknown")
        security_score_change = trends.get("security_score", {}).get("change", 0)
        
        # Determine overall security posture
        if security_score_trend == "increasing":
            posture = "improving"
            posture_emoji = "📈"
        elif security_score_trend == "decreasing":
            posture = "declining"
            posture_emoji = "📉"
        else:
            posture = "stable"
            posture_emoji = "📊"
        
        # Count concerning trends
        concerning_trends = 0
        if trends.get("events", {}).get("critical_trend", {}).get("trend") == "increasing":
            concerning_trends += 1
        if trends.get("incidents", {}).get("open_trend", {}).get("trend") == "increasing":
            concerning_trends += 1
        if trends.get("compliance", {}).get("privacy_trend", {}).get("trend") == "decreasing":
            concerning_trends += 1
        
        # Generate key insights
        insights = []
        
        # Security score insight
        if abs(security_score_change) > 5:
            insights.append(f"Security score {security_score_trend} by {abs(security_score_change):.1f} points")
        
        # Critical events insight
        critical_trend = trends.get("events", {}).get("critical_trend", {})
        if critical_trend.get("trend") == "increasing":
            change = critical_trend.get("change", 0)
            insights.append(f"Critical events increased by {change}")
        
        # Open incidents insight
        open_trend = trends.get("incidents", {}).get("open_trend", {})
        if open_trend.get("current", 0) > 0:
            current_open = open_trend.get("current", 0)
            insights.append(f"{current_open} incidents currently open")
        
        return {
            "overall_posture": posture,
            "posture_emoji": posture_emoji,
            "security_score_change": security_score_change,
            "concerning_trends": concerning_trends,
            "key_insights": insights,
            "risk_level": self._assess_risk_level(trends),
            "recommendations": self._generate_recommendations(trends)
        }
    
    def _assess_risk_level(self, trends: Dict[str, Any]) -> str:
        """Assess current risk level based on trends."""
        risk_score = 0
        
        # High risk factors
        if trends.get("security_score", {}).get("current", 100) < 50:
            risk_score += 3
        elif trends.get("security_score", {}).get("current", 100) < 70:
            risk_score += 2
        elif trends.get("security_score", {}).get("current", 100) < 85:
            risk_score += 1
        
        # Critical events
        critical_count = trends.get("events", {}).get("critical_trend", {}).get("current", 0)
        if critical_count > 5:
            risk_score += 3
        elif critical_count > 2:
            risk_score += 2
        elif critical_count > 0:
            risk_score += 1
        
        # Open incidents
        open_incidents = trends.get("incidents", {}).get("open_trend", {}).get("current", 0)
        if open_incidents > 3:
            risk_score += 2
        elif open_incidents > 1:
            risk_score += 1
        
        # Determine risk level
        if risk_score >= 6:
            return "critical"
        elif risk_score >= 4:
            return "high"
        elif risk_score >= 2:
            return "medium"
        else:
            return "low"
    
    def _generate_recommendations(self, trends: Dict[str, Any]) -> List[str]:
        """Generate security recommendations based on trends."""
        recommendations = []
        
        # Security score recommendations
        security_score = trends.get("security_score", {}).get("current", 100)
        if security_score < 70:
            recommendations.append("Review and address open security incidents immediately")
        
        # Critical events recommendations
        critical_trend = trends.get("events", {}).get("critical_trend", {})
        if critical_trend.get("trend") == "increasing":
            recommendations.append("Investigate root cause of increasing critical security events")
        
        # Open incidents recommendations
        open_trend = trends.get("incidents", {}).get("open_trend", {})
        if open_trend.get("current", 0) > 2:
            recommendations.append("Prioritize resolution of open security incidents")
        
        # Compliance recommendations
        privacy_trend = trends.get("compliance", {}).get("privacy_trend", {})
        if privacy_trend.get("current", 100) < 95:
            recommendations.append("Review privacy compliance controls and ADR-0019 adherence")
        
        # Response effectiveness recommendations
        response_trend = trends.get("automated_response", {}).get("success_rate_trend", {})
        if response_trend.get("current", 100) < 90:
            recommendations.append("Review and optimize automated response rules and handlers")
        
        # General recommendations
        if not recommendations:
            recommendations.append("Continue monitoring security posture and maintain current controls")
        
        return recommendations
    
    def get_security_forecast(self, hours_ahead: int = 24) -> Dict[str, Any]:
        """Generate basic security forecast based on current trends."""
        current_trends = self.get_security_trends(hours=24)
        
        if current_trends.get("trend_analysis") == "insufficient_data":
            return {
                "forecast_period_hours": hours_ahead,
                "status": "insufficient_data",
                "message": "Need more historical data for forecasting"
            }
        
        # Simple linear projection based on current trends
        security_score_trend = current_trends.get("security_score", {})
        current_score = security_score_trend.get("current", 100)
        change_rate = security_score_trend.get("change", 0) / 24  # Change per hour
        
        projected_score = current_score + (change_rate * hours_ahead)
        projected_score = max(0, min(100, projected_score))  # Clamp to 0-100
        
        # Assess projected risk
        if projected_score < 50:
            risk_projection = "critical"
            risk_emoji = "🔴"
        elif projected_score < 70:
            risk_projection = "high"
            risk_emoji = "🟡"
        elif projected_score < 85:
            risk_projection = "medium"
            risk_emoji = "🟢"
        else:
            risk_projection = "low"
            risk_emoji = "🟢"
        
        return {
            "forecast_period_hours": hours_ahead,
            "current_security_score": current_score,
            "projected_security_score": projected_score,
            "score_change_projection": projected_score - current_score,
            "risk_projection": risk_projection,
            "risk_emoji": risk_emoji,
            "confidence": "low",  # Simple linear projection has low confidence
            "based_on_trends": {
                key: trend.get("trend", "unknown") 
                for key, trend in current_trends.items() 
                if isinstance(trend, dict) and "trend" in trend
            },
            "recommendations": self._generate_forecast_recommendations(projected_score, current_score)
        }
    
    def _generate_forecast_recommendations(self, projected_score: float, current_score: float) -> List[str]:
        """Generate recommendations based on security forecast."""
        recommendations = []
        
        if projected_score < current_score - 10:
            recommendations.append("Security posture declining - immediate attention required")
            recommendations.append("Review current security incidents and response effectiveness")
        elif projected_score > current_score + 5:
            recommendations.append("Security posture improving - maintain current practices")
        else:
            recommendations.append("Security posture stable - continue monitoring")
        
        if projected_score < 70:
            recommendations.append("Consider implementing additional security controls")
            recommendations.append("Review and strengthen incident response procedures")
        
        return recommendations
    
    def get_security_metrics_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive security metrics dashboard."""
        current_metrics = self.collect_security_metrics()
        trends = self.get_security_trends(hours)
        forecast = self.get_security_forecast(hours_ahead=24)
        
        return {
            "current_metrics": current_metrics,
            "trends": trends,
            "forecast": forecast,
            "time_period_hours": hours,
            "dashboard_generated_at": datetime.now(timezone.utc).isoformat(),
            "data_points_available": len(self.metrics_history)
        }


# Global security monitor instance
security_monitor: Optional[SecurityMonitor] = None


def init_security() -> SecurityMonitor:
    """Initialize the global security monitor."""
    global security_monitor
    security_monitor = SecurityMonitor()
    return security_monitor


def get_security_monitor() -> Optional[SecurityMonitor]:
    """Get the global security monitor instance."""
    return security_monitor