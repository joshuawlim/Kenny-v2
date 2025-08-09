from datetime import datetime, timedelta
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Kenny Bridge Stub", version="0.1.0")


class MailMessage(BaseModel):
    id: str
    thread_id: Optional[str] = None
    from_: str
    to: List[str] = []
    subject: Optional[str] = None
    ts: str
    snippet: Optional[str] = None

    class Config:
        fields = {"from_": "from"}


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
    # Generate deterministic fake data for demo
    try:
        since_dt = datetime.fromisoformat((since or "").replace("Z", "+00:00"))
    except Exception:
        since_dt = datetime.utcnow() - timedelta(days=30)

    base_ts = datetime.utcnow()
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
                "ts": ts.replace(microsecond=0).isoformat() + "Z",
                "snippet": "This is a demo snippet.",
            }
        )
    return items


