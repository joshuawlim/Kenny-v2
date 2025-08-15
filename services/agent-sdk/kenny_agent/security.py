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
    """Monitors network egress traffic for policy violations."""
    
    def __init__(self):
        """Initialize egress monitor."""
        self.rules: Dict[str, EgressRule] = {}
        self.violation_handlers: List[Callable[[SecurityEvent], None]] = []
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
        """Check if egress connection is allowed."""
        for rule in self.rules.values():
            if rule.is_allowed(destination, port):
                logger.debug(f"Egress allowed: {source_service} -> {destination}:{port or 'any'}")
                return True
        
        # Egress violation detected
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


class SecurityEventCollector:
    """Central collector for security events."""
    
    def __init__(self):
        """Initialize security event collector."""
        self.events: List[SecurityEvent] = []
        self.max_events = 10000
        self.event_handlers: List[Callable[[SecurityEvent], None]] = []
    
    def collect_event(self, event: SecurityEvent):
        """Collect a security event."""
        self.events.append(event)
        
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
    
    def add_event_handler(self, handler: Callable[[SecurityEvent], None]):
        """Add handler for security events."""
        self.event_handlers.append(handler)
    
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


class SecurityMonitor:
    """Main security monitoring engine."""
    
    def __init__(self):
        """Initialize security monitor."""
        self.egress_monitor = EgressMonitor()
        self.data_access_monitor = DataAccessMonitor()
        self.event_collector = SecurityEventCollector()
        
        # Connect monitors to event collector
        self.egress_monitor.add_violation_handler(self.event_collector.collect_event)
        self.data_access_monitor.add_access_handler(self.event_collector.collect_event)
        
        # Add default event handler
        self.event_collector.add_event_handler(self._log_security_event)
    
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
    
    def get_security_dashboard(self, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive security dashboard."""
        return {
            "event_summary": self.event_collector.get_event_summary(),
            "recent_events": [e.to_dict() for e in self.event_collector.get_events(hours)],
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
            "time_period_hours": hours
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