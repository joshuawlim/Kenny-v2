"""
Alerting engine for the Kenny v2 multi-agent system.

This module provides comprehensive alerting capabilities for SLA violations,
performance degradation, security incidents, and system anomalies.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict, field
from enum import Enum
import json

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"
    INFO = "info"


class AlertType(str, Enum):
    """Types of alerts."""
    SLA_VIOLATION = "sla_violation"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    SECURITY_INCIDENT = "security_incident"
    POLICY_VIOLATION = "policy_violation"
    SYSTEM_ANOMALY = "system_anomaly"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


class AlertStatus(str, Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """Represents a system alert."""
    alert_id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    description: str
    source_service: str
    source_component: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: AlertStatus = AlertStatus.ACTIVE
    metadata: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    resolution_notes: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary representation."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["resolved_at"] = self.resolved_at.isoformat() if self.resolved_at else None
        data["alert_type"] = self.alert_type.value
        data["severity"] = self.severity.value
        data["status"] = self.status.value
        return data
    
    def acknowledge(self, acknowledged_by: str, notes: Optional[str] = None):
        """Acknowledge the alert."""
        self.status = AlertStatus.ACKNOWLEDGED
        self.acknowledged_by = acknowledged_by
        if notes:
            self.resolution_notes = notes
    
    def resolve(self, resolved_by: str, resolution_notes: str):
        """Resolve the alert."""
        self.status = AlertStatus.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolution_notes = resolution_notes
        self.acknowledged_by = resolved_by


@dataclass
class AlertRule:
    """Defines conditions for triggering alerts."""
    rule_id: str
    name: str
    description: str
    alert_type: AlertType
    severity: AlertSeverity
    conditions: Dict[str, Any]
    enabled: bool = True
    cooldown_seconds: int = 300  # 5 minute default cooldown
    max_alerts_per_hour: int = 10
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0
    
    def should_trigger(self, data: Dict[str, Any]) -> bool:
        """Check if the rule should trigger based on data."""
        if not self.enabled:
            return False
        
        # Check cooldown period
        if self.last_triggered:
            cooldown_end = self.last_triggered + timedelta(seconds=self.cooldown_seconds)
            if datetime.now(timezone.utc) < cooldown_end:
                return False
        
        # Check rate limiting
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        if self.last_triggered and self.last_triggered > one_hour_ago:
            if self.trigger_count >= self.max_alerts_per_hour:
                return False
        else:
            # Reset trigger count after one hour
            self.trigger_count = 0
        
        # Evaluate conditions
        return self._evaluate_conditions(data)
    
    def _evaluate_conditions(self, data: Dict[str, Any]) -> bool:
        """Evaluate rule conditions against data."""
        for condition_key, condition_value in self.conditions.items():
            if condition_key not in data:
                return False
            
            actual_value = data[condition_key]
            
            # Handle different condition types
            if isinstance(condition_value, dict):
                # Complex condition with operators
                if "gt" in condition_value and actual_value <= condition_value["gt"]:
                    return False
                if "lt" in condition_value and actual_value >= condition_value["lt"]:
                    return False
                if "gte" in condition_value and actual_value < condition_value["gte"]:
                    return False
                if "lte" in condition_value and actual_value > condition_value["lte"]:
                    return False
                if "eq" in condition_value and actual_value != condition_value["eq"]:
                    return False
                if "ne" in condition_value and actual_value == condition_value["ne"]:
                    return False
                if "contains" in condition_value and condition_value["contains"] not in str(actual_value):
                    return False
            else:
                # Simple equality check
                if actual_value != condition_value:
                    return False
        
        return True
    
    def trigger(self) -> None:
        """Mark the rule as triggered."""
        self.last_triggered = datetime.now(timezone.utc)
        self.trigger_count += 1


class AlertEngine:
    """Central alert engine for managing alerts and rules."""
    
    def __init__(self):
        """Initialize the alert engine."""
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable[[Alert], None]] = []
        self.max_history = 1000
        
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.rules[rule.rule_id] = rule
        logger.info(f"Added alert rule: {rule.name} ({rule.rule_id})")
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Removed alert rule: {rule_id}")
            return True
        return False
    
    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a notification handler for alerts."""
        self.notification_handlers.append(handler)
    
    def evaluate_data(self, data: Dict[str, Any]) -> List[Alert]:
        """Evaluate data against all rules and generate alerts."""
        triggered_alerts = []
        
        for rule in self.rules.values():
            if rule.should_trigger(data):
                alert = self._create_alert(rule, data)
                triggered_alerts.append(alert)
                rule.trigger()
        
        return triggered_alerts
    
    def _create_alert(self, rule: AlertRule, data: Dict[str, Any]) -> Alert:
        """Create an alert from a triggered rule."""
        import uuid
        
        alert_id = str(uuid.uuid4())
        
        # Generate alert description with data
        description = rule.description
        for key, value in data.items():
            description = description.replace(f"{{{key}}}", str(value))
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=rule.name,
            description=description,
            source_service=data.get("service_name", "unknown"),
            source_component=data.get("component", None),
            metadata=data.copy(),
            correlation_id=data.get("correlation_id")
        )
        
        # Store alert
        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)
        
        # Trim history if needed
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        # Send notifications
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
        
        logger.warning(f"Alert triggered: {alert.title} ({alert.severity.value})")
        return alert
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str, notes: Optional[str] = None) -> bool:
        """Acknowledge an alert."""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledge(acknowledged_by, notes)
            logger.info(f"Alert {alert_id} acknowledged by {acknowledged_by}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str, resolved_by: str, resolution_notes: str) -> bool:
        """Resolve an alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolve(resolved_by, resolution_notes)
            
            # Move to history
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert {alert_id} resolved by {resolved_by}")
            return True
        return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity."""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        # Sort by severity and timestamp
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3,
            AlertSeverity.INFO: 4
        }
        
        alerts.sort(key=lambda a: (severity_order[a.severity], a.timestamp), reverse=True)
        return alerts
    
    def get_alert_history(self, hours: int = 24, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get alert history for the specified time period."""
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        alerts = [alert for alert in self.alert_history if alert.timestamp >= cutoff_time]
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        alerts.sort(key=lambda a: a.timestamp, reverse=True)
        return alerts
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert statistics."""
        active_alerts = self.get_active_alerts()
        recent_history = self.get_alert_history(hours=24)
        
        # Count by severity
        active_by_severity = {}
        history_by_severity = {}
        
        for severity in AlertSeverity:
            active_by_severity[severity.value] = len([a for a in active_alerts if a.severity == severity])
            history_by_severity[severity.value] = len([a for a in recent_history if a.severity == severity])
        
        # Count by type
        active_by_type = {}
        for alert_type in AlertType:
            active_by_type[alert_type.value] = len([a for a in active_alerts if a.alert_type == alert_type])
        
        return {
            "active_alerts": {
                "total": len(active_alerts),
                "by_severity": active_by_severity,
                "by_type": active_by_type
            },
            "recent_history": {
                "total": len(recent_history),
                "by_severity": history_by_severity,
                "hours": 24
            },
            "rules": {
                "total": len(self.rules),
                "enabled": len([r for r in self.rules.values() if r.enabled])
            }
        }
    
    def load_default_rules(self) -> None:
        """Load default alert rules."""
        # SLA violation rules
        self.add_rule(AlertRule(
            rule_id="sla_response_time",
            name="Response Time SLA Violation",
            description="Response time {response_time_ms}ms exceeds SLA threshold",
            alert_type=AlertType.SLA_VIOLATION,
            severity=AlertSeverity.HIGH,
            conditions={"response_time_ms": {"gt": 2000}},
            cooldown_seconds=60
        ))
        
        self.add_rule(AlertRule(
            rule_id="sla_success_rate",
            name="Success Rate SLA Violation", 
            description="Success rate {success_rate_percent}% below SLA threshold",
            alert_type=AlertType.SLA_VIOLATION,
            severity=AlertSeverity.CRITICAL,
            conditions={"success_rate_percent": {"lt": 95.0}},
            cooldown_seconds=120
        ))
        
        # Performance degradation rules
        self.add_rule(AlertRule(
            rule_id="performance_degradation",
            name="Performance Degradation Detected",
            description="Performance degrading by {change_percent}%",
            alert_type=AlertType.PERFORMANCE_DEGRADATION,
            severity=AlertSeverity.MEDIUM,
            conditions={"trend": "degrading", "change_percent": {"gt": 30.0}},
            cooldown_seconds=300
        ))
        
        # Health check failure rules
        self.add_rule(AlertRule(
            rule_id="health_check_failure",
            name="Agent Health Check Failure",
            description="Agent {agent_id} health check failed: {error_message}",
            alert_type=AlertType.HEALTH_CHECK_FAILURE,
            severity=AlertSeverity.HIGH,
            conditions={"is_healthy": False},
            cooldown_seconds=180
        ))
        
        # Resource exhaustion rules
        self.add_rule(AlertRule(
            rule_id="high_error_rate",
            name="High Error Rate Detected",
            description="Error count {error_count} exceeds threshold",
            alert_type=AlertType.SYSTEM_ANOMALY,
            severity=AlertSeverity.MEDIUM,
            conditions={"error_count": {"gt": 25}},
            cooldown_seconds=240
        ))
        
        logger.info(f"Loaded {len(self.rules)} default alert rules")


class AlertNotifier:
    """Handles alert notifications through various channels."""
    
    def __init__(self):
        """Initialize alert notifier."""
        self.channels: Dict[str, Callable[[Alert], None]] = {}
    
    def add_channel(self, name: str, handler: Callable[[Alert], None]) -> None:
        """Add a notification channel."""
        self.channels[name] = handler
        logger.info(f"Added notification channel: {name}")
    
    def notify(self, alert: Alert) -> None:
        """Send alert through all channels."""
        for name, handler in self.channels.items():
            try:
                handler(alert)
                logger.debug(f"Sent alert {alert.alert_id} via {name}")
            except Exception as e:
                logger.error(f"Failed to send alert via {name}: {e}")
    
    def log_notification(self, alert: Alert) -> None:
        """Log alert to application logs."""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.INFO: logging.INFO
        }.get(alert.severity, logging.INFO)
        
        logger.log(log_level, f"ALERT [{alert.severity.value.upper()}] {alert.title}: {alert.description}")


# Global alert engine instance
alert_engine: Optional[AlertEngine] = None


def init_alerting() -> AlertEngine:
    """Initialize the global alert engine."""
    global alert_engine
    alert_engine = AlertEngine()
    alert_engine.load_default_rules()
    
    # Add default log notification handler
    notifier = AlertNotifier()
    notifier.add_channel("logs", notifier.log_notification)
    alert_engine.add_notification_handler(notifier.notify)
    
    return alert_engine


def get_alert_engine() -> Optional[AlertEngine]:
    """Get the global alert engine instance."""
    return alert_engine