# Data Model (MVP)

Scope focuses on unifying messages across iMessage, WhatsApp, and Apple Mail, plus contacts and calendar. Email scope: Inbox and Sent only (MVP).


## Tables


### contacts
- `id` TEXT PRIMARY KEY (UUIDv7 generated locally)
- `external_id` TEXT NULL (e.g., CNContact identifier)
- `name` TEXT NOT NULL
- `phones` TEXT NOT NULL (JSON array)
- `emails` TEXT NOT NULL (JSON array)
- `job_title` TEXT NULL
- `interests` TEXT NULL (JSON array of strings)
- `source_app` TEXT NOT NULL (e.g., "Contacts.framework")
- `updated_at` TEXT NOT NULL (ISO8601)

Indexes:
- `idx_contacts_name` on (`name`)


### messages
Represents messages from multiple platforms, including email as a message type.

- `id` INTEGER PRIMARY KEY AUTOINCREMENT
- `platform` TEXT NOT NULL CHECK (platform IN ('imessage','whatsapp','mail'))
- `external_id` TEXT NOT NULL -- stable id from source (e.g., Apple Mail message id, chat.db rowid, WA DOM-derived id)
- `thread_external_id` TEXT NULL -- source thread/conversation id
- `mailbox` TEXT NULL -- 'Inbox'|'Sent' for platform='mail'
- `sender_id` TEXT NULL -- contact id or raw address
- `recipient_ids` TEXT NULL -- JSON array of contact ids or raw addresses
- `subject` TEXT NULL -- mail only
- `content_snippet` TEXT NULL -- short preview
- `content_body` TEXT NULL -- optional, only when fetched on-demand (recent mail)
- `has_attachments` INTEGER NOT NULL DEFAULT 0
- `source_message_id` TEXT NULL -- original source id when applicable
- `ts` TEXT NOT NULL -- ISO8601 timestamp
- `is_outgoing` INTEGER NOT NULL DEFAULT 0
- `source_app` TEXT NOT NULL -- 'Apple Mail' | 'Messages' | 'WhatsApp Web'
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601
- `is_agent_channel` INTEGER NOT NULL DEFAULT 0 -- 1 if this record belongs to an agent conversation (should be 0 in MVP)
- `exclude_from_automation` INTEGER NOT NULL DEFAULT 0 -- 1 to exclude from triage/insights

Constraints & Indexes:
- UNIQUE (`platform`,`external_id`)
- `idx_messages_ts` on (`platform`,`ts`)
- `idx_messages_thread` on (`platform`,`thread_external_id`)
- `idx_messages_mailbox_ts` on (`mailbox`,`ts`) WHERE platform='mail'

Optional FTS (SQLite FTS5):
```sql
CREATE VIRTUAL TABLE messages_fts USING fts5(
  subject, content,
  content='messages', content_rowid='id'
);
-- Triggers to sync FTS table on insert/update/delete can be added in migration scripts.
```

#### events
- `id` TEXT PRIMARY KEY (UUIDv7)
- `title` TEXT NOT NULL
- `start` TEXT NOT NULL (ISO8601)
- `end` TEXT NOT NULL (ISO8601)
- `attendees` TEXT NULL (JSON array)
- `source_app` TEXT NOT NULL
- `updated_at` TEXT NOT NULL


### proposals
- `id` TEXT PRIMARY KEY (UUIDv7)
- `type` TEXT NOT NULL CHECK (type IN ('calendar_event'))
- `source_message_id` INTEGER NOT NULL REFERENCES messages(id)
- `title` TEXT NOT NULL
- `start` TEXT NOT NULL
- `end` TEXT NOT NULL
- `attendees` TEXT NULL (JSON array)
- `notes` TEXT NULL
- `confidence` REAL NULL
- `status` TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')) DEFAULT 'pending'
- `result_ref` TEXT NULL -- created event id
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL


### sync_state
Stores cursors/checkpoints for incremental ETL.
- `source` TEXT PRIMARY KEY -- e.g., 'mail:Inbox', 'mail:Sent'
- `cursor` TEXT NULL -- ISO8601 timestamp or source-specific token
- `updated_at` TEXT NOT NULL

#### insights (optional MVP)
- `id` TEXT PRIMARY KEY
- `message_id` INTEGER NOT NULL REFERENCES messages(id)
- `priority` INTEGER NULL
- `suggested_action` TEXT NULL
- `created_at` TEXT NOT NULL

#### message_labels
- `message_id` INTEGER NOT NULL REFERENCES messages(id)
- `label` TEXT NOT NULL CHECK (label IN ('important','actionable','meeting_request','ignore'))
- `confidence` REAL NOT NULL
- `source` TEXT NOT NULL CHECK (source IN ('model','user'))
- `created_at` TEXT NOT NULL

#### feedback_events
- `id` TEXT PRIMARY KEY (UUIDv7)
- `item_type` TEXT NOT NULL CHECK (item_type IN ('message','proposal'))
- `item_id` TEXT NOT NULL
- `action` TEXT NOT NULL CHECK (action IN ('approve','reject','mark_important','snooze','ignore'))
- `created_at` TEXT NOT NULL

