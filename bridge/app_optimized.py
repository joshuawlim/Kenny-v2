"""
Optimized Kenny Bridge with SQLite cache and background sync architecture.

This replaces the inefficient direct JXA approach with:
1. Local SQLite database for fast queries
2. Background sync worker for incremental updates  
3. Sub-second API responses from cache
4. Optimized JXA queries with date filtering
"""

import os
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

# Import our optimized components
from mail_cache import MailCache
from mail_sync_worker import (
    start_sync_worker, 
    stop_sync_worker, 
    get_sync_worker, 
    get_cached_messages
)
from mail_live_optimized import test_mail_connectivity

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Kenny Bridge Optimized", version="0.3.0")

# Bridge mode: "demo" (default) or "live"
BRIDGE_MODE = os.getenv("MAIL_BRIDGE_MODE", "demo").strip().lower()
CONTACTS_BRIDGE_MODE = os.getenv("CONTACTS_BRIDGE_MODE", "demo").strip().lower()

# Initialize mail cache
mail_cache = MailCache()

class MailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    from_: str = Field(alias="from")
    to: List[str] = []
    subject: Optional[str] = None
    ts: str
    snippet: Optional[str] = None

class Contact(BaseModel):
    id: str
    name: str
    firstName: Optional[str] = None
    lastName: Optional[str] = None
    emails: List[str] = []
    phones: List[str] = []
    organization: Optional[str] = None
    note: Optional[str] = None
    platforms: List[str] = []
    source: Optional[str] = None
    confidence: Optional[float] = None
    match_rank: Optional[int] = None

@app.on_event("startup")
async def startup_event():
    """Initialize background sync worker on startup."""
    if BRIDGE_MODE == "live":
        logger.info("Starting optimized bridge in live mode")
        start_sync_worker()
        logger.info("Background sync worker started")
    else:
        logger.info("Starting bridge in demo mode")

@app.on_event("shutdown")  
async def shutdown_event():
    """Clean shutdown of background workers."""
    if BRIDGE_MODE == "live":
        logger.info("Stopping background sync worker")
        stop_sync_worker()

@app.get("/health")
def health():
    """Health check with sync worker status."""
    if BRIDGE_MODE == "live":
        worker = get_sync_worker()
        sync_status = worker.get_sync_status()
        return {
            "status": "ok",
            "mode": "live",
            "sync_worker_running": sync_status["worker_status"]["is_running"],
            "last_sync": sync_status["worker_status"]["last_sync_time"],
            "cache_message_count": sync_status["cache_statistics"]["total_messages"]
        }
    else:
        return {"status": "ok", "mode": "demo"}

@app.get("/v1/mail/messages")
async def mail_messages(
    mailbox: str = Query("Inbox"),
    since: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    page: int = Query(0, ge=0),
):
    """
    Get mail messages with optimized caching architecture.
    
    In live mode: Serves from local SQLite cache (sub-second response)
    In demo mode: Generates mock data
    """
    
    if BRIDGE_MODE == "live":
        try:
            # Parse since parameter if provided
            since_date = None
            if since:
                try:
                    since_date = datetime.fromisoformat(since.replace("Z", "+00:00"))
                except ValueError:
                    logger.warning(f"Invalid since date format: {since}")
            
            # Get messages from cache (fast!)
            messages = get_cached_messages(
                mailbox=mailbox,
                limit=limit,
                page=page,
                since=since_date
            )
            
            logger.info(f"[bridge-optimized] Served {len(messages)} messages from cache for {mailbox}")
            return messages
            
        except Exception as e:
            logger.error(f"[bridge-optimized] Cache read failed: {e}")
            # Fall back to demo data on cache errors
            pass
    
    # Demo mode: Generate deterministic fake data (fallback)
    try:
        since_dt = datetime.fromisoformat((since or "").replace("Z", "+00:00"))
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
    except Exception:
        since_dt = datetime.now(timezone.utc) - timedelta(days=30)
    
    base_ts = datetime.now(timezone.utc)
    start_index = page * limit
    items = []
    for i in range(start_index, start_index + limit):
        ts = base_ts - timedelta(minutes=5 * i)
        if ts < since_dt:
            break
        items.append({
            "id": f"{mailbox.lower()}-msg-{start_index + i + 1}",
            "from": f"sender{(start_index + i) % 10}@example.com",
            "to": ["recipient@example.com"],
            "subject": f"Demo message {start_index + i + 1} in {mailbox}",
            "ts": ts.isoformat(),
            "snippet": f"This is demo message {start_index + i + 1} content..."
        })
    
    logger.info(f"[bridge-demo] Generated {len(items)} demo messages for {mailbox}")
    return items

