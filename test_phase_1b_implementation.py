#!/usr/bin/env python3
"""
Test script for Phase 1B Agent Transformations
Validates intelligent agent implementations and natural language processing.
"""

import asyncio
import json
import aiohttp
from typing import Dict, Any
import sys

# Test configuration
SERVICES = {
    "coordinator": "http://localhost:8002",
    "mail-agent": "http://localhost:8000", 
    "contacts-agent": "http://localhost:8003",
    "imessage-agent": "http://localhost:8006",
    "calendar-agent": "http://localhost:8007",
    "registry": "http://localhost:8001",
    "gateway": "http://localhost:9000"
}

# Natural language test queries
TEST_QUERIES = [
    # Clear, well-formed queries
    {
        "query": "find my recent emails",
        "expected_intent": "mail_operation",
        "expected_agent": "intelligent-mail-agent"
    },
    {
        "query": "search for contact named Sarah",
        "expected_intent": "contacts_operation", 
        "expected_agent": "intelligent-contacts-agent"
    },
    {
        "query": "show me today's meetings",
        "expected_intent": "calendar_operation",
        "expected_agent": "intelligent-calendar-agent"
    },
    
    # Imperfect/ambiguous queries (best-guess testing)
    {
        "query": "find sarah",
        "description": "Ambiguous query - could be contact or message search",
        "minimum_confidence": 0.3
    },
    {
        "query": "what meetings",
        "description": "Incomplete query missing time context",
        "minimum_confidence": 0.3
    },
    {
        "query": "show emails from yesterday",
        "description": "Natural language with time reference",
        "expected_intent": "mail_operation"
    },
    {
        "query": "schedule meeting with john",
        "description": "Action request with natural language",
        "expected_intent": "calendar_operation"
    }
]

