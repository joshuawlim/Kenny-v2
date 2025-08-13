#!/usr/bin/env python3
"""
Test script to verify the Kenny Agent SDK package installation.

This script tests that all the main classes can be imported and
basic functionality works.
"""

def test_imports():
    """Test that all main classes can be imported."""
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
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_basic_classes():
    """Test that basic classes can be instantiated."""
    try:
        from kenny_agent import HealthStatus, HealthCheck
        
        # Test HealthStatus
        status = HealthStatus("healthy", "Test status")
        assert status.status == "healthy"
        assert status.message == "Test status"
        
        # Test HealthCheck
        def test_check():
            return HealthStatus("healthy", "Check passed")
        
        health_check = HealthCheck("test", test_check)
        result = health_check.execute()
        assert result.status == "healthy"
        
        print("✅ Basic classes work correctly")
        return True
    except Exception as e:
        print(f"❌ Basic class test failed: {e}")
        return False


def test_abstract_classes():
    """Test that abstract classes cannot be instantiated."""
    try:
        from kenny_agent import BaseAgent, BaseCapabilityHandler, BaseTool
        
        # Test that abstract classes raise TypeError
        try:
            BaseAgent("test", "test", "test")
            print("❌ BaseAgent should not be instantiable")
            return False
        except TypeError:
            pass
        
        try:
            BaseCapabilityHandler("test", "test")
            print("❌ BaseCapabilityHandler should not be instantiable")
            return False
        except TypeError:
            pass
        
        try:
            BaseTool("test", "test")
            print("❌ BaseTool should not be instantiable")
            return False
        except TypeError:
            pass
        
        print("✅ Abstract classes properly protected")
        return True
    except Exception as e:
        print(f"❌ Abstract class test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing Kenny Agent SDK Installation...\n")
    
    tests = [
        test_imports,
        test_basic_classes,
        test_abstract_classes
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Package installation is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the installation.")
        return 1


if __name__ == "__main__":
    exit(main())
