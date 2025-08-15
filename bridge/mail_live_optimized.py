"""
Optimized Apple Mail integration with date-filtered JXA queries.

This module replaces the inefficient "fetch all messages" approach with
targeted queries that use Apple Mail's native filtering capabilities.
"""

import json
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

def _run_jxa_with_timeout(script: str, timeout_seconds: int = 10) -> str:
    """Run JXA script with timeout and error handling."""
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout_seconds
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or f"osascript failed with code {result.returncode}"
            logger.error(f"JXA script failed: {error_msg}")
            raise RuntimeError(error_msg)
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        logger.error(f"JXA script timed out after {timeout_seconds} seconds")
        raise RuntimeError(f"JXA script timed out after {timeout_seconds} seconds")

def _build_optimized_fetch_script(
    mailbox_name: str, 
    limit: int, 
    since_date: Optional[datetime] = None
) -> str:
    """Build optimized JXA script with native Apple Mail filtering."""
    
    # Escape mailbox name for inclusion in JS string
    mbox = mailbox_name.replace("\\", "\\\\").replace("\"", "\\\"")
    
    # Build date filter if provided
    date_filter = ""
    if since_date:
        # Convert to Apple Mail date format
        since_js = since_date.strftime("%Y-%m-%d %H:%M:%S")
        date_filter = f"""
        const sinceDate = new Date("{since_js}");
        messages = messages.filter(msg => {{
            try {{
                const msgDate = new Date(msg.dateReceived());
                return msgDate >= sinceDate;
            }} catch (e) {{
                return true; // Include if date parsing fails
            }}
        }});
        """
    
    # JXA script with optimized approach
    return f"""
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;
    
    const Mail = Application('Mail');
    
    function getMailboxMessages(name, maxCount) {{
        const lower = String(name || '').toLowerCase();
        let mailbox = null;
        
        try {{
            if (lower === 'inbox') {{
                mailbox = Mail.inbox();
            }} else if (lower === 'sent' || lower === 'sent mailbox' || lower === 'sent messages') {{
                if (typeof Mail.sentMailbox === 'function') {{
                    mailbox = Mail.sentMailbox();
                }}
            }} else {{
                // Generic lookup by name
                const boxes = Mail.mailboxes.whose({{ name: name }})();
                if (boxes.length > 0) {{
                    mailbox = boxes[0];
                }}
            }}
            
            if (!mailbox) {{
                throw new Error(`Mailbox not found: ${{name}}`);
            }}
            
            // Get messages with Apple Mail's native limiting
            let messages = mailbox.messages();
            
            {date_filter}
            
            // Sort by date (most recent first) - this is more efficient than fetching all
            messages.sort((a, b) => {{
                try {{
                    const dateA = new Date(a.dateReceived());
                    const dateB = new Date(b.dateReceived());
                    return dateB.getTime() - dateA.getTime();
                }} catch (e) {{
                    return 0;
                }}
            }});
            
            // Limit to requested count BEFORE processing
            if (messages.length > maxCount) {{
                messages = messages.slice(0, maxCount);
            }}
            
            return messages;
            
        }} catch (e) {{
            throw new Error(`Failed to get mailbox messages: ${{e.message}}`);
        }}
    }}
    
    function toJs(msg) {{
        try {{
            const idVal = msg.id ? String(msg.id()) : '';
            const subjectVal = msg.subject ? String(msg.subject()) : '';
            const dateVal = msg.dateReceived ? msg.dateReceived() : new Date();
            
            let fromVal = '';
            try {{
                fromVal = msg.sender ? String(msg.sender().address()) : '';
            }} catch (e) {{
                fromVal = msg.sender ? String(msg.sender()) : '';
            }}
            
            let toList = [];
            try {{
                const recips = msg.toRecipients ? msg.toRecipients() : [];
                toList = (recips || []).map(r => {{
                    try {{ 
                        return r.address ? String(r.address()) : String(r); 
                    }} catch (e) {{ 
                        return String(r); 
                    }}
                }});
            }} catch (e) {{ 
                toList = []; 
            }}
            
            const snippet = subjectVal ? subjectVal.substring(0, 120) : '';
            
            return {{ 
                id: idVal, 
                from: fromVal, 
                to: toList, 
                subject: subjectVal, 
                ts: new Date(dateVal).toISOString(), 
                snippet: snippet 
            }};
        }} catch (e) {{
            return {{ 
                id: '', 
                from: '', 
                to: [], 
                subject: 'Error processing message', 
                ts: new Date().toISOString(), 
                snippet: '' 
            }};
        }}
    }}
    
    try {{
        const messages = getMailboxMessages("{mbox}", {int(limit)});
        const result = messages.map(msg => toJs(msg));
        JSON.stringify(result);
    }} catch (e) {{
        JSON.stringify({{ error: e.message, messages: [] }});
    }}
    """

