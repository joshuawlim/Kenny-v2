## Module Spec: Whitelisted Website Access

### Purpose
Fetch and parse information from a small set of approved websites to improve planning (e.g., school calendars, announcements).

### Scope (MVP)
- Headless browser worker (Playwright) with domain allowlist.
- Session/login support per site; local session storage.
- Periodic fetch; parse to normalized entries.

### HTTP/API
- Worker internal; exposes `/health` and metrics. Results land in `web_entries` table.

### Data
- `web_entries`:
  - `id` TEXT PK
  - `site` TEXT
  - `url` TEXT
  - `title` TEXT
  - `published_at` TEXT NULL
  - `content_text` TEXT
  - `extracted_at` TEXT
  - `source_snapshot_path` TEXT NULL

### Config
- `WHITELISTED_SITES="https://parent.school1.com,https://parent.school2.com"`
- `EGRESS_ALLOWLIST` includes the same domains.
- Credentials via macOS Keychain preferred; or env vars like `SITE1_USERNAME`, `SITE1_PASSWORD`.


