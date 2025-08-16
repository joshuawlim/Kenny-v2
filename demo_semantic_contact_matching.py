#!/usr/bin/env python3
"""
Demonstration of semantic contact matching with confidence scoring
"""

import asyncio
import sys

# Add agent-sdk to path
sys.path.append('services/agent-sdk')

from kenny_agent.agent_service_base import AgentServiceBase

class SemanticContactMatcher(AgentServiceBase):
    """Contact matching with advanced semantic analysis and confidence scoring."""
    
    def __init__(self):
        super().__init__(
            agent_id="semantic-contact-matcher",
            name="Semantic Contact Matcher",
            description="Advanced contact matching with confidence scoring and fuzzy resolution",
            version="2.1.0"
        )
        
        # Mock contact database with rich metadata
        self.contacts = [
            {
                "id": "c001",
                "name": "John Smith",
                "emails": ["john.smith@company.com", "j.smith@gmail.com"],
                "phones": ["+1-555-0123"],
                "titles": ["Senior Software Engineer", "Lead Developer"],
                "teams": ["Engineering", "Backend Team"],
                "aliases": ["Johnny", "J.Smith"],
                "companies": ["TechCorp", "StartupXYZ"]
            },
            {
                "id": "c002", 
                "name": "Sarah Johnson",
                "emails": ["sarah.j@company.com", "sarah.johnson@design.co"],
                "phones": ["+1-555-0456"],
                "titles": ["Lead UX Designer", "Design Team Lead"],
                "teams": ["Design", "Product"],
                "aliases": ["Sarah J", "SJ"],
                "companies": ["TechCorp", "DesignStudio"]
            },
            {
                "id": "c003",
                "name": "Michael Rodriguez",
                "emails": ["mike.r@company.com", "michael@pm-consulting.com"],
                "phones": ["+1-555-0789"],
                "titles": ["Senior Project Manager", "Agile Coach"],
                "teams": ["Product", "Management"],
                "aliases": ["Mike", "Mikey", "Michael R"],
                "companies": ["TechCorp"]
            },
            {
                "id": "c004",
                "name": "Jennifer Chen",
                "emails": ["jen.chen@company.com", "jennifer@techblog.com"],
                "phones": ["+1-555-0321"],
                "titles": ["DevOps Engineer", "Infrastructure Lead"],
                "teams": ["Engineering", "Platform"],
                "aliases": ["Jen", "Jenny"],
                "companies": ["TechCorp", "CloudFirst"]
            }
        ]
        
        self.fallback_capability = "basic_search"
        self.capabilities = {
            "semantic_match": "Advanced semantic contact matching",
            "confidence_search": "Search with confidence thresholds",
            "fuzzy_resolution": "Fuzzy name and attribute resolution",
            "basic_search": "Basic fallback search"
        }
    
    def get_agent_context(self) -> str:
        return """Semantic contact matching agent that understands:
- Natural language queries about people
- Fuzzy name matching and abbreviations
- Role and team-based searches
- Confidence-scored results with detailed reasoning
"""
    
    async def execute_capability(self, capability: str, parameters: dict):
        """Execute semantic matching capabilities."""
        if capability == "semantic_match":
            return await self._semantic_match(parameters)
        elif capability == "confidence_search":
            return await self._confidence_search(parameters)
        elif capability == "fuzzy_resolution":
            return await self._fuzzy_resolution(parameters)
        elif capability == "basic_search":
            return await self._basic_search(parameters)
        else:
            return {"success": False, "error": f"Unknown capability: {capability}"}
    
    async def _semantic_match(self, parameters: dict):
        """Advanced semantic matching with detailed confidence analysis."""
        query = parameters.get("query", "").lower()
        min_confidence = parameters.get("min_confidence", 0.3)
        
        matches = []
        
        for contact in self.contacts:
            confidence_breakdown = self._calculate_detailed_confidence(query, contact)
            total_confidence = confidence_breakdown["total_confidence"]
            
            if total_confidence >= min_confidence:
                match = {
                    "contact": contact,
                    "confidence": total_confidence,
                    "confidence_breakdown": confidence_breakdown,
                    "match_reasons": self._generate_match_reasons(query, contact, confidence_breakdown)
                }
                matches.append(match)
        
        # Sort by confidence
        matches.sort(key=lambda x: x["confidence"], reverse=True)
        
        return {
            "success": True,
            "query": query,
            "matches": matches,
            "total_candidates": len(self.contacts),
            "matching_method": "semantic_analysis"
        }
    
    def _calculate_detailed_confidence(self, query: str, contact: dict) -> dict:
        """Calculate detailed confidence with breakdown by match type."""
        breakdown = {
            "exact_name_match": 0.0,
            "partial_name_match": 0.0,
            "email_match": 0.0,
            "phone_match": 0.0,
            "title_match": 0.0,
            "team_match": 0.0,
            "alias_match": 0.0,
            "company_match": 0.0,
            "fuzzy_similarity": 0.0
        }
        
        # Exact name match (highest confidence)
        if query == contact["name"].lower():
            breakdown["exact_name_match"] = 1.0
        
        # Partial name match
        name_words = contact["name"].lower().split()
        query_words = query.split()
        name_overlap = sum(1 for word in query_words if any(word in name_word for name_word in name_words))
        if name_overlap > 0:
            breakdown["partial_name_match"] = (name_overlap / max(len(query_words), len(name_words))) * 0.8
        
        # Email matching
        for email in contact["emails"]:
            if query in email.lower():
                breakdown["email_match"] = 0.95
                break
            elif any(word in email.lower() for word in query_words):
                breakdown["email_match"] = max(breakdown["email_match"], 0.7)
        
        # Phone matching
        clean_query = ''.join(filter(str.isdigit, query))
        if clean_query:
            for phone in contact["phones"]:
                clean_phone = ''.join(filter(str.isdigit, phone))
                if clean_query in clean_phone:
                    breakdown["phone_match"] = 0.9
                    break
        
        # Title matching
        for title in contact["titles"]:
            title_words = title.lower().split()
            title_overlap = sum(1 for word in query_words if any(word in title_word for title_word in title_words))
            if title_overlap > 0:
                breakdown["title_match"] = max(breakdown["title_match"], (title_overlap / len(query_words)) * 0.7)
        
        # Team matching
        for team in contact["teams"]:
            if any(word in team.lower() for word in query_words):
                breakdown["team_match"] = 0.6
                break
        
        # Alias matching
        for alias in contact["aliases"]:
            if query in alias.lower() or alias.lower() in query:
                breakdown["alias_match"] = 0.8
                break
        
        # Company matching
        for company in contact["companies"]:
            if any(word in company.lower() for word in query_words):
                breakdown["company_match"] = 0.5
                break
        
        # Fuzzy similarity (simple Levenshtein-like)
        name_similarity = self._fuzzy_similarity(query, contact["name"].lower())
        breakdown["fuzzy_similarity"] = name_similarity * 0.6
        
        # Calculate total confidence (weighted combination)
        weights = {
            "exact_name_match": 1.0,
            "partial_name_match": 0.8,
            "email_match": 0.9,
            "phone_match": 0.9,
            "title_match": 0.7,
            "team_match": 0.6,
            "alias_match": 0.8,
            "company_match": 0.5,
            "fuzzy_similarity": 0.4
        }
        
        total_confidence = sum(breakdown[key] * weights[key] for key in breakdown)
        total_confidence = min(total_confidence, 1.0)  # Cap at 1.0
        
        breakdown["total_confidence"] = total_confidence
        breakdown["weights_used"] = weights
        
        return breakdown
    
    def _fuzzy_similarity(self, s1: str, s2: str) -> float:
        """Simple fuzzy string similarity (0.0 to 1.0)."""
        if not s1 or not s2:
            return 0.0
        
        # Simple character overlap similarity
        s1_chars = set(s1.lower())
        s2_chars = set(s2.lower())
        
        intersection = len(s1_chars & s2_chars)
        union = len(s1_chars | s2_chars)
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_match_reasons(self, query: str, contact: dict, breakdown: dict) -> list:
        """Generate human-readable reasons for the match."""
        reasons = []
        
        if breakdown["exact_name_match"] > 0:
            reasons.append(f"Exact name match: '{contact['name']}'")
        
        if breakdown["partial_name_match"] > 0.5:
            reasons.append(f"Strong name similarity")
        
        if breakdown["email_match"] > 0.8:
            matching_emails = [email for email in contact["emails"] if query in email.lower()]
            if matching_emails:
                reasons.append(f"Email match: {matching_emails[0]}")
        
        if breakdown["phone_match"] > 0:
            reasons.append(f"Phone number match")
        
        if breakdown["title_match"] > 0.5:
            matching_titles = [title for title in contact["titles"] if any(word in title.lower() for word in query.split())]
            if matching_titles:
                reasons.append(f"Title match: {matching_titles[0]}")
        
        if breakdown["team_match"] > 0:
            matching_teams = [team for team in contact["teams"] if any(word in team.lower() for word in query.split())]
            if matching_teams:
                reasons.append(f"Team match: {matching_teams[0]}")
        
        if breakdown["alias_match"] > 0:
            reasons.append(f"Known alias match")
        
        if breakdown["company_match"] > 0:
            reasons.append(f"Company association")
        
        if breakdown["fuzzy_similarity"] > 0.3:
            reasons.append(f"Name similarity: {breakdown['fuzzy_similarity']:.2f}")
        
        return reasons
    
    async def _confidence_search(self, parameters: dict):
        """Search with specific confidence thresholds."""
        query = parameters.get("query", "")
        confidence_tiers = parameters.get("confidence_tiers", [0.9, 0.7, 0.5, 0.3])
        
        results_by_tier = {}
        
        for tier in confidence_tiers:
            result = await self._semantic_match({"query": query, "min_confidence": tier})
            results_by_tier[f"tier_{tier:.1f}"] = {
                "min_confidence": tier,
                "matches": result["matches"],
                "count": len(result["matches"])
            }
        
        return {
            "success": True,
            "query": query,
            "confidence_tiers": results_by_tier,
            "analysis": "Results grouped by confidence threshold"
        }
    
    async def _fuzzy_resolution(self, parameters: dict):
        """Fuzzy resolution with detailed similarity analysis."""
        query = parameters.get("query", "")
        
        similarity_results = []
        
        for contact in self.contacts:
            # Calculate various similarity metrics
            name_similarity = self._fuzzy_similarity(query, contact["name"])
            
            # Check each alias
            alias_similarities = [self._fuzzy_similarity(query, alias) for alias in contact["aliases"]]
            max_alias_similarity = max(alias_similarities) if alias_similarities else 0.0
            
            # Overall fuzzy score
            overall_similarity = max(name_similarity, max_alias_similarity)
            
            if overall_similarity > 0.1:  # Very low threshold for fuzzy
                similarity_results.append({
                    "contact": contact,
                    "name_similarity": name_similarity,
                    "best_alias_similarity": max_alias_similarity,
                    "overall_similarity": overall_similarity,
                    "fuzzy_confidence": overall_similarity * 0.8  # Scale down for fuzzy
                })
        
        # Sort by similarity
        similarity_results.sort(key=lambda x: x["overall_similarity"], reverse=True)
        
        return {
            "success": True,
            "query": query,
            "fuzzy_matches": similarity_results,
            "method": "fuzzy_string_similarity"
        }
    
    async def _basic_search(self, parameters: dict):
        """Basic fallback search."""
        query = parameters.get("query", "").lower()
        matches = []
        
        for contact in self.contacts:
            if (query in contact["name"].lower() or 
                any(query in email.lower() for email in contact["emails"])):
                matches.append({"contact": contact, "confidence": 0.5, "method": "basic"})
        
        return {"success": True, "matches": matches, "method": "basic_fallback"}
    
    async def start(self):
        await super().start()
        return True
    
    async def stop(self):
        await super().stop()
        return True