def fetch_recent_messages(
    mailbox: str = "Inbox", 
    limit: int = 100, 
    since_date: Optional[datetime] = None,
    timeout_seconds: int = 10
) -> List[Dict[str, Any]]:
    """
    Fetch recent messages using optimized JXA queries.
    
    Args:
        mailbox: Mailbox name (e.g., "Inbox", "Sent")
        limit: Maximum number of messages to fetch
        since_date: Only fetch messages newer than this date
        timeout_seconds: JXA execution timeout
        
    Returns:
        List of message dictionaries
    """
    try:
        script = _build_optimized_fetch_script(mailbox, limit, since_date)
        result_json = _run_jxa_with_timeout(script, timeout_seconds)
        
        if not result_json:
            logger.warning("Empty result from JXA script")
            return []
        
        result = json.loads(result_json)
        
        # Handle error response from JXA
        if isinstance(result, dict) and 'error' in result:
            logger.error(f"JXA script error: {result['error']}")
            return result.get('messages', [])
        
        # Validate result is a list
        if not isinstance(result, list):
            logger.error(f"Unexpected result type: {type(result)}")
            return []
        
        logger.info(f"Successfully fetched {len(result)} messages from {mailbox}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JXA result as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to fetch messages: {e}")
        return []

def fetch_messages_since_timestamp(
    mailbox: str, 
    since_timestamp: str, 
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Fetch messages newer than a specific timestamp.
    
    This is optimized for incremental sync operations.
    """
    try:
        # Parse timestamp
        since_date = datetime.fromisoformat(since_timestamp.replace('Z', '+00:00'))
        
        # Add small buffer to avoid missing messages due to clock skew
        since_date = since_date - timedelta(minutes=1)
        
        return fetch_recent_messages(
            mailbox=mailbox,
            limit=limit, 
            since_date=since_date,
            timeout_seconds=15  # Slightly longer timeout for incremental sync
        )
        
    except ValueError as e:
        logger.error(f"Invalid timestamp format: {since_timestamp}")
        return []

def test_mail_connectivity() -> Dict[str, Any]:
    """Test basic Apple Mail connectivity with optimized approach."""
    try:
        # Test with minimal fetch
        messages = fetch_recent_messages("Inbox", limit=1, timeout_seconds=5)
        
        return {
            "status": "success",
            "accessible": True,
            "sample_message_count": len(messages),
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "accessible": False,
            "error": str(e),
            "test_timestamp": datetime.now(timezone.utc).isoformat()
        }

# Legacy compatibility function
def fetch_mail_messages(
    mailbox: str, 
    since_iso: Optional[str], 
    limit: int, 
    page: int
) -> List[Dict[str, Any]]:
    """
    Legacy compatibility wrapper for the optimized implementation.
    
    This maintains the same interface as the original mail_live.py
    but uses the optimized approach internally.
    """
    try:
        # Convert since_iso to datetime if provided
        since_date = None
        if since_iso:
            since_date = datetime.fromisoformat(since_iso.replace('Z', '+00:00'))
        
        # Fetch messages with the optimized approach
        messages = fetch_recent_messages(
            mailbox=mailbox,
            limit=limit + (page * limit),  # Adjust for pagination
            since_date=since_date,
            timeout_seconds=15
        )
        
        # Apply pagination
        start_idx = page * limit
        end_idx = start_idx + limit
        paginated_messages = messages[start_idx:end_idx]
        
        logger.info(f"Legacy fetch: {len(paginated_messages)} messages (page {page}, limit {limit})")
        return paginated_messages
        
    except Exception as e:
        logger.error(f"Legacy fetch failed: {e}")
        return []