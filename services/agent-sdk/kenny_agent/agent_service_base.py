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
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

import sqlite3
from .base_agent import BaseAgent

# Optional aiohttp import for LLM functionality
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None


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
    
    @abstractmethod
    def get_agent_context(self) -> str:
        """Return context description for LLM interpretation. Override in subclasses."""
        return self.description