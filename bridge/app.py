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
CONTACTS_BRIDGE_MODE = os.getenv("CONTACTS_BRIDGE_MODE", "demo").strip().lower()

# Simple in-memory cache for live mail and contacts data
_mail_cache = {}
_contacts_cache = {}
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


def _get_cached_contacts(cache_key: str) -> Optional[List]:
    """Get cached contacts data if still valid."""
    with _cache_lock:
        if cache_key in _contacts_cache:
            data, timestamp = _contacts_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data
            else:
                # Expired, remove from cache
                del _contacts_cache[cache_key]
    return None


def _cache_contacts(cache_key: str, data: List) -> None:
    """Cache contacts data with timestamp."""
    with _cache_lock:
        _contacts_cache[cache_key] = (data, time.time())

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


async def _fetch_live_contacts_async(query: Optional[str] = None, limit: int = 100) -> List:
    """Fetch live contacts data in a thread to avoid blocking."""
    def _fetch_sync():
        try:
            print(f"[bridge] starting JXA contacts fetch, query={query}, limit={limit}")
            from contacts_live import fetch_all_contacts, search_contacts
            if query and query.strip():
                result = search_contacts(query=query.strip(), limit=limit)
            else:
                result = fetch_all_contacts(limit=limit)
            print(f"[bridge] JXA contacts fetch completed, got {len(result)} contacts")
            return result
        except Exception as e:
            print(f"[bridge] live contacts fetch error: {e}")
            return []
    
    # Run the blocking JXA call in a thread with timeout
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_sync),
            timeout=60.0  # 60 second timeout for JXA execution
        )
    except asyncio.TimeoutError:
        print(f"[bridge] JXA contacts fetch timed out after 60s")
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


@app.get("/v1/contacts")
async def get_contacts(
    query: Optional[str] = Query(None, description="Search query for contacts"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of contacts to return")
):
    """Get contacts from macOS Contacts.app or return demo data."""
    # Live mode: fetch from macOS Contacts via AppleScript with caching
    if CONTACTS_BRIDGE_MODE == "live":
        cache_key = f"contacts:{query or 'all'}:{limit}"
        
        # Try cache first
        cached_data = _get_cached_contacts(cache_key)
        if cached_data is not None:
            print(f"[bridge] returning cached contacts data for {cache_key}")
            return cached_data
        
        # Fetch live data asynchronously
        try:
            live_data = await _fetch_live_contacts_async(query, limit)
            # Cache the result
            _cache_contacts(cache_key, live_data)
            print(f"[bridge] fetched and cached live contacts data for {cache_key}")
            return live_data
        except Exception as live_err:
            # Fall back to demo data on error
            print(f"[bridge] live contacts fetch failed, falling back to demo: {live_err}")

    # Demo mode: generate deterministic fake data
    items = []
    search_term = (query or "").lower()
    
    # Generate some demo contacts
    demo_contacts = [
        {"id": "contact-1", "name": "John Doe", "emails": ["john.doe@example.com"], "phones": ["+1-555-0123"], "organization": "Acme Corp"},
        {"id": "contact-2", "name": "Jane Smith", "emails": ["jane.smith@example.com", "jane@work.com"], "phones": ["+1-555-0456"], "organization": "Tech Solutions"},
        {"id": "contact-3", "name": "Bob Johnson", "emails": ["bob@example.com"], "phones": ["+1-555-0789", "+1-555-0999"], "organization": ""},
        {"id": "contact-4", "name": "Alice Brown", "emails": ["alice.brown@company.org"], "phones": ["+1-555-1234"], "organization": "Nonprofit Inc"},
        {"id": "contact-5", "name": "Charlie Wilson", "emails": ["charlie@email.com"], "phones": ["+1-555-5678"], "organization": "Freelance"}
    ]
    
    # Filter by search query if provided
    for i, contact in enumerate(demo_contacts):
        if i >= limit:
            break
            
        # Apply search filter
        if search_term:
            name_match = search_term in contact["name"].lower()
            email_match = any(search_term in email.lower() for email in contact["emails"])
            phone_match = any(search_term in phone for phone in contact["phones"])
            org_match = search_term in contact.get("organization", "").lower()
            
            if not (name_match or email_match or phone_match or org_match):
                continue
        
        items.append({
            "id": contact["id"],
            "name": contact["name"],
            "firstName": contact["name"].split()[0] if " " in contact["name"] else contact["name"],
            "lastName": contact["name"].split()[-1] if " " in contact["name"] and len(contact["name"].split()) > 1 else "",
            "emails": contact["emails"],
            "phones": contact["phones"],
            "organization": contact["organization"],
            "note": "",
            "platforms": ["demo"],
            "source": "demo",
            "confidence": 0.85
        })
    
    return items


@app.get("/v1/contacts/{contact_id}")
async def get_contact_by_id(contact_id: str):
    """Get a specific contact by ID."""
    # Live mode: fetch from macOS Contacts
    if CONTACTS_BRIDGE_MODE == "live":
        try:
            from contacts_live import get_contact_by_id
            contact = await asyncio.get_event_loop().run_in_executor(
                None, get_contact_by_id, contact_id
            )
            if contact:
                return contact
        except Exception as e:
            print(f"[bridge] error fetching contact {contact_id}: {e}")
    
    # Demo mode or fallback: return demo contact
    if contact_id == "contact-1":
        return {
            "id": "contact-1",
            "name": "John Doe",
            "firstName": "John",
            "lastName": "Doe",
            "emails": ["john.doe@example.com"],
            "phones": ["+1-555-0123"],
            "organization": "Acme Corp",
            "note": "Demo contact for testing",
            "platforms": ["demo"],
            "source": "demo",
            "confidence": 1.0
        }
    
    return {"error": "Contact not found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5100)


