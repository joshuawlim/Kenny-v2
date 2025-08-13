import logging
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class PolicyAction(Enum):
    """Types of policy actions"""
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    AUDIT = "audit"

class PolicyRule:
    """A policy rule definition"""
    
    def __init__(self, rule_id: str, name: str, action: PolicyAction, 
                 conditions: Dict[str, Any], priority: int = 100):
        self.rule_id = rule_id
        self.name = name
        self.action = action
        self.conditions = conditions
        self.priority = priority
        self.enabled = True
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluate if this rule applies to the given context"""
        if not self.enabled:
            return False
        
        for key, expected_value in self.conditions.items():
            if key not in context:
                return False
            
            actual_value = context[key]
            
            # Simple equality check for now
            if actual_value != expected_value:
                return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule to dictionary representation"""
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "action": self.action.value,
            "conditions": self.conditions,
            "priority": self.priority,
            "enabled": self.enabled
        }

class PolicyEngine:
    """Basic policy engine for rule evaluation and enforcement"""
    
    def __init__(self):
        self.rules: List[PolicyRule] = []
        self.rule_counter = 0
    
    def add_rule(self, name: str, action: PolicyAction, conditions: Dict[str, Any], 
                 priority: int = 100) -> str:
        """Add a new policy rule"""
        rule_id = f"rule_{self.rule_counter:04d}"
        self.rule_counter += 1
        
        rule = PolicyRule(rule_id, name, action, conditions, priority)
        self.rules.append(rule)
        
        # Sort rules by priority (higher priority first)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
        
        logger.info(f"Added policy rule: {name} (ID: {rule_id})")
        return rule_id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a policy rule by ID"""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                removed_rule = self.rules.pop(i)
                logger.info(f"Removed policy rule: {removed_rule.name} (ID: {rule_id})")
                return True
        return False
    
    def enable_rule(self, rule_id: str) -> bool:
        """Enable a policy rule"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = True
                logger.info(f"Enabled policy rule: {rule.name} (ID: {rule_id})")
                return True
        return False
    
    def disable_rule(self, rule_id: str) -> bool:
        """Disable a policy rule"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                rule.enabled = False
                logger.info(f"Disabled policy rule: {rule.name} (ID: {rule_id})")
                return True
        return False
    
    def evaluate_policy(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate all applicable policy rules for the given context"""
        applicable_rules = []
        decisions = []
        
        for rule in self.rules:
            if rule.evaluate(context):
                applicable_rules.append(rule)
                decisions.append({
                    "rule_id": rule.rule_id,
                    "rule_name": rule.name,
                    "action": rule.action.value,
                    "priority": rule.priority
                })
        
        # Determine final decision based on highest priority rule
        final_decision = None
        if applicable_rules:
            highest_priority_rule = applicable_rules[0]
            final_decision = {
                "action": highest_priority_rule.action.value,
                "rule_id": highest_priority_rule.rule_id,
                "rule_name": highest_priority_rule.name,
                "requires_approval": highest_priority_rule.action == PolicyAction.REQUIRE_APPROVAL
            }
        
        return {
            "context": context,
            "applicable_rules": decisions,
            "final_decision": final_decision,
            "total_rules_evaluated": len(self.rules),
            "applicable_rules_count": len(applicable_rules)
        }
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get all policy rules"""
        return [rule.to_dict() for rule in self.rules]
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific policy rule by ID"""
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule.to_dict()
        return None
    
    def clear_rules(self):
        """Clear all policy rules"""
        self.rules.clear()
        self.rule_counter = 0
        logger.info("Cleared all policy rules")
    
    def load_default_rules(self):
        """Load default policy rules"""
        # Calendar approval rule
        self.add_rule(
            name="Calendar Write Approval",
            action=PolicyAction.REQUIRE_APPROVAL,
            conditions={"operation": "calendar_write", "resource": "calendar"},
            priority=100
        )
        
        # Mail read rule
        self.add_rule(
            name="Mail Read Allow",
            action=PolicyAction.ALLOW,
            conditions={"operation": "mail_read", "resource": "mail"},
            priority=50
        )
        
        # Network egress rule
        self.add_rule(
            name="Network Egress Deny",
            action=PolicyAction.DENY,
            conditions={"operation": "network_egress", "resource": "external_api"},
            priority=200
        )
        
        logger.info("Loaded default policy rules")
