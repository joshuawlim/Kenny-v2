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
IMESSAGE_BRIDGE_MODE = os.getenv("IMESSAGE_BRIDGE_MODE", "demo").strip().lower()

# Simple in-memory cache for live mail, contacts, and imessage data
_mail_cache = {}
_contacts_cache = {}
_imessage_cache = {}
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


class iMessageMessage(BaseModel):
    id: str
    thread_id: str
    from_: Optional[str] = Field(alias="from")
    to: Optional[str] = None
    content: Optional[str] = None
    timestamp: str
    message_type: str = "text"
    has_attachments: bool = False
    contact_name: Optional[str] = None
    phone_number: Optional[str] = None
    attachments: List[dict] = []


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


def _get_cached_imessages(cache_key: str) -> Optional[List]:
    """Get cached iMessage data if still valid."""
    with _cache_lock:
        if cache_key in _imessage_cache:
            data, timestamp = _imessage_cache[cache_key]
            if time.time() - timestamp < CACHE_TTL_SECONDS:
                return data
            else:
                # Expired, remove from cache
                del _imessage_cache[cache_key]
    return None


def _cache_imessages(cache_key: str, data: List) -> None:
    """Cache iMessage data with timestamp."""
    with _cache_lock:
        _imessage_cache[cache_key] = (data, time.time())

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


async def _fetch_live_imessages_async(operation: str, **kwargs) -> List:
    """Fetch live iMessage data in a thread to avoid blocking."""
    def _fetch_sync():
        try:
            print(f"[bridge] starting JXA iMessage {operation}, kwargs={kwargs}")
            from imessage_live import fetch_imessages, search_imessages, get_imessage_thread
            
            if operation == "list":
                result = fetch_imessages(limit=kwargs.get("limit", 100), page=kwargs.get("page", 0))
            elif operation == "search":
                result = search_imessages(query=kwargs.get("query", ""), limit=kwargs.get("limit", 50))
            elif operation == "read_thread":
                result = get_imessage_thread(thread_id=kwargs.get("thread_id"))
            elif operation == "read_message":
                # For individual message reads, we'd need a specific function
                result = []
            else:
                result = []
                
            print(f"[bridge] JXA iMessage {operation} completed, got {len(result)} items")
            return result
        except Exception as e:
            print(f"[bridge] live iMessage {operation} error: {e}")
            return []
    
    # Run the blocking JXA call in a thread with timeout
    loop = asyncio.get_event_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(None, _fetch_sync),
            timeout=60.0  # 60 second timeout for JXA execution
        )
    except asyncio.TimeoutError:
        print(f"[bridge] JXA iMessage {operation} timed out after 60s")
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


@app.get("/v1/messages/imessage")
async def imessage_messages(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of messages to return"),
    page: int = Query(0, ge=0, description="Page number for pagination"),
):
    """Get recent iMessages from Messages.app or return demo data."""
    # Live mode: fetch from macOS Messages via AppleScript with caching
    if IMESSAGE_BRIDGE_MODE == "live":
        cache_key = f"imessage:list:{limit}:{page}"
        
        # Try cache first
        cached_data = _get_cached_imessages(cache_key)
        if cached_data is not None:
            print(f"[bridge] returning cached iMessage data for {cache_key}")
            return cached_data
        
        # Fetch live data asynchronously
        try:
            live_data = await _fetch_live_imessages_async("list", limit=limit, page=page)
            # Cache the result
            _cache_imessages(cache_key, live_data)
            print(f"[bridge] fetched and cached live iMessage data for {cache_key}")
            return live_data
        except Exception as live_err:
            # Fall back to demo data on error
            print(f"[bridge] live iMessage fetch failed, falling back to demo: {live_err}")

    # Demo mode: generate deterministic fake data
    base_ts = datetime.now(timezone.utc)
    start_index = page * limit
    items = []
    for i in range(start_index, start_index + limit):
        ts = base_ts - timedelta(minutes=10 * i)
        contact_name = f"Contact {(i % 5) + 1}"
        phone_number = f"+1-555-{(i % 9000) + 1000:04d}"
        
        items.append({
            "id": f"imessage-{i}",
            "thread_id": f"thread-{i % 10}",
            "from": contact_name if i % 2 == 0 else "Me",
            "to": "Me" if i % 2 == 0 else contact_name,
            "content": f"Demo iMessage #{i} - This is a sample message.",
            "timestamp": ts.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "message_type": "text",
            "has_attachments": i % 7 == 0,  # Every 7th message has attachments
            "contact_name": contact_name,
            "phone_number": phone_number,
            "attachments": [{"type": "image", "filename": "photo.jpg"}] if i % 7 == 0 else []
        })
    return {"messages": items, "total": len(items)}


