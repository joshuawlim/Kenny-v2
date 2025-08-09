import sqlite3 from 'sqlite3';
import { open } from 'sqlite';

function resolveSqlitePath(dbUrl) {
  if (!dbUrl || !dbUrl.startsWith('sqlite:')) return '/data/agent.db';
  return dbUrl.replace('sqlite:', '');
}

export async function openDatabase() {
  const filename = resolveSqlitePath(process.env.DB_URL);
  const db = await open({ filename, driver: sqlite3.Database });
  await db.exec(`
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      platform TEXT NOT NULL,
      external_id TEXT NOT NULL,
      thread_external_id TEXT NULL,
      mailbox TEXT NULL,
      sender_id TEXT NULL,
      recipient_ids TEXT NULL,
      subject TEXT NULL,
      content_snippet TEXT NULL,
      content_body TEXT NULL,
      ts TEXT NOT NULL,
      is_outgoing INTEGER NOT NULL DEFAULT 0,
      source_app TEXT NOT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      is_agent_channel INTEGER NOT NULL DEFAULT 0,
      exclude_from_automation INTEGER NOT NULL DEFAULT 0,
      UNIQUE(platform, external_id)
    );
    CREATE TABLE IF NOT EXISTS sync_state (
      source TEXT PRIMARY KEY,
      cursor TEXT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(platform, ts);
    CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(platform, thread_external_id);
    CREATE INDEX IF NOT EXISTS idx_messages_mailbox_ts ON messages(mailbox, ts);
  `);
  return db;
}


