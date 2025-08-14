"""
Message analyzer tool for extracting contact enrichment data from messages.

This tool analyzes message content across platforms (iMessage, WhatsApp, Email)
to extract job information, interests, relationships, and interaction patterns
for contact enrichment.
"""

import sys
import logging
import sqlite3
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
import requests
import asyncio

# Add the agent-sdk to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "agent-sdk"))

from kenny_agent.base_tool import BaseTool


class MessageAnalyzer(BaseTool):
    """Tool for analyzing messages to extract contact enrichment data."""
    
    def __init__(self, memory_client_url: str = "http://localhost:8003"):
        """Initialize the message analyzer tool."""
        super().__init__(
            name="message_analyzer",
            description="Analyze messages for contact enrichment data extraction"
        )
        self.memory_client_url = memory_client_url
        self.logger = logging.getLogger(__name__)
        
        # iMessage database path
        self.imessage_db_path = Path.home() / "Library" / "Messages" / "chat.db"
        
    async def analyze_messages_for_contact(
        self, 
        contact_id: str, 
        contact_name: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Analyze messages for a specific contact to extract enrichment data.
        
        Args:
            contact_id: Unique identifier for the contact
            contact_name: Display name of the contact
            lookback_days: Number of days to look back in message history
            
        Returns:
            Dict containing extracted enrichment data
        """
        try:
            # Get contact identifiers (phone numbers, emails) for message matching
            contact_identifiers = await self._get_contact_identifiers(contact_name)
            
            # Get message data from multiple sources
            message_data = await self._collect_message_data(contact_identifiers, lookback_days)
            
            if not message_data:
                self.logger.info(f"No messages found for contact {contact_name}")
                return self._empty_analysis_result()
            
            # Analyze message content for enrichment data
            analysis_result = await self._analyze_message_content(message_data, contact_name)
            
            # Store analysis in memory for future reference
            await self._store_analysis_in_memory(contact_id, contact_name, analysis_result)
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing messages for {contact_name}: {e}")
            return self._empty_analysis_result()
    
    async def _get_contact_identifiers(self, contact_name: str) -> List[str]:
        """Get phone numbers and emails associated with a contact."""
        # For now, we'll extract potential identifiers from the contact name
        # In a real implementation, this would query the contacts database
        identifiers = []
        
        # Basic email detection
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, contact_name)
        identifiers.extend(emails)
        
        # Basic phone number detection 
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        phones = re.findall(phone_pattern, contact_name)
        identifiers.extend(phones)
        
        # If no identifiers found, use the name for matching
        if not identifiers:
            identifiers.append(contact_name.lower())
            
        return identifiers
    
    async def _collect_message_data(self, identifiers: List[str], lookback_days: int) -> List[Dict]:
        """Collect message data from various sources for the given identifiers."""
        all_messages = []
        
        # Get iMessage data
        imessage_data = await self._get_imessage_data(identifiers, lookback_days)
        all_messages.extend(imessage_data)
        
        # Get email data (via mail agent if available)
        email_data = await self._get_email_data(identifiers, lookback_days)
        all_messages.extend(email_data)
        
        return all_messages
    
    async def _get_imessage_data(self, identifiers: List[str], lookback_days: int) -> List[Dict]:
        """Get iMessage data for the contact identifiers."""
        try:
            if not self.imessage_db_path.exists():
                self.logger.warning("iMessage database not found")
                return []
            
            since_date = datetime.now() - timedelta(days=lookback_days)
            # Convert to Apple epoch (seconds since 2001-01-01)
            apple_epoch = datetime(2001, 1, 1)
            since_apple_time = int((since_date - apple_epoch).total_seconds())
            
            messages = []
            
            with sqlite3.connect(str(self.imessage_db_path)) as conn:
                conn.row_factory = sqlite3.Row
                
                # Query for messages from/to the contact identifiers
                query = """
                SELECT 
                    m.ROWID,
                    m.text,
                    m.date,
                    m.is_from_me,
                    h.id as handle_id,
                    c.guid as chat_guid
                FROM message m
                JOIN chat_message_join cmj ON m.ROWID = cmj.message_id
                JOIN chat c ON cmj.chat_id = c.ROWID
                JOIN handle h ON m.handle_id = h.ROWID
                WHERE m.date >= ? AND m.text IS NOT NULL
                ORDER BY m.date DESC
                LIMIT 500
                """
                
                cursor = conn.execute(query, (since_apple_time,))
                rows = cursor.fetchall()
                
                for row in rows:
                    # Check if this message involves our contact
                    handle_id = row['handle_id'].lower()
                    if any(identifier.lower() in handle_id for identifier in identifiers):
                        # Convert Apple time to Unix timestamp
                        unix_time = since_apple_time + 978307200  # Apple epoch offset
                        
                        messages.append({
                            'platform': 'imessage',
                            'content': row['text'],
                            'timestamp': unix_time,
                            'is_outgoing': bool(row['is_from_me']),
                            'sender_id': handle_id,
                            'thread_id': row['chat_guid']
                        })
                        
            self.logger.info(f"Found {len(messages)} iMessage messages")
            return messages
            
        except Exception as e:
            self.logger.error(f"Error querying iMessage database: {e}")
            return []
    
    async def _get_email_data(self, identifiers: List[str], lookback_days: int) -> List[Dict]:
        """Get email data for the contact identifiers."""
        try:
            # Try to get email data via the mail agent bridge
            bridge_url = "http://localhost:5100/v1/mail/messages"
            
            # Query for messages from the contact identifiers
            for identifier in identifiers:
                if '@' in identifier:  # Only query emails
                    try:
                        response = requests.get(
                            bridge_url,
                            params={'from': identifier, 'limit': 100},
                            timeout=10
                        )
                        
                        if response.status_code == 200:
                            mail_data = response.json()
                            messages = []
                            
                            for msg in mail_data.get('messages', []):
                                messages.append({
                                    'platform': 'email',
                                    'content': msg.get('snippet', ''),
                                    'timestamp': msg.get('ts', ''),
                                    'is_outgoing': False,  # Assume incoming for now
                                    'sender_id': msg.get('from', ''),
                                    'thread_id': msg.get('thread_id', ''),
                                    'subject': msg.get('subject', '')
                                })
                            
                            self.logger.info(f"Found {len(messages)} email messages")
                            return messages
                            
                    except requests.RequestException as e:
                        self.logger.warning(f"Could not fetch email data: {e}")
                        
        except Exception as e:
            self.logger.error(f"Error getting email data: {e}")
            
        return []
    
    async def _analyze_message_content(self, messages: List[Dict], contact_name: str) -> Dict[str, Any]:
        """Analyze message content to extract enrichment data."""
        try:
            # Combine all message content for analysis
            all_content = []
            for msg in messages:
                if msg.get('content'):
                    all_content.append(msg['content'])
            
            if not all_content:
                return self._empty_analysis_result()
            
            # Use LLM-powered analysis via memory agent
            analysis_result = await self._llm_analyze_content(all_content, contact_name)
            
            # Add interaction patterns analysis
            interaction_patterns = self._analyze_interaction_patterns(messages)
            analysis_result['interaction_patterns'] = interaction_patterns
            
            return analysis_result
            
        except Exception as e:
            self.logger.error(f"Error analyzing message content: {e}")
            return self._empty_analysis_result()
    
    async def _llm_analyze_content(self, content_list: List[str], contact_name: str) -> Dict[str, Any]:
        """Use LLM to analyze message content for enrichment data."""
        try:
            # Prepare content for analysis
            combined_content = "\n".join(content_list[:50])  # Limit content size
            
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze the following messages involving {contact_name} and extract:
            1. Job title or occupation information
            2. Interests and hobbies mentioned
            3. Relationship type (colleague, friend, family, etc.)
            
            Messages:
            {combined_content}
            
            Return a JSON response with:
            - job_info: list of {{value, confidence, source_evidence}}
            - interests: list of {{value, confidence, source_evidence}}
            - relationships: list of {{value, confidence, source_evidence}}
            """
            
            # Try to get analysis via memory agent embedding
            memory_response = await self._query_memory_agent(analysis_prompt)
            
            if memory_response:
                return self._parse_llm_response(memory_response)
            else:
                # Fallback to pattern-based analysis
                return self._pattern_based_analysis(content_list)
                
        except Exception as e:
            self.logger.error(f"Error in LLM analysis: {e}")
            return self._pattern_based_analysis(content_list)
    
    async def _query_memory_agent(self, prompt: str) -> Optional[str]:
        """Query the memory agent for LLM-powered analysis."""
        try:
            response = requests.post(
                f"{self.memory_client_url}/capabilities/memory.embed",
                json={"input": {"text": prompt}},
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json().get('result', {}).get('analysis', '')
                
        except requests.RequestException as e:
            self.logger.warning(f"Could not query memory agent: {e}")
            
        return None
    
    def _pattern_based_analysis(self, content_list: List[str]) -> Dict[str, Any]:
        """Fallback pattern-based analysis when LLM is not available."""
        combined_text = " ".join(content_list).lower()
        
        # Job-related patterns
        job_patterns = [
            (r'\b(?:work|job|company|office|team|project|manager|engineer|developer|designer)\b', 'work_context', 0.6),
            (r'\b(?:meeting|call|deadline|client|boss|colleague)\b', 'professional_context', 0.7),
            (r'\b(?:at [A-Za-z]+|works at|company called)\b', 'company_mention', 0.8)
        ]
        
        # Interest patterns  
        interest_patterns = [
            (r'\b(?:love|enjoy|hobby|interested in|passion for)\b', 'interest_expression', 0.7),
            (r'\b(?:music|sports|travel|reading|cooking|photography)\b', 'common_interests', 0.6),
            (r'\b(?:weekend|vacation|free time|after work)\b', 'leisure_context', 0.5)
        ]
        
        # Relationship patterns
        relationship_patterns = [
            (r'\b(?:colleague|coworker|teammate)\b', 'colleague', 0.9),
            (r'\b(?:friend|buddy|pal)\b', 'friend', 0.8),
            (r'\b(?:family|brother|sister|parent|cousin)\b', 'family', 0.9)
        ]
        
        job_info = []
        interests = []
        relationships = []
        
        # Analyze patterns
        for pattern, context, confidence in job_patterns:
            if re.search(pattern, combined_text):
                job_info.append({
                    "value": f"Work-related context detected: {context}",
                    "confidence": confidence,
                    "source_evidence": f"Pattern match: {pattern}"
                })
        
        for pattern, interest, confidence in interest_patterns:
            if re.search(pattern, combined_text):
                interests.append({
                    "value": f"Interest detected: {interest}",
                    "confidence": confidence,
                    "source_evidence": f"Pattern match: {pattern}"
                })
        
        for pattern, relationship, confidence in relationship_patterns:
            if re.search(pattern, combined_text):
                relationships.append({
                    "value": relationship.title(),
                    "confidence": confidence,
                    "source_evidence": f"Pattern match: {pattern}"
                })
        
        return {
            "job_info": job_info,
            "interests": interests,
            "relationships": relationships
        }
    
    def _analyze_interaction_patterns(self, messages: List[Dict]) -> Dict[str, Any]:
        """Analyze interaction patterns from message data."""
        if not messages:
            return {
                "frequency": "none",
                "recency": "never",
                "sentiment": "neutral",
                "topic_distribution": {}
            }
        
        # Calculate frequency
        message_count = len(messages)
        if message_count > 20:
            frequency = "high"
        elif message_count > 5:
            frequency = "medium"
        else:
            frequency = "low"
        
        # Calculate recency
        if messages:
            latest_msg = max(messages, key=lambda m: m.get('timestamp', 0))
            latest_time = latest_msg.get('timestamp', 0)
            
            if isinstance(latest_time, str):
                try:
                    latest_dt = datetime.fromisoformat(latest_time.replace('Z', '+00:00'))
                except:
                    latest_dt = datetime.now() - timedelta(days=999)
            else:
                latest_dt = datetime.fromtimestamp(latest_time)
            
            days_ago = (datetime.now() - latest_dt).days
            
            if days_ago < 1:
                recency = "today"
            elif days_ago < 7:
                recency = f"{days_ago} days ago"
            elif days_ago < 30:
                recency = f"{days_ago // 7} weeks ago"
            else:
                recency = f"{days_ago // 30} months ago"
        else:
            recency = "never"
        
        # Basic sentiment analysis (placeholder)
        sentiment = "neutral"
        
        # Topic distribution (placeholder)
        topic_distribution = {"personal": 0.5, "work": 0.5}
        
        return {
            "frequency": frequency,
            "recency": recency,
            "sentiment": sentiment,
            "topic_distribution": topic_distribution
        }
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response into structured format."""
        try:
            # Try to extract JSON from the response
            import json
            return json.loads(response_text)
        except:
            # Fallback to empty structure
            return self._empty_analysis_result()
    
    async def _store_analysis_in_memory(self, contact_id: str, contact_name: str, analysis_result: Dict) -> None:
        """Store the analysis result in memory for future reference."""
        try:
            memory_content = f"Contact enrichment analysis for {contact_name}"
            
            response = requests.post(
                f"{self.memory_client_url}/capabilities/memory.store",
                json={
                    "input": {
                        "content": memory_content,
                        "metadata": {
                            "source": "contacts_agent",
                            "data_scope": "contact_enrichment",
                            "contact_id": contact_id,
                            "contact_name": contact_name,
                            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
                            "enrichment_data": analysis_result
                        }
                    }
                },
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info(f"Stored analysis in memory for {contact_name}")
            else:
                self.logger.warning(f"Failed to store analysis in memory: {response.status_code}")
                
        except requests.RequestException as e:
            self.logger.warning(f"Could not store analysis in memory: {e}")
    
    def _empty_analysis_result(self) -> Dict[str, Any]:
        """Return empty analysis result structure."""
        return {
            "job_info": [],
            "interests": [],
            "relationships": [],
            "interaction_patterns": {
                "frequency": "none",
                "recency": "never",
                "sentiment": "neutral",
                "topic_distribution": {}
            }
        }
    
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the message analyzer tool.
        
        Args:
            parameters: Contains contact_id, contact_name, and optional lookback_days
            
        Returns:
            Dict containing analysis results
        """
        contact_id = parameters.get("contact_id", "")
        contact_name = parameters.get("contact_name", "")
        lookback_days = parameters.get("lookback_days", 30)
        
        if not contact_id and not contact_name:
            return {"error": "Either contact_id or contact_name is required"}
        
        try:
            analysis_result = await self.analyze_messages_for_contact(
                contact_id, contact_name, lookback_days
            )
            return {"success": True, "analysis": analysis_result}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """Return tool usage summary."""
        return {
            "tool_name": self.name,
            "description": self.description,
            "usage_count": self.usage_count,
            "average_execution_time": self.average_execution_time
        }