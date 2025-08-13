#!/usr/bin/env python3
"""
Simple test script to verify coordinator service functionality
"""

import asyncio
import json
from src.coordinator import Coordinator
from src.policy.engine import PolicyEngine, PolicyAction

async def test_coordinator():
    """Test the coordinator functionality"""
    print("Testing Coordinator Service...")
    
    # Test coordinator
    coordinator = Coordinator()
    
    # Test graph info
    graph_info = coordinator.get_graph_info()
    print(f"Graph Info: {json.dumps(graph_info, indent=2)}")
    
    # Test processing requests
    test_inputs = [
        "check my email",
        "schedule a meeting tomorrow",
        "what's the weather like"
    ]
    
    for user_input in test_inputs:
        print(f"\nProcessing: '{user_input}'")
        result = await coordinator.process_request(user_input)
        print(f"Intent: {result['context'].get('intent')}")
        print(f"Plan: {result['context'].get('plan')}")
        print(f"Execution Path: {result['execution_path']}")
        print(f"Results: {result['results']}")
    
    print("\n" + "="*50)
    
    # Test policy engine
    print("Testing Policy Engine...")
    engine = PolicyEngine()
    engine.load_default_rules()
    
    # Show default rules
    rules = engine.get_rules()
    print(f"Default Rules ({len(rules)}):")
    for rule in rules:
        print(f"  - {rule['name']}: {rule['action']} (Priority: {rule['priority']})")
    
    # Test policy evaluation
    test_contexts = [
        {"operation": "calendar_write", "resource": "calendar"},
        {"operation": "mail_read", "resource": "mail"},
        {"operation": "network_egress", "resource": "external_api"}
    ]
    
    for context in test_contexts:
        print(f"\nEvaluating policy for: {context}")
        result = engine.evaluate_policy(context)
        if result['final_decision']:
            decision = result['final_decision']
            print(f"  Decision: {decision['action']} (Rule: {decision['rule_name']})")
            print(f"  Requires Approval: {decision['requires_approval']}")
        else:
            print("  No applicable rules found")
    
    print("\nCoordinator Service test completed successfully!")

if __name__ == "__main__":
    asyncio.run(test_coordinator())