#### model_prompts
- `name` TEXT NOT NULL
- `version` TEXT NOT NULL
- `template` TEXT NOT NULL
- `created_at` TEXT NOT NULL

#### prompt_exemplars
- `prompt_name` TEXT NOT NULL
- `example_json` TEXT NOT NULL
- `created_at` TEXT NOT NULL

#### contact_relations
- `person_id` TEXT NOT NULL REFERENCES contacts(id)
- `related_person_id` TEXT NOT NULL REFERENCES contacts(id)
- `relation_type` TEXT NOT NULL -- e.g., spouse, child, manager

#### contact_enrichment
- `contact_id` TEXT NOT NULL REFERENCES contacts(id)
- `attribute` TEXT NOT NULL -- e.g., occupation, birthday, interest
- `value` TEXT NOT NULL
- `confidence` REAL NOT NULL
- `source_id` TEXT NOT NULL REFERENCES knowledge_sources(id)
- `created_at` TEXT NOT NULL

#### knowledge_sources
- `id` TEXT PRIMARY KEY (UUIDv7)
- `source_type` TEXT NOT NULL -- e.g., email, message, manual
- `source_ref` TEXT NOT NULL -- e.g., message_id
- `extracted_at` TEXT NOT NULL

#### web_entries
- `id` TEXT PRIMARY KEY (UUIDv7)
- `site` TEXT NOT NULL
- `url` TEXT NOT NULL
- `title` TEXT NULL
- `published_at` TEXT NULL
- `content_text` TEXT NOT NULL
- `extracted_at` TEXT NOT NULL
- `source_snapshot_path` TEXT NULL

#### sync_runs
- `id` TEXT PRIMARY KEY (UUIDv7)
- `source` TEXT NOT NULL -- e.g., imessage, mail:Inbox, mail:Sent, whatsapp
- `started_at` TEXT NOT NULL
- `ended_at` TEXT NULL
- `status` TEXT NOT NULL CHECK (status IN ('success','error','partial'))
- `items_fetched` INTEGER NOT NULL DEFAULT 0
- `errors` INTEGER NOT NULL DEFAULT 0

#### metrics_counters_daily
- `date` TEXT NOT NULL -- YYYY-MM-DD
- `name` TEXT NOT NULL -- e.g., messages_analyzed_total, proposals_created_total
- `value` INTEGER NOT NULL DEFAULT 0
- PRIMARY KEY (`date`,`name`)

### Media and Extractions (Postgres)

> These tables live in Postgres to support richer metadata and future job orchestration. Links to `messages` are enforced in the application layer (cross-store).

#### attachments
- `id` TEXT PRIMARY KEY (UUIDv7)
- `message_id` INTEGER NOT NULL -- references `messages.id` (app-enforced cross-store)
- `source` TEXT NOT NULL CHECK (source IN ('whatsapp'))
- `media_type` TEXT NOT NULL -- e.g., 'image/jpeg','image/png'
- `file_path` TEXT NOT NULL -- local filesystem path
- `checksum` TEXT NOT NULL -- sha256
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_attachments_message` on (`message_id`)

#### extractions
- `id` TEXT PRIMARY KEY (UUIDv7)
- `attachment_id` TEXT NOT NULL -- references attachments(id)
- `extractor` TEXT NOT NULL -- e.g., 'tesseract','opencv-qr','vision-ocr'
- `text` TEXT NULL
- `confidence` REAL NULL
- `provenance` TEXT NULL -- JSON (bounding boxes, languages, model/version)
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_extractions_attachment` on (`attachment_id`)

### Retention & Privacy
- Email bodies are stored only when explicitly needed for summarization/classification and limited to a recent time window (e.g., last 30 days).
- WhatsApp image attachments are stored locally on disk with checksums; processing/extraction is opt-in and disabled by default.
- Add configurable retention knobs for optional future cleanup of old `agent_messages`, embeddings, and attachments.


### agent_conversations
- `id` TEXT PRIMARY KEY (UUIDv7)
- `created_at` TEXT NOT NULL


### agent_messages
- `id` TEXT PRIMARY KEY (UUIDv7)
- `conversation_id` TEXT NOT NULL REFERENCES agent_conversations(id)
- `role` TEXT NOT NULL CHECK (role IN ('user','assistant'))
- `content` TEXT NOT NULL
- `created_at` TEXT NOT NULL

Optional FTS (SQLite FTS5) for chat search:
```sql
CREATE VIRTUAL TABLE agent_messages_fts USING fts5(
  content,
  content='agent_messages', content_rowid='id'
);
```

### Embeddings (vectors.db)
- `embeddings`
  - `id` INTEGER PRIMARY KEY
  - `source_table` TEXT NOT NULL CHECK (source_table IN ('messages','agent_messages'))
  - `source_id` INTEGER/TEXT NOT NULL
  - `vector` VSS_VECTOR NOT NULL
  - `model` TEXT NOT NULL
  - `created_at` TEXT NOT NULL
  - Unique on (`source_table`,`source_id`,`model`)



