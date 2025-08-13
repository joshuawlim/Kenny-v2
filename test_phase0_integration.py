#!/usr/bin/env python3
"""
Phase 0 Integration Test

This script tests that all Phase 0 components can work together
and are properly accessible from the project root.
"""

import sys
import os

def test_agent_sdk_import():
    """Test that Agent SDK can be imported from project root."""
    try:
        from kenny_agent import (
            BaseAgent, 
            BaseCapabilityHandler, 
            BaseTool, 
            HealthStatus, 
            HealthCheck, 
            HealthMonitor, 
            AgentRegistryClient
        )
        print("✅ Agent SDK imports successful from project root")
        return True
    except ImportError as e:
        print(f"❌ Agent SDK import failed: {e}")
        return False

def test_agent_sdk_functionality():
    """Test basic Agent SDK functionality from project root."""
    try:
        from kenny_agent import HealthStatus, HealthCheck
        
        # Test basic functionality
        status = HealthStatus("healthy", "Test status")
        assert status.status == "healthy"
        
        def test_check():
            return HealthStatus("healthy", "Check passed")
        
        health_check = HealthCheck("test", test_check)
        result = health_check.execute()
        assert result.status == "healthy"
        
        print("✅ Agent SDK functionality working from project root")
        return True
    except Exception as e:
        print(f"❌ Agent SDK functionality test failed: {e}")
        return False

def test_project_structure():
    """Test that project structure is correct."""
    expected_dirs = [
        "services/agent-registry",
        "services/coordinator", 
        "services/agent-sdk",
        "docs/architecture",
        "infra"
    ]
    
    missing_dirs = []
    for dir_path in expected_dirs:
        if not os.path.exists(dir_path):
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        print(f"❌ Missing expected directories: {missing_dirs}")
        return False
    
    print("✅ Project structure is correct")
    return True

def test_roadmap_status():
    """Test that roadmap reflects Phase 0 completion."""
    try:
        with open("roadmap.md", "r") as f:
            content = f.read()
        
        # Check for Phase 0 completion indicators
        phase0_completed = all([
            "Phase 0.1 (Agent Registry Service): ✅ **COMPLETED**" in content or "0.1 Agent Registry Service ✅ **COMPLETED**" in content,
            "Phase 0.2 (Coordinator Skeleton): ✅ **COMPLETED**" in content or "0.2 Coordinator Skeleton (LangGraph) ✅ **COMPLETED**" in content,
            "Phase 0.3 (Agent SDK): ✅ **COMPLETED**" in content or "0.3 Base Agent Framework (Agent SDK) ✅ **COMPLETED**" in content
        ])
        
        if phase0_completed:
            print("✅ Roadmap correctly reflects Phase 0 completion")
            return True
        else:
            print("❌ Roadmap does not reflect Phase 0 completion")
            return False
            
    except Exception as e:
        print(f"❌ Roadmap status check failed: {e}")
        return False

def main():
    """Run all Phase 0 integration tests."""
    print("=== Phase 0 Integration Testing ===\n")
    
    tests = [
        test_project_structure,
        test_agent_sdk_import,
        test_agent_sdk_functionality,
        test_roadmap_status
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All Phase 0 integration tests passed!")
        print("Phase 0 is ready for Git commit and Phase 1 development.")
        return 0
    else:
        print("❌ Some integration tests failed. Please fix issues before proceeding.")
        return 1

if __name__ == "__main__":
    exit(main())
