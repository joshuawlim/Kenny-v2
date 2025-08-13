import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _run_jxa(script: str) -> str:
    """Run a JXA (JavaScript for Automation) script via osascript and return stdout.

    Raises RuntimeError on non-zero exit.
    """
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"osascript failed with code {result.returncode}")
    return result.stdout.strip()


def _build_fetch_script(mailbox_name: str, limit: int) -> str:
    """Build JXA script to fetch most recent messages for a given mailbox.

    The script returns a JSON string array with fields: id, from, to (array), subject, ts, snippet.
    """
    # Escape mailbox name for inclusion in JS string
    mbox = mailbox_name.replace("\\", "\\\\").replace("\"", "\\\"")
    # JXA script
    return f"""
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;

    const Mail = Application('Mail');

    function getMailboxMessages(name) {{
      const lower = String(name || '').toLowerCase();
      try {{
        if (lower === 'inbox') {{
          return Mail.inbox().messages();
        }}
        if (lower === 'sent' || lower === 'sent mailbox' || lower === 'sent messages') {{
          if (typeof Mail.sentMailbox === 'function') {{
            return Mail.sentMailbox().messages();
          }}
        }}
        // Generic lookup by name across top-level mailboxes
        const boxes = Mail.mailboxes.whose({{ name: name }})();
        if (boxes && boxes.length > 0) {{
          return boxes[0].messages();
        }}
      }} catch (e) {{
        // Fall through to inbox
      }}
      return Mail.inbox().messages();
    }}

    function toJs(msg) {{
      function safe(fn, dflt) {{
        try {{ return fn(); }} catch (e) {{ return dflt; }}
      }}
      const fromVal = safe(() => msg.sender(), '');
      const subjectVal = safe(() => msg.subject(), '');
      const dateVal = safe(() => msg.dateReceived ? msg.dateReceived() : (msg.dateSent ? msg.dateSent() : new Date()), new Date());
      const idVal = safe(() => String(msg.id()), '');
      let toList = [];
      try {{
        const recips = msg.toRecipients ? msg.toRecipients() : (msg.recipients ? msg.recipients() : []);
        toList = (recips || []).map(r => {{
          try {{ return r.address ? r.address() : String(r); }} catch (e) {{ return String(r); }}
        }});
      }} catch (e) {{ toList = []; }}
      const snippet = subjectVal ? subjectVal.substring(0, 120) : '';
      return {{ id: idVal, from: fromVal, to: toList, subject: subjectVal, ts: new Date(dateVal).toISOString(), snippet }};
    }}

    const msgs = getMailboxMessages("{mbox}");
    // Sort desc by date if possible
    let arr = [];
    try {{
      arr = msgs.map(m => toJs(m));
      arr.sort((a, b) => (new Date(b.ts).getTime()) - (new Date(a.ts).getTime()));
    }} catch (e) {{
      arr = [];
    }}

    const out = arr.slice(0, {int(limit)});
    JSON.stringify(out);
    """


def _iso_to_datetime_or_none(value: Optional[str]):
    if not value:
        return None
    try:
        v = value.replace("Z", "+00:00")
        return datetime.fromisoformat(v)
    except Exception:
        return None


def fetch_mail_messages(mailbox: str, since_iso: Optional[str], limit: int, page: int) -> List[Dict[str, Any]]:
    """Fetch messages from Apple Mail for a mailbox.

    - mailbox: name like "Inbox" or "Sent"
    - since_iso: ISO8601 string (UTC Z) to filter messages newer than this
    - limit: max number to return
    - page: 0-based page; implemented via slicing after sort
    """
    # Run JXA to get a recent batch (we'll over-fetch to allow paging + since filtering)
    overfetch = max(limit * (page + 1), limit * 3)
    script = _build_fetch_script(mailbox_name=mailbox, limit=overfetch)
    raw = _run_jxa(script)
    try:
        items = json.loads(raw or "[]")
        if not isinstance(items, list):
            raise ValueError("JXA returned non-list")
    except Exception as parse_err:
        raise RuntimeError(f"Failed to parse JXA output: {parse_err}")

    # Normalize and filter
    since_dt = _iso_to_datetime_or_none(since_iso)
    normalized: List[Dict[str, Any]] = []
    for it in items:
        try:
            ts = it.get("ts")
            ts_dt = _iso_to_datetime_or_none(ts) or datetime.now(timezone.utc)
            if since_dt and ts_dt <= since_dt:
                continue
            normalized.append(
                {
                    "id": str(it.get("id", "")),
                    "thread_id": None,
                    "from": str(it.get("from", "")),
                    "to": list(it.get("to", []) or []),
                    "subject": it.get("subject"),
                    "ts": ts_dt.astimezone(timezone.utc)
                    .replace(microsecond=0)
                    .isoformat()
                    .replace("+00:00", "Z"),
                    "snippet": it.get("snippet"),
                }
            )
        except Exception:
            # Skip malformed entries
            continue

    # Ensure stable sort by ts desc
    normalized.sort(key=lambda x: x.get("ts", ""), reverse=True)

    # Paging
    start_index = page * limit
    end_index = start_index + limit
    return normalized[start_index:end_index]