@app.get("/v1/mail/sync/status")
async def get_sync_status():
    """Get detailed sync worker status and cache statistics."""
    if BRIDGE_MODE != "live":
        raise HTTPException(status_code=400, detail="Sync status only available in live mode")
    
    worker = get_sync_worker()
    return worker.get_sync_status()

@app.post("/v1/mail/sync/force")
async def force_sync(mailbox: Optional[str] = None):
    """Force an immediate sync of specified mailbox or all mailboxes."""
    if BRIDGE_MODE != "live":
        raise HTTPException(status_code=400, detail="Force sync only available in live mode")
    
    worker = get_sync_worker()
    result = worker.force_sync_now(mailbox)
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.get("/v1/mail/test")
async def test_mail_integration():
    """Test Apple Mail connectivity and integration."""
    if BRIDGE_MODE != "live":
        raise HTTPException(status_code=400, detail="Mail test only available in live mode")
    
    return test_mail_connectivity()

@app.get("/v1/mail/cache/stats")
async def get_cache_stats():
    """Get cache statistics and performance metrics."""
    if BRIDGE_MODE != "live":
        raise HTTPException(status_code=400, detail="Cache stats only available in live mode")
    
    return mail_cache.get_cache_stats()

@app.post("/v1/mail/cache/cleanup")
async def cleanup_cache(days_to_keep: int = Query(30, ge=1, le=365)):
    """Clean up old cached messages to manage storage."""
    if BRIDGE_MODE != "live":
        raise HTTPException(status_code=400, detail="Cache cleanup only available in live mode")
    
    deleted_count = mail_cache.cleanup_old_messages(days_to_keep)
    return {
        "status": "success",
        "deleted_messages": deleted_count,
        "days_kept": days_to_keep,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Legacy contacts endpoint (unchanged for now)
@app.get("/v1/contacts")
async def contacts(query: Optional[str] = None, limit: int = Query(100, ge=1, le=500)):
    """Get contacts - using existing implementation for now."""
    
    # Contacts implementation unchanged - keeping existing logic
    if CONTACTS_BRIDGE_MODE == "live":
        try:
            from contacts_live import fetch_all_contacts, search_contacts
            if query and query.strip():
                result = search_contacts(query=query.strip(), limit=limit)
            else:
                result = fetch_all_contacts(limit=limit)
            return result
        except Exception as e:
            logger.error(f"Live contacts fetch failed: {e}")
            # Fall back to demo data
    
    # Demo contacts data
    base_contacts = [
        {"id": "contact-1", "name": "John Doe", "emails": ["john@example.com"], "phones": ["+1234567890"]},
        {"id": "contact-2", "name": "Jane Smith", "emails": ["jane@example.com"], "phones": ["+0987654321"]},
        {"id": "contact-3", "name": "Bob Johnson", "emails": ["bob@example.com"], "phones": ["+1122334455"]},
    ]
    
    if query:
        # Simple filtering for demo
        query_lower = query.lower()
        filtered = [c for c in base_contacts if query_lower in c["name"].lower()]
        return filtered[:limit]
    
    return base_contacts[:limit]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5100)