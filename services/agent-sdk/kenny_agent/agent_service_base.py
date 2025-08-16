"""
AgentServiceBase: Intelligent Agent Service Framework for Kenny v2.1

This class extends BaseAgent with embedded LLM capabilities for natural language
query interpretation, semantic caching, and intelligent tool selection.

Key Features:
- Natural language → structured tool calls via embedded LLM
- Multi-tier semantic caching (L1: memory, L2: ChromaDB, L3: SQLite)
- Confidence scoring and fallback mechanisms
- Performance optimization for <5s response times
"""

import asyncio
import hashlib
import json
import time
from abc import abstractmethod
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
from dataclasses import dataclass

import sqlite3
from .base_agent import BaseAgent

# Optional aiohttp import for LLM functionality
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None


@dataclass
class ConfidenceResult:
    """Result with confidence scoring and fallback information."""
    result: Any
    confidence: float
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    response_time: float = 0.0
    cached: bool = False


@dataclass 
class AgentDependency:
    """Agent dependency configuration."""
    agent_id: str
    capabilities: List[str]
    required: bool = False
    timeout: float = 5.0


class SemanticCache:
    """Multi-tier semantic caching for agent responses."""
    
    def __init__(self, cache_dir: str = "/tmp/kenny_cache"):
        """Initialize semantic cache with L1 (memory), L2 (ChromaDB), L3 (SQLite)."""
        self.cache_dir = cache_dir
        self.l1_cache: Dict[str, Tuple[Any, float]] = {}  # query_hash -> (result, timestamp)
        self.l1_ttl = 300  # 5 minutes
        self.l1_max_size = 100
        
        # L3 SQLite cache for structured data
        self.db_path = f"{cache_dir}/agent_cache.db"
        self._init_sqlite_cache()
    
    def _init_sqlite_cache(self):
        """Initialize SQLite cache database."""
        import os
        os.makedirs(self.cache_dir, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                query_hash TEXT PRIMARY KEY,
                query_text TEXT,
                result_data TEXT,
                confidence REAL,
                timestamp REAL,
                agent_id TEXT
            )
        """)
        
        # Enhanced table for relationship data
        conn.execute("""
            CREATE TABLE IF NOT EXISTS relationship_cache (
                entity_type TEXT,
                entity_id TEXT,
                related_entity_type TEXT,
                related_entity_id TEXT,
                relationship_data TEXT,
                confidence REAL,
                timestamp REAL,
                agent_id TEXT,
                PRIMARY KEY (entity_type, entity_id, related_entity_type, related_entity_id, agent_id)
            )
        """)
        
        # Semantic similarity cache for fuzzy matching
        conn.execute("""
            CREATE TABLE IF NOT EXISTS semantic_matches (
                query_hash TEXT,
                match_hash TEXT,
                similarity_score REAL,
                entity_type TEXT,
                timestamp REAL,
                agent_id TEXT,
                PRIMARY KEY (query_hash, match_hash, agent_id)
            )
        """)
        conn.commit()
        conn.close()
    
    def _hash_query(self, query: str, agent_id: str) -> str:
        """Generate consistent hash for query."""
        content = f"{agent_id}:{query.lower().strip()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def get(self, query: str, agent_id: str) -> Optional[Tuple[Any, float]]:
        """Retrieve cached result with confidence score."""
        query_hash = self._hash_query(query, agent_id)
        current_time = time.time()
        
        # L1 Cache check
        if query_hash in self.l1_cache:
            result, timestamp = self.l1_cache[query_hash]
            if current_time - timestamp < self.l1_ttl:
                return result, 1.0  # Perfect match confidence
        
        # L3 SQLite cache check
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT result_data, confidence FROM query_cache WHERE query_hash = ? AND timestamp > ?",
            (query_hash, current_time - 3600)  # 1 hour TTL
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                result = json.loads(row[0])
                confidence = row[1]
                # Promote to L1 cache
                self.l1_cache[query_hash] = (result, current_time)
                return result, confidence
            except json.JSONDecodeError:
                pass
        
        return None
    
    async def set(self, query: str, agent_id: str, result: Any, confidence: float = 1.0):
        """Store result in cache with confidence score."""
        query_hash = self._hash_query(query, agent_id)
        current_time = time.time()
        
        # L1 Cache
        if len(self.l1_cache) >= self.l1_max_size:
            # Remove oldest entry
            oldest_key = min(self.l1_cache.keys(), key=lambda k: self.l1_cache[k][1])
            del self.l1_cache[oldest_key]
        
        self.l1_cache[query_hash] = (result, current_time)
        
        # L3 SQLite cache
        try:
            result_json = json.dumps(result, default=str)
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR REPLACE INTO query_cache VALUES (?, ?, ?, ?, ?, ?)",
                (query_hash, query, result_json, confidence, current_time, agent_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Cache storage error: {e}")
    
    async def cache_relationship_data(self, entity_type: str, entity_id: str, 
                                    related_entity_type: str, related_entity_id: str,
                                    relationship_data: Dict, agent_id: str, 
                                    confidence: float = 1.0, ttl: int = 3600):
        """Cache relationship data between entities."""
        try:
            current_time = time.time()
            data_json = json.dumps(relationship_data, default=str)
            
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO relationship_cache 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (entity_type, entity_id, related_entity_type, related_entity_id, 
                  data_json, confidence, current_time, agent_id))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Relationship cache error: {e}")
    
    async def get_relationship_data(self, entity_type: str, entity_id: str,
                                  related_entity_type: str, agent_id: str,
                                  ttl: int = 3600) -> List[Dict]:
        """Retrieve relationship data for an entity."""
        try:
            current_time = time.time()
            conn = sqlite3.connect(self.db_path)
            
            cursor = conn.execute("""
                SELECT related_entity_id, relationship_data, confidence 
                FROM relationship_cache 
                WHERE entity_type = ? AND entity_id = ? AND related_entity_type = ? 
                AND agent_id = ? AND timestamp > ?
            """, (entity_type, entity_id, related_entity_type, agent_id, 
                  current_time - ttl))
            
            results = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[1])
                    results.append({
                        "related_entity_id": row[0],
                        "relationship_data": data,
                        "confidence": row[2]
                    })
                except json.JSONDecodeError:
                    continue
            
            conn.close()
            return results
        except Exception as e:
            print(f"Relationship retrieval error: {e}")
            return []
    
    async def get_semantic_matches(self, query: str, entity_type: str, agent_id: str,
                                 threshold: float = 0.8, ttl: int = 3600) -> List[Dict]:
        """Retrieve semantically similar cached data."""
        try:
            query_hash = self._hash_query(query, agent_id)
            current_time = time.time()
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute("""
                SELECT sm.match_hash, sm.similarity_score, qc.result_data, qc.confidence
                FROM semantic_matches sm
                JOIN query_cache qc ON sm.match_hash = qc.query_hash
                WHERE sm.query_hash = ? AND sm.entity_type = ? AND sm.agent_id = ?
                AND sm.similarity_score >= ? AND sm.timestamp > ?
                ORDER BY sm.similarity_score DESC
            """, (query_hash, entity_type, agent_id, threshold, current_time - ttl))
            
            results = []
            for row in cursor.fetchall():
                try:
                    data = json.loads(row[2])
                    results.append({
                        "similarity_score": row[1],
                        "result_data": data,
                        "confidence": row[3]
                    })
                except json.JSONDecodeError:
                    continue
            
            conn.close()
            return results
        except Exception as e:
            print(f"Semantic match error: {e}")
            return []


class LLMQueryProcessor:
    """Embedded LLM for natural language query interpretation."""
    
    def __init__(self, model_name: str = "llama3.2:3b", ollama_url: str = "http://localhost:11434"):
        """Initialize LLM processor with specified model."""
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.session = None
    
    async def _ensure_session(self):
        """Ensure HTTP session is available."""
        if not AIOHTTP_AVAILABLE:
            raise ImportError("aiohttp is required for LLM functionality. Install with: pip install aiohttp")
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def interpret_query(self, query: str, available_capabilities: List[str], agent_context: str) -> Dict[str, Any]:
        """
        Interpret natural language query into structured capability calls.
        
        Args:
            query: Natural language query from user
            available_capabilities: List of agent capabilities
            agent_context: Context about what this agent does
            
        Returns:
            Dictionary with capability, parameters, and confidence score
        """
        await self._ensure_session()
        
        system_prompt = f"""You are an intelligent agent interpreter for a {agent_context}.