async def demo_semantic_matching():
    """Demonstrate semantic contact matching capabilities."""
    print("🧪 Semantic Contact Matching with Confidence Scoring Demo")
    print("=" * 65)
    
    matcher = SemanticContactMatcher()
    await matcher.start()
    
    # Demo scenarios
    demo_queries = [
        "John Smith",           # Exact match
        "john.smith@company",   # Email partial match  
        "Johnny",               # Alias match
        "Sarah J",              # Partial name + alias
        "Lead Designer",        # Title match
        "Engineering",          # Team match
        "Mike",                 # Common nickname
        "555-0456",            # Phone number
        "DevOps",              # Role keyword
        "Jen Chen"             # Partial name match
    ]
    
    print("\n🎯 Testing Semantic Matching Scenarios:")
    print("-" * 45)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n{i}. Query: '{query}'")
        
        try:
            result = await matcher.execute_with_confidence(
                capability="semantic_match",
                parameters={"query": query, "min_confidence": 0.3},
                min_confidence=0.2
            )
            
            if result.result["success"]:
                matches = result.result["matches"]
                print(f"   Found {len(matches)} matches (confidence ≥ 0.3)")
                
                for j, match in enumerate(matches[:2]):  # Show top 2
                    contact = match["contact"]
                    confidence = match["confidence"]
                    reasons = match["match_reasons"]
                    
                    print(f"   {j+1}. {contact['name']} - Confidence: {confidence:.2f}")
                    print(f"      Reasons: {', '.join(reasons[:2])}")  # Show top 2 reasons
                    
                    # Show confidence breakdown for top match
                    if j == 0:
                        breakdown = match["confidence_breakdown"]
                        top_factors = sorted(
                            [(k, v) for k, v in breakdown.items() if v > 0 and k != "total_confidence"],
                            key=lambda x: x[1], reverse=True
                        )[:3]
                        if top_factors:
                            factors_str = ", ".join([f"{k}: {v:.2f}" for k, v in top_factors])
                            print(f"      Top factors: {factors_str}")
            else:
                print(f"   ❌ Search failed")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Demo confidence tiers
    print(f"\n🎯 Confidence Tier Analysis for 'john':")
    print("-" * 40)
    
    try:
        tier_result = await matcher.execute_capability(
            "confidence_search",
            {"query": "john", "confidence_tiers": [0.9, 0.7, 0.5, 0.3]}
        )
        
        if tier_result["success"]:
            for tier_name, tier_data in tier_result["confidence_tiers"].items():
                min_conf = tier_data["min_confidence"]
                count = tier_data["count"]
                print(f"   Confidence ≥ {min_conf:.1f}: {count} matches")
                
                if count > 0:
                    top_match = tier_data["matches"][0]
                    contact_name = top_match["contact"]["name"]
                    confidence = top_match["confidence"]
                    print(f"      Top: {contact_name} ({confidence:.2f})")
    
    except Exception as e:
        print(f"   ❌ Tier analysis error: {e}")
    
    # Demo fuzzy matching
    print(f"\n🎯 Fuzzy Matching Demo for 'Jon Smth':")
    print("-" * 40)
    
    try:
        fuzzy_result = await matcher.execute_capability(
            "fuzzy_resolution",
            {"query": "Jon Smth"}
        )
        
        if fuzzy_result["success"]:
            fuzzy_matches = fuzzy_result["fuzzy_matches"]
            print(f"   Found {len(fuzzy_matches)} fuzzy matches")
            
            for match in fuzzy_matches[:3]:  # Top 3
                contact = match["contact"]
                similarity = match["overall_similarity"]
                print(f"   • {contact['name']} - Similarity: {similarity:.3f}")
    
    except Exception as e:
        print(f"   ❌ Fuzzy matching error: {e}")
    
    await matcher.stop()
    
    print(f"\n✅ Semantic Contact Matching Demo Completed!")
    print(f"\n🎯 Key Capabilities Demonstrated:")
    print(f"   • Confidence scoring with detailed breakdown")
    print(f"   • Multi-factor matching (name, email, title, team, etc.)")
    print(f"   • Fuzzy string similarity")
    print(f"   • Alias and nickname recognition")
    print(f"   • Confidence threshold filtering")
    print(f"   • Human-readable match reasoning")

async def main():
    """Main demo entry point."""
    try:
        await demo_semantic_matching()
        return True
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)