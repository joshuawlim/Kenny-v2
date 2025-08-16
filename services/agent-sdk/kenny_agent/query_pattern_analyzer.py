"""
Query Pattern Analysis Engine for Kenny v2.1 Phase 3.2.3

ML-based query pattern recognition and prediction for intelligent cache warming.
Analyzes historical query patterns, user behavior, and temporal patterns to 
predict likely future queries for proactive cache warming.

Key Features:
- Historical query pattern analysis
- Temporal pattern recognition (morning vs evening queries)
- User behavior learning and adaptation
- Probability scoring for predictive cache warming
- Adaptive learning from cache hit/miss patterns
"""

import json
import sqlite3
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict, Counter
import logging
import re
import hashlib


@dataclass
class PredictedQuery:
    """Represents a predicted query with probability and timing."""
    query: str
    probability: float
    predicted_time: datetime
    confidence: float
    reasoning: str
    query_type: str  # e.g., "time_based", "contact_based", "recurring"
    temporal_pattern: Optional[str] = None  # e.g., "morning_check", "weekly_planning"


@dataclass
class QueryPattern:
    """Represents an analyzed query pattern."""
    pattern_id: str
    query_template: str
    frequency: int
    temporal_distribution: Dict[int, float]  # hour -> frequency
    weekday_distribution: Dict[int, float]  # weekday -> frequency
    success_rate: float
    cache_effectiveness: float
    last_seen: datetime
    variations: List[str]


@dataclass
class CacheAction:
    """Represents a recommended cache action."""
    action_type: str  # "warm", "invalidate", "refresh"
    query: str
    priority: float
    reasoning: str
    estimated_benefit: float