class Phase1BValidator:
    """Validates Phase 1B implementation components."""
    
    def __init__(self):
        self.session = None
        self.results = {
            "service_health": {},
            "intelligent_agents": {},
            "coordinator_nlp": {},
            "query_tests": [],
            "overall_status": "UNKNOWN"
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30))
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def test_service_health(self):
        """Test basic health of all services."""
        print("\n🔍 Testing Service Health...")
        
        for service_name, base_url in SERVICES.items():
            try:
                async with self.session.get(f"{base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results["service_health"][service_name] = {
                            "status": "healthy",
                            "response_code": response.status,
                            "data": data
                        }
                        print(f"  ✅ {service_name}: healthy")
                    else:
                        self.results["service_health"][service_name] = {
                            "status": "unhealthy",
                            "response_code": response.status
                        }
                        print(f"  ❌ {service_name}: unhealthy (status {response.status})")
            except Exception as e:
                self.results["service_health"][service_name] = {
                    "status": "error",
                    "error": str(e)
                }
                print(f"  ❌ {service_name}: error - {e}")
    
    async def test_intelligent_agent_manifests(self):
        """Test that agents are properly registered as intelligent services."""
        print("\n🤖 Testing Intelligent Agent Manifests...")
        
        intelligent_agents = ["intelligent-mail-agent", "intelligent-contacts-agent", 
                            "intelligent-imessage-agent", "intelligent-calendar-agent"]
        
        try:
            # Get all registered agents from registry
            async with self.session.get(f"{SERVICES['registry']}/agents") as response:
                if response.status == 200:
                    agents_data = await response.json()
                    registered_agents = agents_data.get("agents", [])
                    
                    for agent_id in intelligent_agents:
                        agent_info = next((a for a in registered_agents if a.get("agent_id") == agent_id), None)
                        
                        if agent_info:
                            manifest = agent_info.get("manifest", {})
                            agent_type = manifest.get("agent_type", "unknown")
                            llm_model = manifest.get("tool_access", [])
                            
                            is_intelligent = agent_type == "intelligent_service"
                            has_llm = "llama3.2:3b" in llm_model
                            
                            self.results["intelligent_agents"][agent_id] = {
                                "registered": True,
                                "agent_type": agent_type,
                                "is_intelligent": is_intelligent,
                                "has_llm_model": has_llm,
                                "manifest": manifest
                            }
                            
                            status_icon = "✅" if is_intelligent and has_llm else "⚠️"
                            print(f"  {status_icon} {agent_id}: type={agent_type}, llm={has_llm}")
                        else:
                            self.results["intelligent_agents"][agent_id] = {
                                "registered": False,
                                "error": "Agent not found in registry"
                            }
                            print(f"  ❌ {agent_id}: not registered")
                else:
                    print(f"  ❌ Failed to get agents from registry (status {response.status})")
        except Exception as e:
            print(f"  ❌ Error testing agent manifests: {e}")
    
    async def test_coordinator_nlp_enhancements(self):
        """Test coordinator's enhanced NLP capabilities."""
        print("\n🧠 Testing Coordinator NLP Enhancements...")
        
        # Test a simple query to see if enhanced routing works
        test_query = "find recent emails"
        
        try:
            async with self.session.post(
                f"{SERVICES['coordinator']}/process",
                json={"user_input": test_query}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    context = data.get("context", {})
                    
                    # Check for enhanced routing features
                    has_confidence = "confidence" in context
                    has_interpretation = "interpretation" in context
                    has_best_guess = "is_best_guess" in context
                    has_fallback_options = "fallback_options" in context
                    
                    self.results["coordinator_nlp"] = {
                        "status": "working",
                        "has_confidence_scoring": has_confidence,
                        "has_interpretation": has_interpretation, 
                        "has_best_guess_capability": has_best_guess,
                        "has_fallback_options": has_fallback_options,
                        "test_response": data
                    }
                    
                    confidence = context.get("confidence", 0)
                    intent = context.get("intent", "unknown")
                    
                    print(f"  ✅ Coordinator NLP: intent={intent}, confidence={confidence:.2f}")
                    print(f"  ✅ Enhanced features: confidence={has_confidence}, interpretation={has_interpretation}")
                    print(f"  ✅ Best-guess capability: {has_best_guess}, fallback options: {has_fallback_options}")
                else:
                    self.results["coordinator_nlp"] = {
                        "status": "error",
                        "response_code": response.status
                    }
                    print(f"  ❌ Coordinator test failed (status {response.status})")
        except Exception as e:
            self.results["coordinator_nlp"] = {
                "status": "error", 
                "error": str(e)
            }
            print(f"  ❌ Coordinator NLP test error: {e}")
    
    async def test_natural_language_queries(self):
        """Test natural language queries with enhanced processing."""
        print("\n💬 Testing Natural Language Queries...")
        
        for i, test_case in enumerate(TEST_QUERIES):
            query = test_case["query"]
            description = test_case.get("description", "Standard query test")
            
            print(f"\n  Test {i+1}: '{query}' ({description})")
            
            try:
                # Test via gateway (end-to-end)
                async with self.session.post(
                    f"{SERVICES['gateway']}/query",
                    json={"query": query}
                ) as response:
                    
                    result = {
                        "query": query,
                        "description": description,
                        "status_code": response.status,
                        "success": response.status == 200
                    }
                    
                    if response.status == 200:
                        data = await response.json()
                        result["response_data"] = data
                        
                        # Check routing accuracy
                        intent = data.get("intent")
                        confidence = data.get("confidence", 0)
                        agents_used = data.get("agents_used", [])
                        
                        result["intent"] = intent
                        result["confidence"] = confidence
                        result["agents_used"] = agents_used
                        
                        # Validate against expectations
                        if "expected_intent" in test_case:
                            result["intent_match"] = intent == test_case["expected_intent"]
                        
                        if "expected_agent" in test_case:
                            result["agent_match"] = test_case["expected_agent"] in agents_used
                        
                        if "minimum_confidence" in test_case:
                            result["confidence_adequate"] = confidence >= test_case["minimum_confidence"]
                        
                        # Print results
                        status_icon = "✅" if result["success"] else "❌"
                        print(f"    {status_icon} Response: intent={intent}, confidence={confidence:.2f}")
                        
                        if "intent_match" in result:
                            match_icon = "✅" if result["intent_match"] else "❌"
                            print(f"    {match_icon} Intent match: expected={test_case['expected_intent']}, got={intent}")
                        
                        if "agent_match" in result:
                            match_icon = "✅" if result["agent_match"] else "❌"
                            print(f"    {match_icon} Agent match: expected={test_case['expected_agent']}, used={agents_used}")
                        
                        if "confidence_adequate" in result:
                            conf_icon = "✅" if result["confidence_adequate"] else "⚠️"
                            print(f"    {conf_icon} Confidence adequate: {confidence:.2f} >= {test_case['minimum_confidence']}")
                    
                    else:
                        error_text = await response.text()
                        result["error"] = error_text
                        print(f"    ❌ Query failed: {response.status} - {error_text}")
                    
                    self.results["query_tests"].append(result)
            
            except Exception as e:
                result = {
                    "query": query,
                    "description": description,
                    "success": False,
                    "error": str(e)
                }
                self.results["query_tests"].append(result)
                print(f"    ❌ Query error: {e}")
    
    def generate_summary(self):
        """Generate test summary and overall status."""
        print("\n" + "="*60)
        print("🎯 PHASE 1B IMPLEMENTATION VALIDATION SUMMARY")
        print("="*60)
        
        # Service health summary
        healthy_services = sum(1 for s in self.results["service_health"].values() if s.get("status") == "healthy")
        total_services = len(SERVICES)
        print(f"\n📊 Service Health: {healthy_services}/{total_services} services healthy")
        
        # Intelligent agents summary
        intelligent_count = sum(1 for a in self.results["intelligent_agents"].values() 
                              if a.get("is_intelligent") and a.get("has_llm_model"))
        total_intelligent_agents = 4  # Expected intelligent agents
        print(f"🤖 Intelligent Agents: {intelligent_count}/{total_intelligent_agents} properly configured")
        
        # Coordinator NLP summary
        coordinator_working = self.results["coordinator_nlp"].get("status") == "working"
        enhanced_features = sum([
            self.results["coordinator_nlp"].get("has_confidence_scoring", False),
            self.results["coordinator_nlp"].get("has_interpretation", False),
            self.results["coordinator_nlp"].get("has_best_guess_capability", False),
            self.results["coordinator_nlp"].get("has_fallback_options", False)
        ])
        print(f"🧠 Coordinator NLP: {'Working' if coordinator_working else 'Failed'}, {enhanced_features}/4 enhanced features")
        
        # Query tests summary  
        successful_queries = sum(1 for q in self.results["query_tests"] if q.get("success"))
        total_queries = len(TEST_QUERIES)
        print(f"💬 Natural Language Queries: {successful_queries}/{total_queries} successful")
        
        # Overall assessment
        overall_score = (
            (healthy_services / total_services) * 0.3 +
            (intelligent_count / total_intelligent_agents) * 0.3 +
            (1 if coordinator_working else 0) * 0.2 +
            (successful_queries / total_queries) * 0.2
        )
        
        if overall_score >= 0.9:
            self.results["overall_status"] = "EXCELLENT"
            status_icon = "🎉"
        elif overall_score >= 0.7:
            self.results["overall_status"] = "GOOD"
            status_icon = "✅"
        elif overall_score >= 0.5:
            self.results["overall_status"] = "FAIR"
            status_icon = "⚠️"
        else:
            self.results["overall_status"] = "POOR"
            status_icon = "❌"
        
        print(f"\n{status_icon} Overall Status: {self.results['overall_status']} (Score: {overall_score:.2f})")
        
        # Recommendations
        print("\n📋 Recommendations:")
        if healthy_services < total_services:
            print("  • Check unhealthy services and restart if needed")
        if intelligent_count < total_intelligent_agents:
            print("  • Verify intelligent agent configurations and manifests")
        if not coordinator_working:
            print("  • Check coordinator LLM integration and router configuration")
        if successful_queries < total_queries:
            print("  • Review failed queries and improve intent classification")
        
        if overall_score >= 0.9:
            print("  🎉 Phase 1B implementation looks excellent! All systems operational.")
        
        return self.results["overall_status"]

async def main():
    """Run Phase 1B validation tests."""
    print("🚀 Starting Phase 1B Agent Transformations Validation")
    print("="*60)
    
    async with Phase1BValidator() as validator:
        # Run all validation tests
        await validator.test_service_health()
        await validator.test_intelligent_agent_manifests()
        await validator.test_coordinator_nlp_enhancements()
        await validator.test_natural_language_queries()
        
        # Generate summary
        status = validator.generate_summary()
        
        # Save detailed results
        with open("phase_1b_validation_results.json", "w") as f:
            json.dump(validator.results, f, indent=2, default=str)
        
        print(f"\n💾 Detailed results saved to: phase_1b_validation_results.json")
        
        # Return appropriate exit code
        return 0 if status in ["EXCELLENT", "GOOD"] else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Validation failed with error: {e}")
        sys.exit(1)