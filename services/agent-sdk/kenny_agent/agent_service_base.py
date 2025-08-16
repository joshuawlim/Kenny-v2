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

# Optional Redis import for enhanced L2 caching
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


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
    """Enhanced multi-tier semantic caching for agent responses with Redis L2 layer."""
    
    def __init__(self, cache_dir: str = "/tmp/kenny_cache", redis_url: str = "redis://localhost:6379"):
        """Initialize enhanced semantic cache with L1 (memory), L2 (Redis), L3 (SQLite)."""
        self.cache_dir = cache_dir
        self.redis_url = redis_url
        
        # Enhanced L1 cache: query_hash -> (result, timestamp, access_count, last_access)
        self.l1_cache: Dict[str, Tuple[Any, float, int, float]] = {}
        self.l1_ttl = 30  # Reduced to 30 seconds for aggressive freshness
        self.l1_max_size = 1000  # Increased to 1000 entries for better performance
        self.l1_access_weight = 0.3  # Weight for frequency in LFU-LRU hybrid
        
        # L2 Redis cache connection
        self.redis_client = None
        self.l2_ttl = 300  # 5 minutes for Redis cache
        self.redis_connection_pool = None
        
        # L3 SQLite cache for structured data
        self.db_path = f"{cache_dir}/agent_cache.db"
        self._init_sqlite_cache()
        
        # Cache performance metrics
        self.cache_metrics = {
            "l1_hits": 0,
            "l2_hits": 0, 
            "l3_hits": 0,
            "cache_misses": 0,
            "total_queries": 0,
            "l2_connection_errors": 0
        }
    
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
    
    async def _init_redis_connection(self):
        """Initialize Redis connection with connection pooling."""
        if not REDIS_AVAILABLE:
            print("Warning: Redis not available, L2 cache disabled")
            return
        
        try:
            # Create connection pool for better performance
            self.redis_connection_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                decode_responses=True
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_connection_pool)
            
            # Test connection
            await self.redis_client.ping()
            print(f"Redis L2 cache connected: {self.redis_url}")
            
        except Exception as e:
            print(f"Warning: Redis L2 cache unavailable: {e}")
            self.redis_client = None
            self.cache_metrics["l2_connection_errors"] += 1
    
    async def _ensure_redis_connection(self):
        """Ensure Redis connection is available."""
        if REDIS_AVAILABLE and self.redis_client is None:
            await self._init_redis_connection()
    
    def _hash_query(self, query: str, agent_id: str) -> str:
        """Generate consistent hash for query."""
        content = f"{agent_id}:{query.lower().strip()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def get(self, query: str, agent_id: str) -> Optional[Tuple[Any, float]]:
        """Retrieve cached result with confidence score using L1 -> L2 -> L3 hierarchy."""
        query_hash = self._hash_query(query, agent_id)
        current_time = time.time()
        self.cache_metrics["total_queries"] += 1
        
        # L1 Cache check with access tracking (30-second TTL)
        if query_hash in self.l1_cache:
            result, timestamp, access_count, last_access = self.l1_cache[query_hash]
            if current_time - timestamp < self.l1_ttl:
                # Update access statistics for LFU-LRU hybrid
                self.l1_cache[query_hash] = (result, timestamp, access_count + 1, current_time)
                self.cache_metrics["l1_hits"] += 1
                return result, 1.0  # Perfect match confidence
        
        # L2 Redis Cache check (5-minute TTL)
        await self._ensure_redis_connection()
        if self.redis_client:
            try:
                redis_key = f"kenny:cache:{agent_id}:{query_hash}"
                cached_data = await self.redis_client.get(redis_key)
                if cached_data:
                    cache_entry = json.loads(cached_data)
                    result = cache_entry["result"]
                    confidence = cache_entry["confidence"]
                    
                    # Promote to L1 cache
                    self.l1_cache[query_hash] = (result, current_time, 1, current_time)
                    self.cache_metrics["l2_hits"] += 1
                    return result, confidence
            except Exception as e:
                print(f"Redis L2 cache error: {e}")
                self.cache_metrics["l2_connection_errors"] += 1
        
        # L3 SQLite cache check (1-hour TTL)
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
                
                # Promote to L2 and L1 caches
                await self._promote_to_upper_caches(query_hash, agent_id, result, confidence, current_time)
                self.cache_metrics["l3_hits"] += 1
                return result, confidence
            except json.JSONDecodeError:
                pass
        
        self.cache_metrics["cache_misses"] += 1
        return None
    
    async def _promote_to_upper_caches(self, query_hash: str, agent_id: str, result: Any, confidence: float, current_time: float):
        """Promote cache entry to L2 and L1 caches."""
        # Promote to L1 cache
        self.l1_cache[query_hash] = (result, current_time, 1, current_time)
        
        # Promote to L2 Redis cache
        await self._ensure_redis_connection()
        if self.redis_client:
            try:
                redis_key = f"kenny:cache:{agent_id}:{query_hash}"
                cache_data = {
                    "result": result,
                    "confidence": confidence,
                    "timestamp": current_time,
                    "agent_id": agent_id
                }
                await self.redis_client.setex(
                    redis_key,
                    self.l2_ttl,
                    json.dumps(cache_data, default=str)
                )
            except Exception as e:
                print(f"Error promoting to Redis L2 cache: {e}")
                self.cache_metrics["l2_connection_errors"] += 1
    
    async def set(self, query: str, agent_id: str, result: Any, confidence: float = 1.0):
        """Store result in all cache layers (L1, L2, L3) with enhanced performance."""
        query_hash = self._hash_query(query, agent_id)
        current_time = time.time()
        
        # Enhanced L1 Cache with LFU-LRU hybrid eviction
        if len(self.l1_cache) >= self.l1_max_size:
            # Enhanced eviction: combine frequency and recency with configurable weight
            # Score = (1 - access_weight) * recency + access_weight * frequency
            def eviction_score(key):
                _, timestamp, access_count, last_access = self.l1_cache[key]
                recency_score = (current_time - last_access) / (current_time - timestamp + 1)
                frequency_score = 1.0 / (access_count + 1)
                return (1 - self.l1_access_weight) * recency_score + self.l1_access_weight * frequency_score
            
            # Remove entry with lowest score (least valuable)
            worst_key = min(self.l1_cache.keys(), key=eviction_score)
            del self.l1_cache[worst_key]
        
        # Store with enhanced metadata: (result, creation_time, access_count, last_access)
        self.l1_cache[query_hash] = (result, current_time, 1, current_time)
        
        # L2 Redis Cache
        await self._ensure_redis_connection()
        if self.redis_client:
            try:
                redis_key = f"kenny:cache:{agent_id}:{query_hash}"
                cache_data = {
                    "result": result,
                    "confidence": confidence,
                    "timestamp": current_time,
                    "agent_id": agent_id
                }
                await self.redis_client.setex(
                    redis_key,
                    self.l2_ttl,
                    json.dumps(cache_data, default=str)
                )
            except Exception as e:
                print(f"Redis L2 cache storage error: {e}")
                self.cache_metrics["l2_connection_errors"] += 1
        
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
            print(f"SQLite L3 cache storage error: {e}")
    
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
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics for all tiers."""
        current_time = time.time()
        
        # Calculate L1 cache statistics
        l1_size = len(self.l1_cache)
        l1_total_access_count = sum(entry[2] for entry in self.l1_cache.values())  # access_count
        l1_avg_access_count = l1_total_access_count / max(l1_size, 1)
        
        # Calculate age distribution
        ages = [(current_time - entry[1]) for entry in self.l1_cache.values()]  # current_time - timestamp
        l1_avg_age = sum(ages) / max(len(ages), 1)
        l1_oldest_entry = max(ages) if ages else 0
        
        # Calculate memory usage (rough estimate)
        l1_memory_usage_mb = l1_size * 0.01  # Rough estimate: 10KB per entry
        
        # Calculate hit rates
        total_queries = max(self.cache_metrics["total_queries"], 1)
        l1_hit_rate = (self.cache_metrics["l1_hits"] / total_queries) * 100
        l2_hit_rate = (self.cache_metrics["l2_hits"] / total_queries) * 100
        l3_hit_rate = (self.cache_metrics["l3_hits"] / total_queries) * 100
        cache_miss_rate = (self.cache_metrics["cache_misses"] / total_queries) * 100
        
        return {
            "l1_cache": {
                "size": l1_size,
                "max_size": self.l1_max_size,
                "utilization_percent": round((l1_size / self.l1_max_size) * 100, 2),
                "hit_rate_percent": round(l1_hit_rate, 2),
                "avg_access_count": round(l1_avg_access_count, 2),
                "avg_age_seconds": round(l1_avg_age, 2),
                "oldest_entry_seconds": round(l1_oldest_entry, 2),
                "ttl_seconds": self.l1_ttl,
                "estimated_memory_mb": round(l1_memory_usage_mb, 2)
            },
            "l2_cache": {
                "enabled": REDIS_AVAILABLE and self.redis_client is not None,
                "hit_rate_percent": round(l2_hit_rate, 2),
                "ttl_seconds": self.l2_ttl,
                "connection_errors": self.cache_metrics["l2_connection_errors"],
                "redis_url": self.redis_url if REDIS_AVAILABLE else "unavailable"
            },
            "l3_cache": {
                "hit_rate_percent": round(l3_hit_rate, 2),
                "ttl_seconds": 3600,  # 1 hour
                "database_path": self.db_path
            },
            "overall_performance": {
                "total_queries": self.cache_metrics["total_queries"],
                "cache_miss_rate_percent": round(cache_miss_rate, 2),
                "total_hit_rate_percent": round(100 - cache_miss_rate, 2),
                "eviction_policy": "Enhanced LFU-LRU Hybrid",
                "access_weight": self.l1_access_weight,
                "multi_tier_caching": "L1 (memory) -> L2 (Redis) -> L3 (SQLite)"
            }
        }
    
    def get_cache_hit_rate(self, total_queries: int, cache_hits: int) -> float:
        """Calculate cache hit rate percentage."""
        return (cache_hits / max(total_queries, 1)) * 100
    
    async def close(self):
        """Close Redis connections and cleanup resources."""
        if self.redis_client:
            try:
                await self.redis_client.close()
                print("Redis L2 cache connection closed")
            except Exception as e:
                print(f"Error closing Redis connection: {e}")
        
        if self.redis_connection_pool:
            try:
                await self.redis_connection_pool.disconnect()
            except Exception as e:
                print(f"Error closing Redis connection pool: {e}")
    
    async def warm_cache_for_patterns(self, common_queries: List[str], agent_id: str):
        """Warm cache with common query patterns for better performance."""
        for query in common_queries:
            try:
                # This would typically call the actual agent capability to warm the cache
                print(f"Would warm cache for pattern: {query}")
            except Exception as e:
                print(f"Error warming cache for query '{query}': {e}")
    
    async def invalidate_cache_pattern(self, pattern: str, agent_id: str):
        """Invalidate cache entries matching a pattern."""
        # Invalidate L1 cache
        to_remove = []
        for key in self.l1_cache.keys():
            if pattern in key:
                to_remove.append(key)
        
        for key in to_remove:
            del self.l1_cache[key]
        
        # Invalidate L2 Redis cache
        await self._ensure_redis_connection()
        if self.redis_client:
            try:
                redis_pattern = f"kenny:cache:{agent_id}:*{pattern}*"
                keys = await self.redis_client.keys(redis_pattern)
                if keys:
                    await self.redis_client.delete(*keys)
                    print(f"Invalidated {len(keys)} Redis cache entries for pattern: {pattern}")
            except Exception as e:
                print(f"Error invalidating Redis cache for pattern '{pattern}': {e}")
        
        print(f"Invalidated cache entries for pattern: {pattern}")


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
        """Get current performance metrics with enhanced cache statistics."""
        cache_hit_rate = (
            self.query_metrics["cache_hits"] / max(self.query_metrics["total_queries"], 1)
        )
        
        # Get detailed cache statistics
        cache_stats = self.semantic_cache.get_cache_stats()
        
        # Calculate performance improvement from caching
        cache_hit_rate_percent = cache_hit_rate * 100
        estimated_performance_improvement = min(cache_hit_rate_percent * 0.8, 80)  # Max 80% improvement
        
        return {
            **self.query_metrics,
            "cache_hit_rate": cache_hit_rate,
            "cache_hit_rate_percent": round(cache_hit_rate_percent, 1),
            "estimated_performance_improvement_percent": round(estimated_performance_improvement, 1),
            "cache_statistics": cache_stats,
            "performance_target": "5.0s",
            "status": "optimal" if self.query_metrics["avg_response_time"] < 2.0 else 
                     "acceptable" if self.query_metrics["avg_response_time"] < 5.0 else "degraded",
            "cache_enabled": True,
            "cache_policy": "Enhanced L1 LFU-LRU Hybrid"
        }
    
    async def stop(self):
        """Stop the agent and cleanup resources."""
        # Cleanup semantic cache Redis connections
        if hasattr(self, 'semantic_cache') and self.semantic_cache:
            await self.semantic_cache.close()
        
        # Cleanup LLM processor
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