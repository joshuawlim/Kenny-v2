import fetch from 'node-fetch';

const apiBase = process.env.API_BASE_URL || 'http://api';
const pollIntervalMs = 5000;

async function shouldPause() {
  try {
    const res = await fetch(`${apiBase}/api/kill-switch`);
    const body = await res.json();
    return Boolean(body.enabled);
  } catch (e) {
    return false;
  }
}

async function recordEgress(target, allowed) {
  try {
    await fetch(`${apiBase}/api/audit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type: 'egress', target, allowed })
    });
  } catch (_) {
    // ignore
  }
}

async function mainLoop() {
  // No-op worker loop that respects kill switch and only touches allowlisted URLs by design
  while (true) {
    const paused = await shouldPause();
    if (paused) {
      await new Promise(r => setTimeout(r, pollIntervalMs));
      continue;
    }
    // In Sprint 1, we do not ingest yet. We can still report that we would talk to allowlisted endpoints.
    await recordEgress('http://host.docker.internal:11434', true);
    await recordEgress('http://host.docker.internal:5100', true);
    await new Promise(r => setTimeout(r, pollIntervalMs));
  }
}

mainLoop().catch(err => {
  // eslint-disable-next-line no-console
  console.error('Worker crashed', err);
  process.exit(1);
});


