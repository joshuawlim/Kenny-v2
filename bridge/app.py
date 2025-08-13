import os
from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI(title="Kenny Bridge", version="0.2.0")

# Bridge mode: "demo" (default) or "live"
BRIDGE_MODE = os.getenv("MAIL_BRIDGE_MODE", "demo").strip().lower()


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


@app.get("/v1/mail/messages")
def mail_messages(
    mailbox: str = Query("Inbox"),
    since: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    page: int = Query(0, ge=0),
):
    # Live mode: fetch from Apple Mail via AppleScript
    if BRIDGE_MODE == "live":
        try:
            from mail_live import fetch_mail_messages

            return fetch_mail_messages(mailbox=mailbox, since_iso=since, limit=limit, page=page)
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