class QueryPatternAnalyzer:
    """
    ML-based query pattern analyzer for predictive cache warming.
    
    Analyzes historical queries to identify patterns and predict likely future queries
    for proactive cache warming optimization.
    """
    
    def __init__(self, agent_id: str, cache_dir: str = "/tmp/kenny_cache"):
        """Initialize the query pattern analyzer."""
        self.agent_id = agent_id
        self.cache_dir = cache_dir
        self.db_path = f"{cache_dir}/query_patterns_{agent_id}.db"
        self.logger = logging.getLogger(f"query-pattern-analyzer-{agent_id}")
        
        # Pattern analysis configuration
        self.min_pattern_frequency = 3  # Minimum occurrences to consider a pattern
        self.temporal_window_hours = 24  # Hours to consider for temporal patterns
        self.learning_rate = 0.1  # Weight for updating pattern probabilities
        self.prediction_confidence_threshold = 0.6  # Minimum confidence for predictions
        
        # Pattern storage
        self.patterns: Dict[str, QueryPattern] = {}
        self.temporal_patterns: Dict[str, Dict] = {}
        self.user_behavior_profile: Dict[str, Any] = {}
        
        # Performance tracking
        self.prediction_accuracy: Dict[str, float] = {
            "total_predictions": 0,
            "correct_predictions": 0,
            "accuracy_rate": 0.0
        }
        
        self._init_database()
        self._load_patterns()
    
    def _init_database(self):
        """Initialize SQLite database for pattern storage."""
        import os
        os.makedirs(self.cache_dir, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        
        # Query history table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_hash TEXT,
                query_text TEXT,
                timestamp REAL,
                hour INTEGER,
                weekday INTEGER,
                success BOOLEAN,
                cache_hit BOOLEAN,
                response_time REAL,
                confidence REAL,
                agent_id TEXT
            )
        """)
        
        # Pattern analysis table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_patterns (
                pattern_id TEXT PRIMARY KEY,
                query_template TEXT,
                frequency INTEGER,
                temporal_distribution TEXT,
                weekday_distribution TEXT,
                success_rate REAL,
                cache_effectiveness REAL,
                last_seen REAL,
                variations TEXT,
                agent_id TEXT
            )
        """)
        
        # Prediction accuracy tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_accuracy (
                prediction_id TEXT PRIMARY KEY,
                predicted_query TEXT,
                prediction_time REAL,
                actual_time REAL,
                accuracy_score REAL,
                agent_id TEXT
            )
        """)
        
        # User behavior profile
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_behavior (
                profile_key TEXT PRIMARY KEY,
                profile_data TEXT,
                last_updated REAL,
                agent_id TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def _load_patterns(self):
        """Load existing patterns from database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.execute(
                "SELECT * FROM query_patterns WHERE agent_id = ?",
                (self.agent_id,)
            )
            
            for row in cursor.fetchall():
                pattern_id, query_template, frequency, temporal_dist, weekday_dist, \
                success_rate, cache_effectiveness, last_seen, variations, _ = row
                
                try:
                    temporal_distribution = json.loads(temporal_dist)
                    weekday_distribution = json.loads(weekday_dist)
                    variation_list = json.loads(variations)
                    
                    pattern = QueryPattern(
                        pattern_id=pattern_id,
                        query_template=query_template,
                        frequency=frequency,
                        temporal_distribution=temporal_distribution,
                        weekday_distribution=weekday_distribution,
                        success_rate=success_rate,
                        cache_effectiveness=cache_effectiveness,
                        last_seen=datetime.fromtimestamp(last_seen),
                        variations=variation_list
                    )
                    
                    self.patterns[pattern_id] = pattern
                    
                except json.JSONDecodeError:
                    self.logger.error(f"Error loading pattern {pattern_id}")
            
            conn.close()
            self.logger.info(f"Loaded {len(self.patterns)} query patterns from database")
            
        except Exception as e:
            self.logger.error(f"Error loading patterns: {e}")
    
    async def record_query(self, query: str, success: bool, cache_hit: bool, 
                         response_time: float, confidence: float):
        """Record a query for pattern analysis."""
        current_time = time.time()
        dt = datetime.fromtimestamp(current_time)
        query_hash = self._hash_query(query)
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT INTO query_history 
                (query_hash, query_text, timestamp, hour, weekday, success, 
                 cache_hit, response_time, confidence, agent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                query_hash, query, current_time, dt.hour, dt.weekday(),
                success, cache_hit, response_time, confidence, self.agent_id
            ))
            conn.commit()
            conn.close()
            
            # Update patterns asynchronously
            await self._update_patterns(query, dt, success, cache_hit)
            
        except Exception as e:
            self.logger.error(f"Error recording query: {e}")
    
    async def analyze_historical_patterns(self) -> Dict[str, float]:
        """Analyze historical query patterns and return pattern weights."""
        try:
            conn = sqlite3.connect(self.db_path)
            
            # Get query history for the last 30 days
            thirty_days_ago = time.time() - (30 * 24 * 3600)
            cursor = conn.execute("""
                SELECT query_text, hour, weekday, success, cache_hit, COUNT(*) as frequency
                FROM query_history 
                WHERE agent_id = ? AND timestamp > ?
                GROUP BY query_text, hour, weekday
                ORDER BY frequency DESC
            """, (self.agent_id, thirty_days_ago))
            
            pattern_weights = {}
            temporal_analysis = defaultdict(lambda: defaultdict(float))
            
            for row in cursor.fetchall():
                query, hour, weekday, success, cache_hit, frequency = row
                
                # Extract pattern template
                pattern_template = self._extract_pattern_template(query)
                pattern_id = self._generate_pattern_id(pattern_template)
                
                # Calculate weight based on frequency and success
                success_weight = 1.0 if success else 0.5
                cache_weight = 1.2 if cache_hit else 1.0
                base_weight = frequency * success_weight * cache_weight
                
                pattern_weights[pattern_id] = pattern_weights.get(pattern_id, 0) + base_weight
                
                # Track temporal patterns
                temporal_analysis[pattern_id][f"hour_{hour}"] += frequency
                temporal_analysis[pattern_id][f"weekday_{weekday}"] += frequency
            
            conn.close()
            
            # Normalize weights
            if pattern_weights:
                max_weight = max(pattern_weights.values())
                pattern_weights = {
                    k: v / max_weight for k, v in pattern_weights.items()
                }
            
            # Update temporal patterns
            self.temporal_patterns.update(temporal_analysis)
            
            self.logger.info(f"Analyzed {len(pattern_weights)} query patterns")
            return pattern_weights
            
        except Exception as e:
            self.logger.error(f"Error analyzing patterns: {e}")
            return {}
    
    async def predict_likely_queries(self, time_context: datetime) -> List[PredictedQuery]:
        """Predict likely queries based on temporal context and patterns."""
        predicted_queries = []
        
        try:
            # Get current temporal context
            current_hour = time_context.hour
            current_weekday = time_context.weekday()
            
            # Analyze each pattern for prediction potential
            for pattern_id, pattern in self.patterns.items():
                # Calculate temporal probability
                hour_prob = pattern.temporal_distribution.get(current_hour, 0.1)
                weekday_prob = pattern.weekday_distribution.get(current_weekday, 0.1)
                
                # Combined probability with frequency weighting
                base_probability = (hour_prob + weekday_prob) / 2
                frequency_weight = min(pattern.frequency / 10.0, 1.0)  # Cap at 1.0
                success_weight = pattern.success_rate
                cache_weight = pattern.cache_effectiveness
                
                final_probability = (
                    base_probability * frequency_weight * success_weight * cache_weight
                )
                
                # Only predict if probability exceeds threshold
                if final_probability >= self.prediction_confidence_threshold:
                    # Generate specific query from template
                    predicted_query = self._generate_query_from_template(
                        pattern.query_template, time_context
                    )
                    
                    prediction = PredictedQuery(
                        query=predicted_query,
                        probability=final_probability,
                        predicted_time=time_context,
                        confidence=min(final_probability * 1.2, 1.0),
                        reasoning=f"Pattern {pattern_id}: {pattern.frequency} occurrences, "
                                f"{success_weight:.2f} success rate, "
                                f"{cache_weight:.2f} cache effectiveness",
                        query_type=self._classify_query_type(predicted_query),
                        temporal_pattern=self._identify_temporal_pattern(current_hour)
                    )
                    
                    predicted_queries.append(prediction)
            
            # Add time-specific predictions
            time_based_predictions = self._generate_time_based_predictions(time_context)
            predicted_queries.extend(time_based_predictions)
            
            # Sort by probability and return top predictions
            predicted_queries.sort(key=lambda x: x.probability, reverse=True)
            
            self.logger.info(f"Generated {len(predicted_queries)} query predictions")
            return predicted_queries[:20]  # Return top 20 predictions
            
        except Exception as e:
            self.logger.error(f"Error predicting queries: {e}")
            return []
    
    async def update_pattern_weights(self, query: str, success: bool):
        """Update pattern weights based on actual query outcomes."""
        pattern_template = self._extract_pattern_template(query)
        pattern_id = self._generate_pattern_id(pattern_template)
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            
            # Update success rate with exponential moving average
            if success:
                pattern.success_rate = (
                    (1 - self.learning_rate) * pattern.success_rate + 
                    self.learning_rate * 1.0
                )
            else:
                pattern.success_rate = (
                    (1 - self.learning_rate) * pattern.success_rate + 
                    self.learning_rate * 0.0
                )
            
            # Update frequency
            pattern.frequency += 1
            pattern.last_seen = datetime.now()
            
            # Save updated pattern
            await self._save_pattern(pattern)
            
            self.logger.debug(f"Updated pattern {pattern_id}: success_rate={pattern.success_rate:.3f}")
    
    async def get_optimization_recommendations(self) -> List[CacheAction]:
        """Get cache optimization recommendations based on pattern analysis."""
        recommendations = []
        
        try:
            current_time = datetime.now()
            
            # Recommend warming high-probability patterns
            predicted_queries = await self.predict_likely_queries(current_time)
            
            for prediction in predicted_queries[:10]:  # Top 10 predictions
                if prediction.probability > 0.7:
                    action = CacheAction(
                        action_type="warm",
                        query=prediction.query,
                        priority=prediction.probability,
                        reasoning=f"High probability prediction: {prediction.reasoning}",
                        estimated_benefit=prediction.probability * 0.8  # Estimated response time improvement
                    )
                    recommendations.append(action)
            
            # Recommend invalidating stale patterns
            for pattern_id, pattern in self.patterns.items():
                age_hours = (current_time - pattern.last_seen).total_seconds() / 3600
                
                if age_hours > 24 and pattern.cache_effectiveness < 0.5:
                    action = CacheAction(
                        action_type="invalidate",
                        query=pattern.query_template,
                        priority=0.8 - pattern.cache_effectiveness,
                        reasoning=f"Stale pattern with low cache effectiveness: {pattern.cache_effectiveness:.2f}",
                        estimated_benefit=0.3
                    )
                    recommendations.append(action)
            
            # Recommend refreshing time-sensitive patterns
            time_sensitive_keywords = ["today", "tomorrow", "this week", "upcoming"]
            for keyword in time_sensitive_keywords:
                action = CacheAction(
                    action_type="refresh",
                    query=f"events {keyword}",
                    priority=0.9,
                    reasoning=f"Time-sensitive query requires regular refresh",
                    estimated_benefit=0.6
                )
                recommendations.append(action)
            
            # Sort by priority
            recommendations.sort(key=lambda x: x.priority, reverse=True)
            
            self.logger.info(f"Generated {len(recommendations)} optimization recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating recommendations: {e}")
            return []
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query."""
        return hashlib.sha256(query.lower().strip().encode()).hexdigest()[:16]
    
    def _extract_pattern_template(self, query: str) -> str:
        """Extract pattern template from specific query."""
        # Normalize query
        normalized = query.lower().strip()
        
        # Replace specific dates with placeholders
        date_patterns = [
            (r'\b\d{4}-\d{2}-\d{2}\b', '[DATE]'),
            (r'\b\d{1,2}/\d{1,2}/\d{4}\b', '[DATE]'),
            (r'\btoday\b', '[TODAY]'),
            (r'\btomorrow\b', '[TOMORROW]'),
            (r'\bthis week\b', '[THIS_WEEK]'),
            (r'\bnext week\b', '[NEXT_WEEK]'),
            (r'\bthis month\b', '[THIS_MONTH]'),
            (r'\bnext month\b', '[NEXT_MONTH]'),
        ]
        
        for pattern, replacement in date_patterns:
            normalized = re.sub(pattern, replacement, normalized)
        
        # Replace specific names with placeholders (basic implementation)
        # This could be enhanced with NLP entity recognition
        words = normalized.split()
        template_words = []
        
        for word in words:
            if word and word[0].isupper() and len(word) > 1:
                template_words.append('[NAME]')
            else:
                template_words.append(word)
        
        return ' '.join(template_words)
    
    def _generate_pattern_id(self, template: str) -> str:
        """Generate unique pattern ID from template."""
        return hashlib.sha256(template.encode()).hexdigest()[:12]
    
    def _generate_query_from_template(self, template: str, context: datetime) -> str:
        """Generate specific query from template with current context."""
        query = template
        
        # Replace temporal placeholders
        replacements = {
            '[TODAY]': 'today',
            '[TOMORROW]': 'tomorrow',
            '[THIS_WEEK]': 'this week',
            '[NEXT_WEEK]': 'next week',
            '[THIS_MONTH]': 'this month',
            '[NEXT_MONTH]': 'next month',
            '[DATE]': context.strftime('%Y-%m-%d'),
            '[NAME]': 'contacts'  # Generic placeholder
        }
        
        for placeholder, replacement in replacements.items():
            query = query.replace(placeholder, replacement)
        
        return query
    
    def _classify_query_type(self, query: str) -> str:
        """Classify query type for pattern analysis."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['today', 'tomorrow', 'this week']):
            return 'time_based'
        elif any(word in query_lower for word in ['meeting', 'event', 'appointment']):
            return 'event_based'
        elif any(word in query_lower for word in ['with', 'from', 'contact']):
            return 'contact_based'
        else:
            return 'general'
    
    def _identify_temporal_pattern(self, hour: int) -> str:
        """Identify temporal pattern based on hour."""
        if 6 <= hour < 10:
            return 'morning_check'
        elif 10 <= hour < 12:
            return 'mid_morning'
        elif 12 <= hour < 14:
            return 'lunch_time'
        elif 14 <= hour < 17:
            return 'afternoon_work'
        elif 17 <= hour < 19:
            return 'end_of_day'
        elif 19 <= hour < 22:
            return 'evening_planning'
        else:
            return 'off_hours'
    
    def _generate_time_based_predictions(self, context: datetime) -> List[PredictedQuery]:
        """Generate predictions based on time context."""
        predictions = []
        hour = context.hour
        
        # Morning predictions (7-10 AM)
        if 7 <= hour < 10:
            morning_queries = [
                "events today",
                "meetings today", 
                "schedule today",
                "upcoming meetings"
            ]
            for query in morning_queries:
                predictions.append(PredictedQuery(
                    query=query,
                    probability=0.8,
                    predicted_time=context,
                    confidence=0.7,
                    reasoning="Morning schedule check pattern",
                    query_type="time_based",
                    temporal_pattern="morning_check"
                ))
        
        # Afternoon predictions (1-3 PM)
        elif 13 <= hour < 15:
            afternoon_queries = [
                "meetings this afternoon",
                "events today",
                "meetings tomorrow"
            ]
            for query in afternoon_queries:
                predictions.append(PredictedQuery(
                    query=query,
                    probability=0.7,
                    predicted_time=context,
                    confidence=0.6,
                    reasoning="Afternoon planning pattern",
                    query_type="time_based",
                    temporal_pattern="afternoon_work"
                ))
        
        # Evening predictions (6-8 PM)
        elif 18 <= hour < 20:
            evening_queries = [
                "events tomorrow",
                "meetings tomorrow",
                "schedule this week"
            ]
            for query in evening_queries:
                predictions.append(PredictedQuery(
                    query=query,
                    probability=0.75,
                    predicted_time=context,
                    confidence=0.65,
                    reasoning="Evening preparation pattern",
                    query_type="time_based",
                    temporal_pattern="evening_planning"
                ))
        
        return predictions
    
    async def _update_patterns(self, query: str, dt: datetime, success: bool, cache_hit: bool):
        """Update pattern information based on new query."""
        template = self._extract_pattern_template(query)
        pattern_id = self._generate_pattern_id(template)
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.frequency += 1
            pattern.last_seen = dt
            
            # Update temporal distribution
            if dt.hour not in pattern.temporal_distribution:
                pattern.temporal_distribution[dt.hour] = 0
            pattern.temporal_distribution[dt.hour] += 1
            
            if dt.weekday() not in pattern.weekday_distribution:
                pattern.weekday_distribution[dt.weekday()] = 0
            pattern.weekday_distribution[dt.weekday()] += 1
            
            # Update success rate and cache effectiveness
            pattern.success_rate = (
                (pattern.success_rate * (pattern.frequency - 1) + (1.0 if success else 0.0)) / 
                pattern.frequency
            )
            pattern.cache_effectiveness = (
                (pattern.cache_effectiveness * (pattern.frequency - 1) + (1.0 if cache_hit else 0.0)) / 
                pattern.frequency
            )
            
            # Add query variation if not already present
            if query not in pattern.variations:
                pattern.variations.append(query)
                if len(pattern.variations) > 10:  # Limit variations
                    pattern.variations = pattern.variations[-10:]
            
        else:
            # Create new pattern
            pattern = QueryPattern(
                pattern_id=pattern_id,
                query_template=template,
                frequency=1,
                temporal_distribution={dt.hour: 1},
                weekday_distribution={dt.weekday(): 1},
                success_rate=1.0 if success else 0.0,
                cache_effectiveness=1.0 if cache_hit else 0.0,
                last_seen=dt,
                variations=[query]
            )
            self.patterns[pattern_id] = pattern
        
        # Save pattern to database
        await self._save_pattern(pattern)
    
    async def _save_pattern(self, pattern: QueryPattern):
        """Save pattern to database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO query_patterns 
                (pattern_id, query_template, frequency, temporal_distribution, 
                 weekday_distribution, success_rate, cache_effectiveness, 
                 last_seen, variations, agent_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.pattern_id,
                pattern.query_template,
                pattern.frequency,
                json.dumps(pattern.temporal_distribution),
                json.dumps(pattern.weekday_distribution),
                pattern.success_rate,
                pattern.cache_effectiveness,
                pattern.last_seen.timestamp(),
                json.dumps(pattern.variations),
                self.agent_id
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error saving pattern: {e}")
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get pattern analysis statistics."""
        return {
            "total_patterns": len(self.patterns),
            "active_patterns": len([p for p in self.patterns.values() 
                                  if (datetime.now() - p.last_seen).days < 7]),
            "high_frequency_patterns": len([p for p in self.patterns.values() 
                                          if p.frequency >= 10]),
            "prediction_accuracy": self.prediction_accuracy,
            "learning_rate": self.learning_rate,
            "confidence_threshold": self.prediction_confidence_threshold,
            "temporal_patterns_count": len(self.temporal_patterns)
        }