@app.get("/v1/messages/imessage/search")
async def search_imessage_messages(
    q: str = Query(..., description="Search query"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results to return"),
    context: Optional[str] = Query(None, description="Additional search context"),
):
    """Search iMessages by query or return demo data."""
    # Live mode: search in macOS Messages via AppleScript with caching
    if IMESSAGE_BRIDGE_MODE == "live":
        cache_key = f"imessage:search:{q}:{limit}:{context or 'None'}"
        
        # Try cache first
        cached_data = _get_cached_imessages(cache_key)
        if cached_data is not None:
            print(f"[bridge] returning cached iMessage search data for {cache_key}")
            return cached_data
        
        # Fetch live data asynchronously
        try:
            live_data = await _fetch_live_imessages_async("search", query=q, limit=limit, context=context)
            # Cache the result
            _cache_imessages(cache_key, live_data)
            print(f"[bridge] fetched and cached live iMessage search data for {cache_key}")
            return live_data
        except Exception as live_err:
            # Fall back to demo data on error
            print(f"[bridge] live iMessage search failed, falling back to demo: {live_err}")

    # Demo mode: generate search results that contain the query
    base_ts = datetime.now(timezone.utc)
    items = []
    for i in range(min(limit, 20)):  # Limit demo results
        ts = base_ts - timedelta(hours=i)
        contact_name = f"Search Contact {i + 1}"
        phone_number = f"+1-555-{(i % 9000) + 2000:04d}"
        
        items.append({
            "id": f"search-imessage-{i}",
            "thread_id": f"search-thread-{i % 5}",
            "from": contact_name if i % 2 == 0 else "Me",
            "to": "Me" if i % 2 == 0 else contact_name,
            "content": f"Demo search result #{i} containing '{q}' in the message content.",
            "timestamp": ts.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "message_type": "text",
            "has_attachments": i % 5 == 0,
            "contact_name": contact_name,
            "phone_number": phone_number,
            "attachments": [{"type": "image", "filename": "search_photo.jpg"}] if i % 5 == 0 else []
        })
    
    return {"results": items, "total": len(items), "query": q}


@app.get("/v1/messages/imessage/{message_id}")
async def get_imessage_message(message_id: str):
    """Get a specific iMessage by ID."""
    # Live mode: fetch from macOS Messages
    if IMESSAGE_BRIDGE_MODE == "live":
        try:
            # In a real implementation, we'd have a specific function to get a message by ID
            # For now, this is a placeholder that returns demo data
            pass
        except Exception as e:
            print(f"[bridge] error fetching iMessage {message_id}: {e}")
    
    # Demo mode or fallback: return demo message
    if message_id.startswith("imessage-") or message_id.startswith("search-imessage-"):
        ts = datetime.now(timezone.utc) - timedelta(hours=1)
        return {
            "id": message_id,
            "thread_id": f"thread-{message_id.split('-')[-1]}",
            "from": "Demo Contact",
            "to": "Me",
            "content": f"This is the full content of message {message_id}.",
            "timestamp": ts.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "message_type": "text",
            "has_attachments": False,
            "contact_name": "Demo Contact",
            "phone_number": "+1-555-DEMO",
            "attachments": []
        }
    
    return {"error": "iMessage not found"}


@app.get("/v1/messages/imessage/thread/{thread_id}")
async def get_imessage_thread(thread_id: str):
    """Get all messages in an iMessage thread."""
    # Live mode: fetch from macOS Messages
    if IMESSAGE_BRIDGE_MODE == "live":
        cache_key = f"imessage:thread:{thread_id}"
        
        # Try cache first
        cached_data = _get_cached_imessages(cache_key)
        if cached_data is not None:
            print(f"[bridge] returning cached iMessage thread data for {cache_key}")
            return cached_data
        
        # Fetch live data asynchronously
        try:
            live_data = await _fetch_live_imessages_async("read_thread", thread_id=thread_id)
            # Cache the result
            _cache_imessages(cache_key, live_data)
            print(f"[bridge] fetched and cached live iMessage thread data for {cache_key}")
            return live_data
        except Exception as live_err:
            print(f"[bridge] live iMessage thread fetch failed, falling back to demo: {live_err}")
    
    # Demo mode: return demo thread
    base_ts = datetime.now(timezone.utc)
    messages = []
    
    for i in range(5):  # 5 messages in the thread
        ts = base_ts - timedelta(minutes=30 * i)
        contact_name = f"Thread Contact"
        
        messages.append({
            "id": f"thread-msg-{thread_id}-{i}",
            "thread_id": thread_id,
            "from": contact_name if i % 2 == 0 else "Me",
            "to": "Me" if i % 2 == 0 else contact_name,
            "content": f"Thread message #{i} in conversation {thread_id}",
            "timestamp": ts.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "message_type": "text",
            "has_attachments": i == 2,  # One message has attachments
            "contact_name": contact_name,
            "phone_number": "+1-555-THREAD",
            "attachments": [{"type": "image", "filename": "thread_photo.jpg"}] if i == 2 else []
        })
    
    return {
        "thread_id": thread_id,
        "messages": messages,
        "thread_info": {
            "id": thread_id,
            "participants": ["Me", "Thread Contact"],
            "message_count": len(messages),
            "last_message": messages[0]["timestamp"] if messages else None
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5100)


