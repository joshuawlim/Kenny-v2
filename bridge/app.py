import os
import asyncio
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import threading
import time

app = FastAPI(title="Kenny Bridge", version="0.2.0")

# Bridge mode: "demo" (default) or "live"
BRIDGE_MODE = os.getenv("MAIL_BRIDGE_MODE", "demo").strip().lower()

# Simple in-memory cache for live mail data
_mail_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL_SECONDS = 120  # Cache for 2 minutes given slow JXA execution


class MailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    from_: str = Field(alias="from")
    to: List[str] = []
    subject: Optional[str] = None
    ts: str
    snippet: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


def _get_cache_key(mailbox: str, since: Optional[str], limit: int, page: int) -> str:
    """Generate cache key for mail request."""
    return f"{mailbox}:{since or 'None'}:{limit}:{page}"

def _get_cached_mail(cache_key: str) -> Optional[List]:
    """Get cached mail data if still valid."""
    with _cache_lock:
        if cache_key in _mail_cache:
            data, timestamp = _mail_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data
            else:
                # Expired, remove from cache
                del _mail_cache[cache_key]
    return None

def _cache_mail(cache_key: str, data: List) -> None:
    """Cache mail data with timestamp."""
    with _cache_lock:
        _mail_cache[cache_key] = (data, time.time())

async def _fetch_live_mail_async(mailbox: str, since: Optional[str], limit: int, page: int) -> List:
    """Fetch live mail data in a thread to avoid blocking."""
    def _fetch_sync():
        try:
            print(f"[bridge] starting JXA fetch for {mailbox}, limit={limit}")
            from mail_live import fetch_mail_messages
            result = fetch_mail_messages(mailbox=mailbox, since_iso=since, limit=limit, page=page)
            print(f"[bridge] JXA fetch completed, got {len(result)} messages")
            return result
        except Exception as e:
            print(f"[bridge] live fetch error: {e}")
            return []
    
    # Run the blocking JXA call in a thread with timeout
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_sync),
            timeout=60.0  # 60 second timeout for JXA execution (JXA is slow)
        )
    except asyncio.TimeoutError:
        print(f"[bridge] JXA fetch timed out after 60s for {mailbox}")
        return []

@app.get("/v1/mail/messages")
async def mail_messages(
    mailbox: str = Query("Inbox"),
    since: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    page: int = Query(0, ge=0),
):
    # Live mode: fetch from Apple Mail via AppleScript with caching
    if BRIDGE_MODE == "live":
        cache_key = _get_cache_key(mailbox, since, limit, page)
        
        # Try cache first
        cached_data = _get_cached_mail(cache_key)
        if cached_data is not None:
            print(f"[bridge] returning cached data for {cache_key}")
            return cached_data
        
        # Fetch live data asynchronously
        try:
            live_data = await _fetch_live_mail_async(mailbox, since, limit, page)
            # Cache the result
            _cache_mail(cache_key, live_data)
            print(f"[bridge] fetched and cached live data for {cache_key}")
            return live_data
        except Exception as live_err:
            # Fall back to demo data on error
            print(f"[bridge] live fetch failed, falling back to demo: {live_err}")

    # Demo mode: generate deterministic fake data
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
        items.append(
            {
                "id": f"mail-{mailbox.lower()}-{i}",
                "thread_id": f"thread-{i%20}",
                "from": "example@sender.com" if mailbox == "Inbox" else "me@example.com",
                "to": ["me@example.com"] if mailbox == "Inbox" else ["friend@example.com"],
                "subject": f"Demo {mailbox} message #{i}",
                "ts": ts.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
                "snippet": "This is a demo snippet.",
            }
        )
    return items


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5100)


