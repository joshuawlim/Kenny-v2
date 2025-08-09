import express from 'express';

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

const port = process.env.PORT || 80;
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`API listening on ${port}`);
});


