import express from 'express';
import { openDatabase } from './db.js';

const app = express();
app.use(express.json());

// In-memory state. Persisted to container lifetime only.
const state = {
  killSwitchEnabled: false,
  auditEvents: [],
  components: {
    api: { healthy: true },
    ollama: { healthy: false },
    bridge: { healthy: false },
    workers: { healthy: false },
  }
};

function recordAudit(event) {
  const entry = { timestamp: new Date().toISOString(), ...event };
  state.auditEvents.unshift(entry);
  state.auditEvents = state.auditEvents.slice(0, 500);
}

// Health
app.get('/healthz', (req, res) => {
  res.json({ status: 'ok' });
});

// Status with components, audit, and kill switch
app.get('/api/status', (req, res) => {
  res.json({
    components: state.components,
    killSwitchEnabled: state.killSwitchEnabled,
    audit: state.auditEvents,
  });
});

// Kill switch toggle
app.post('/api/kill-switch', (req, res) => {
  const { enabled } = req.body || {};
  state.killSwitchEnabled = Boolean(enabled);
  recordAudit({ type: 'kill_switch', enabled: state.killSwitchEnabled });
  res.json({ ok: true, enabled: state.killSwitchEnabled });
});

// Egress-audit endpoint for workers/UI to record allowlisted checks
app.post('/api/audit', (req, res) => {
  const { type = 'egress', target, allowed } = req.body || {};
  recordAudit({ type, target, allowed: Boolean(allowed) });
  res.json({ ok: true });
});

// Endpoint workers can poll to know if they should pause
app.get('/api/kill-switch', (req, res) => {
  res.json({ enabled: state.killSwitchEnabled });
});

// --- Mail ETL (read-only, Inbox/Sent) ---
let dbPromise;
async function getDb() {
  if (!dbPromise) dbPromise = openDatabase();
  return dbPromise;
}

async function upsertMessage(db, msg) {
  const now = new Date().toISOString();
  await db.run(
    `INSERT INTO messages (
      platform, external_id, thread_external_id, mailbox, sender_id, recipient_ids,
      subject, content_snippet, content_body, ts, is_outgoing, source_app,
      created_at, updated_at, is_agent_channel, exclude_from_automation
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    ON CONFLICT(platform, external_id) DO UPDATE SET
      thread_external_id=excluded.thread_external_id,
      mailbox=excluded.mailbox,
      sender_id=excluded.sender_id,
      recipient_ids=excluded.recipient_ids,
      subject=excluded.subject,
      content_snippet=excluded.content_snippet,
      ts=excluded.ts,
      is_outgoing=excluded.is_outgoing,
      source_app=excluded.source_app,
      updated_at=excluded.updated_at`,
    [
      'mail', msg.id, msg.thread_id ?? null, msg.mailbox ?? null, msg.from ?? null,
      JSON.stringify(msg.to ?? []), msg.subject ?? null, msg.snippet ?? null, null,
      msg.ts, msg.is_outgoing ? 1 : 0, 'Apple Mail', now, now, 0, 0,
    ]
  );
}

async function fetchBridge(path) {
  const base = process.env.MAC_BRIDGE_URL || 'http://host.docker.internal:5100';
  const url = `${base}${path}`;
  try {
    const r = await fetch(url);
    recordAudit({ type: 'egress', target: url, allowed: true });
    if (!r.ok) throw new Error(`bridge_http_${r.status}`);
    return await r.json();
  } catch (e) {
    recordAudit({ type: 'egress', target: url, allowed: false });
    throw e;
  }
}

app.post('/api/sync/mail', async (req, res) => {
  if (state.killSwitchEnabled) return res.status(423).json({ error: 'kill_switch_enabled' });
  const mailbox = (req.query.mailbox || 'Inbox').toString();
  if (!['Inbox', 'Sent'].includes(mailbox)) return res.status(400).json({ error: 'invalid_mailbox' });
  const db = await getDb();
  const nowIso = new Date().toISOString();
  await db.run('INSERT INTO sync_state(source, cursor, updated_at) VALUES(?,?,?) ON CONFLICT(source) DO NOTHING', [`mail:${mailbox}`, null, nowIso]);
  const row = await db.get('SELECT cursor FROM sync_state WHERE source=?', `mail:${mailbox}`);
  const since = row?.cursor || new Date(Date.now() - 30 * 24 * 3600 * 1000).toISOString();
  let total = 0;
  try {
    let page = 0;
    while (true) {
      const limit = 200;
      const items = await fetchBridge(`/v1/mail/messages?mailbox=${encodeURIComponent(mailbox)}&since=${encodeURIComponent(since)}&limit=${limit}&page=${page}`);
      if (!Array.isArray(items) || items.length === 0) break;
      for (const m of items) {
        await upsertMessage(db, {
          id: m.id, thread_id: m.thread_id, mailbox,
          from: m.from, to: m.to || [], subject: m.subject, snippet: m.snippet,
          ts: m.ts || m.date || new Date().toISOString(), is_outgoing: mailbox === 'Sent'
        });
      }
      total += items.length;
      page += 1;
      if (items.length < limit) break;
    }
    await db.run('UPDATE sync_state SET cursor=?, updated_at=? WHERE source=?', [nowIso, nowIso, `mail:${mailbox}`]);
    res.json({ ok: true, mailbox, upserts: total });
  } catch (e) {
    res.status(502).json({ error: 'bridge_unavailable' });
  }
});

app.get('/api/messages', async (req, res) => {
  const db = await getDb();
  const days = Math.max(1, Math.min(60, Number(req.query.sinceDays ?? 30)));
  const since = new Date(Date.now() - days * 24 * 3600 * 1000).toISOString();
  const rows = await db.all(
    `SELECT id, platform, mailbox, sender_id, recipient_ids, subject, content_snippet, ts, is_outgoing
     FROM messages WHERE platform='mail' AND ts >= ?
     ORDER BY ts DESC LIMIT 500`,
    since
  );
  res.json(rows.map(r => ({
    id: r.id,
    mailbox: r.mailbox,
    from: r.sender_id,
    to: JSON.parse(r.recipient_ids || '[]'),
    subject: r.subject,
    snippet: r.content_snippet,
    ts: r.ts,
    is_outgoing: !!r.is_outgoing
  })));
});

const port = process.env.PORT || 80;
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`API listening on ${port}`);
});


