import express from 'express';

const app = express();
app.use(express.json());

const apiBase = process.env.API_BASE_URL || 'http://proxy';

function htmlPage(body) {
  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kenny · Status</title>
  <style>
    body { font-family: -apple-system, system-ui, sans-serif; margin: 2rem; color: #0a0a0a; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    .row { display: flex; gap: 1rem; }
    .col { flex: 1; }
    code { background: #f9fafb; padding: 2px 4px; border-radius: 4px; }
    button { padding: 0.5rem 0.75rem; border-radius: 6px; border: 1px solid #d1d5db; background: white; cursor: pointer; }
  </style>
  <script>
    const apiBase = '${apiBase}'.replace(/\/$/, '');
    async function refresh() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('kill').textContent = data.killSwitchEnabled ? 'On' : 'Off';
      const list = document.getElementById('audit');
      list.innerHTML = '';
      (data.audit || []).forEach(e => {
        const li = document.createElement('li');
        li.textContent = '[' + e.timestamp + '] ' + e.type + (e.target ? (' ' + e.target) : '') + (e.allowed !== undefined ? (' allowed=' + e.allowed) : '');
        list.appendChild(li);
      });
      const comps = document.getElementById('components');
      comps.innerHTML = '';
      Object.entries(data.components || {}).forEach(([k, v]) => {
        const li = document.createElement('li');
        li.textContent = k + ': ' + (v.healthy ? 'healthy' : 'unknown');
        comps.appendChild(li);
      });
    }
    async function toggleKill() {
      const current = document.getElementById('kill').textContent === 'On';
      const res = await fetch('/api/kill-switch', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ enabled: !current }) });
      const json = await res.json();
      await refresh();
    }
    window.addEventListener('load', refresh);
  </script>
</head>
<body>
  <h1>Kenny · Local Status</h1>

  <div class="card">
    <h2>Components</h2>
    <ul id="components"></ul>
  </div>

  <div class="card">
    <h2>Kill switch: <span id="kill">Off</span></h2>
    <button onclick="toggleKill()">Toggle</button>
  </div>

  <div class="card">
    <h2>Egress audit (allowlist transparency)</h2>
    <ul id="audit"></ul>
  </div>

  <p style="color:#6b7280;font-size:12px">Local-first. No cloud egress beyond allowlist. Future approvals default to WhatsApp when writes are introduced.</p>
</body>
</html>`;
}

// Server-side proxy for API to avoid CORS and let Caddy route to api service
app.get('/api/status', async (_req, res) => {
  try {
    const r = await fetch(`${apiBase}/api/status`);
    const j = await r.json();
    res.json(j);
  } catch (e) {
    res.status(500).json({ error: 'api_unreachable' });
  }
});

app.post('/api/kill-switch', async (req, res) => {
  try {
    const r = await fetch(`${apiBase}/api/kill-switch`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req.body || {}) });
    const j = await r.json();
    res.json(j);
  } catch (e) {
    res.status(500).json({ error: 'api_unreachable' });
  }
});

app.get('/', (_req, res) => {
  res.setHeader('Content-Type', 'text/html');
  res.send(htmlPage(''));
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  // eslint-disable-next-line no-console
  console.log(`UI listening on ${port}`);
});