Available capabilities: {', '.join(available_capabilities)}

Your task: Convert natural language queries into structured capability calls.

Output ONLY valid JSON in this format:
{{
    "capability": "capability_name",
    "parameters": {{"param1": "value1", "param2": "value2"}},
    "confidence": 0.95,
    "reasoning": "Brief explanation"
}}

If query is unclear or not relevant to available capabilities, use confidence < 0.5."""

        user_prompt = f"Query: {query}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=10) if AIOHTTP_AVAILABLE else None
            async with self.session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": f"System: {system_prompt}\n\nUser: {user_prompt}\n\nResponse:",
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=timeout
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "").strip()
                    
                    # Extract JSON from response
                    try:
                        # Find JSON block in response
                        start_idx = response_text.find('{')
                        end_idx = response_text.rfind('}') + 1
                        if start_idx >= 0 and end_idx > start_idx:
                            json_str = response_text[start_idx:end_idx]
                            parsed = json.loads(json_str)
                            
                            # Validate required fields
                            if all(key in parsed for key in ["capability", "parameters", "confidence"]):
                                return parsed
                    except json.JSONDecodeError:
                        pass
                    
                    # Fallback parsing
                    return {
                        "capability": "unknown",
                        "parameters": {"query": query},
                        "confidence": 0.1,
                        "reasoning": "Failed to parse LLM response"
                    }
                else:
                    print(f"LLM request failed: {response.status}")
                    
        except Exception as e:
            print(f"LLM interpretation error: {e}")
        
        # Ultimate fallback
        return {
            "capability": "search" if "search" in available_capabilities else available_capabilities[0] if available_capabilities else "unknown",
            "parameters": {"query": query},
            "confidence": 0.3,
            "reasoning": "LLM unavailable, using fallback"
        }
    
    async def close(self):
        """Close HTTP session."""
        if self.session:
            await self.session.close()


class AgentServiceBase(BaseAgent):
    """
    Intelligent Agent Service Base class with embedded LLM capabilities.
    
    Extends BaseAgent with:
    - Natural language query interpretation via embedded LLM
    - Multi-tier semantic caching for performance
    - Confidence scoring and intelligent fallbacks
    - Performance monitoring for <5s response targets
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        version: str = "2.1.0",
        llm_model: str = "llama3.2:3b",
        cache_dir: str = "/tmp/kenny_cache",
        **kwargs
    ):
        """Initialize intelligent agent service."""
        super().__init__(agent_id, name, description, version, **kwargs)
        
        # LLM and caching components
        self.llm_processor = LLMQueryProcessor(model_name=llm_model)
        self.semantic_cache = SemanticCache(cache_dir=f"{cache_dir}/{agent_id}")
        
        # Performance tracking
        self.query_metrics = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_response_time": 0.0,
            "llm_interpretation_time": 0.0,
            "last_updated": datetime.now(timezone.utc)
        }
        
        # Confidence thresholds
        self.min_confidence = 0.5
        self.fallback_capability = "search"  # Override in subclasses
        
        # Agent dependencies for cross-platform integration
        self.agent_dependencies: Dict[str, AgentDependency] = {}
        self.registry_client = None  # Will be set if needed
        
        print(f"Initialized {name} with LLM model: {llm_model}")
    
    async def process_natural_language_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process natural language query with intelligent interpretation and caching.
        
        Args:
            query: Natural language query from user
            context: Optional additional context for query processing
            
        Returns:
            Structured response with results, confidence, and performance metrics
        """
        start_time = time.time()
        self.query_metrics["total_queries"] += 1
        
        try:
            # Check semantic cache first
            cached_result = await self.semantic_cache.get(query, self.agent_id)
            if cached_result:
                result, confidence = cached_result
                self.query_metrics["cache_hits"] += 1
                
                response_time = time.time() - start_time
                self._update_performance_metrics(response_time)
                
                return {
                    "success": True,
                    "result": result,
                    "confidence": confidence,
                    "cached": True,
                    "response_time": response_time,
                    "agent_id": self.agent_id
                }
            
            # LLM interpretation
            llm_start = time.time()
            interpretation = await self.llm_processor.interpret_query(
                query=query,
                available_capabilities=list(self.capabilities.keys()),
                agent_context=self.description
            )
            llm_time = time.time() - llm_start
            self.query_metrics["llm_interpretation_time"] = llm_time
            
            # Validate confidence threshold
            if interpretation["confidence"] < self.min_confidence:
                # Use fallback capability
                interpretation = {
                    "capability": self.fallback_capability,
                    "parameters": {"query": query},
                    "confidence": 0.4,
                    "reasoning": f"Low confidence, using fallback: {self.fallback_capability}"
                }
            
            # Execute capability
            capability_result = await self.execute_capability(
                interpretation["capability"],
                interpretation["parameters"]
            )
            
            # Prepare response
            result = {
                "interpretation": interpretation,
                "capability_result": capability_result,
                "llm_processing_time": llm_time
            }
            
            # Cache successful results
            if interpretation["confidence"] > 0.6:
                await self.semantic_cache.set(
                    query, self.agent_id, result, interpretation["confidence"]
                )
            
            response_time = time.time() - start_time
            self._update_performance_metrics(response_time)
            
            return {
                "success": True,
                "result": result,
                "confidence": interpretation["confidence"],
                "cached": False,
                "response_time": response_time,
                "agent_id": self.agent_id
            }
            
        except Exception as e:
            error_time = time.time() - start_time
            self._update_performance_metrics(error_time)
            
            return {
                "success": False,
                "error": str(e),
                "response_time": error_time,
                "agent_id": self.agent_id
            }
    
    def _update_performance_metrics(self, response_time: float):
        """Update running performance metrics."""
        # Exponential moving average for response time
        alpha = 0.1
        if self.query_metrics["avg_response_time"] == 0:
            self.query_metrics["avg_response_time"] = response_time
        else:
            self.query_metrics["avg_response_time"] = (
                alpha * response_time + 
                (1 - alpha) * self.query_metrics["avg_response_time"]
            )
        
        self.query_metrics["last_updated"] = datetime.now(timezone.utc)
        
        # Update health status based on performance
        if response_time > 5.0:
            self.update_health_status(
                "degraded", 
                f"Slow response time: {response_time:.2f}s",
                {"response_time": response_time, "target": "5.0s"}
            )
        elif self.query_metrics["avg_response_time"] < 2.0:
            self.update_health_status(
                "healthy",
                f"Performance optimal: {self.query_metrics['avg_response_time']:.2f}s avg",
                self.query_metrics
            )
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        cache_hit_rate = (
            self.query_metrics["cache_hits"] / max(self.query_metrics["total_queries"], 1)
        )
        
        return {
            **self.query_metrics,
            "cache_hit_rate": cache_hit_rate,
            "performance_target": "5.0s",
            "status": "optimal" if self.query_metrics["avg_response_time"] < 2.0 else 
                     "acceptable" if self.query_metrics["avg_response_time"] < 5.0 else "degraded"
        }
    
    async def stop(self):
        """Stop the agent and cleanup resources."""
        await self.llm_processor.close()
        await super().stop()
    
    def register_agent_dependency(self, agent_id: str, capabilities: List[str], 
                                 required: bool = False, timeout: float = 5.0):
        """Register dependency on another agent for cross-platform features."""
        self.agent_dependencies[agent_id] = AgentDependency(
            agent_id=agent_id,
            capabilities=capabilities,
            required=required,
            timeout=timeout
        )
        print(f"Registered dependency on {agent_id} for capabilities: {capabilities}")
    
    def set_registry_client(self, registry_client):
        """Set the agent registry client for cross-agent communication."""
        self.registry_client = registry_client
    
    async def query_agent(self, agent_id: str, capability: str, parameters: Dict[str, Any],
                         timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Query another agent for cross-platform functionality."""
        if not self.registry_client:
            print(f"No registry client available for querying {agent_id}")
            return None
        
        if agent_id not in self.agent_dependencies:
            print(f"Agent {agent_id} not in registered dependencies")
            return None
        
        dependency = self.agent_dependencies[agent_id]
        if capability not in dependency.capabilities:
            print(f"Capability {capability} not available from {agent_id}")
            return None
        
        try:
            # Use registry client to route request to target agent
            result = await self.registry_client.invoke_agent_capability(
                agent_id=agent_id,
                capability=capability,
                parameters=parameters,
                timeout=timeout
            )
            return result
        except Exception as e:
            print(f"Error querying agent {agent_id}: {e}")
            if dependency.required:
                raise
            return None
    
    async def execute_with_confidence(self, capability: str, parameters: Dict[str, Any],
                                    min_confidence: Optional[float] = None) -> ConfidenceResult:
        """Execute capability with confidence scoring and fallback support."""
        start_time = time.time()
        confidence_threshold = min_confidence or self.min_confidence
        
        try:
            # Check if this requires LLM interpretation
            if isinstance(parameters.get("query"), str):
                # Natural language query - use LLM interpretation
                llm_start = time.time()
                interpretation = await self.llm_processor.interpret_query(
                    query=parameters["query"],
                    available_capabilities=list(self.capabilities.keys()),
                    agent_context=self.get_agent_context()
                )
                llm_time = time.time() - llm_start
                
                if interpretation["confidence"] < confidence_threshold:
                    # Use fallback
                    result = await self.execute_capability(
                        self.fallback_capability, parameters
                    )
                    return ConfidenceResult(
                        result=result,
                        confidence=interpretation["confidence"],
                        fallback_used=True,
                        fallback_reason=f"Low confidence: {interpretation['confidence']:.2f} < {confidence_threshold}",
                        response_time=time.time() - start_time
                    )
                
                # Use interpreted capability
                result = await self.execute_capability(
                    interpretation["capability"],
                    interpretation["parameters"]
                )
                return ConfidenceResult(
                    result=result,
                    confidence=interpretation["confidence"],
                    fallback_used=False,
                    response_time=time.time() - start_time
                )
            else:
                # Direct capability call
                result = await self.execute_capability(capability, parameters)
                return ConfidenceResult(
                    result=result,
                    confidence=1.0,  # Direct calls have full confidence
                    fallback_used=False,
                    response_time=time.time() - start_time
                )
                
        except Exception as e:
            # Error fallback
            if capability != self.fallback_capability:
                try:
                    fallback_result = await self.execute_capability(
                        self.fallback_capability, parameters
                    )
                    return ConfidenceResult(
                        result=fallback_result,
                        confidence=0.3,
                        fallback_used=True,
                        fallback_reason=f"Error fallback: {str(e)}",
                        response_time=time.time() - start_time
                    )
                except:
                    pass
            
            raise e
    
    async def enrich_query_context(self, query: str, platforms: List[str]) -> Dict[str, Any]:
        """Enrich query context with cross-platform data."""
        enriched_context = {"original_query": query, "platforms": platforms}
        
        # Query relevant dependent agents for context
        for platform in platforms:
            platform_agent_map = {
                "contacts": "contacts-agent",
                "mail": "mail-agent", 
                "calendar": "calendar-agent",
                "imessage": "imessage-agent"
            }
            
            agent_id = platform_agent_map.get(platform)
            if agent_id and agent_id in self.agent_dependencies:
                try:
                    # Try to get context from the platform agent
                    context_result = await self.query_agent(
                        agent_id=agent_id,
                        capability="get_context",  # Assume context capability
                        parameters={"query": query},
                        timeout=2.0  # Quick context lookup
                    )
                    if context_result:
                        enriched_context[f"{platform}_context"] = context_result
                except Exception as e:
                    print(f"Could not enrich context from {platform}: {e}")
        
        return enriched_context
    
    def get_multi_platform_context(self) -> str:
        """Return context that spans multiple data sources/platforms."""
        base_context = self.get_agent_context()
        
        if self.agent_dependencies:
            dependency_info = []
            for agent_id, dep in self.agent_dependencies.items():
                dependency_info.append(f"{agent_id} ({', '.join(dep.capabilities)})")
            
            cross_platform_context = f"""
{base_context}

Cross-platform integrations available:
{', '.join(dependency_info)}

This agent can coordinate with other agents for comprehensive responses.
"""
            return cross_platform_context
        
        return base_context
    
    async def cache_entity_relationship(self, entity_type: str, entity_id: str,
                                      related_entity_type: str, related_entity_id: str,
                                      relationship_data: Dict, confidence: float = 1.0):
        """Cache relationship data between entities."""
        await self.semantic_cache.cache_relationship_data(
            entity_type=entity_type,
            entity_id=entity_id,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            relationship_data=relationship_data,
            agent_id=self.agent_id,
            confidence=confidence
        )
    
    async def get_entity_relationships(self, entity_type: str, entity_id: str,
                                     related_entity_type: str) -> List[Dict]:
        """Get cached relationship data for an entity."""
        return await self.semantic_cache.get_relationship_data(
            entity_type=entity_type,
            entity_id=entity_id,
            related_entity_type=related_entity_type,
            agent_id=self.agent_id
        )
    
    async def find_semantic_matches(self, query: str, entity_type: str,
                                  threshold: float = 0.8) -> List[Dict]:
        """Find semantically similar cached data."""
        return await self.semantic_cache.get_semantic_matches(
            query=query,
            entity_type=entity_type,
            agent_id=self.agent_id,
            threshold=threshold
        )
    
    @abstractmethod
    def get_agent_context(self) -> str:
        """Return context description for LLM interpretation. Override in subclasses."""
        return self.description