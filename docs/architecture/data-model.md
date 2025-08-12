# Data Model (Multi-Agent Architecture)

Scope focuses on unifying messages across iMessage, WhatsApp, and Apple Mail, plus contacts and calendar, now organized through a coordinator-led multi-agent system. Email scope: Inbox and Sent only (MVP).

## Core Data Tables

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

### events
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

## Multi-Agent Architecture Tables

### agent_manifests
Stores agent capability registrations with the Agent Registry.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `agent_id` TEXT NOT NULL UNIQUE -- e.g., 'mail-agent', 'whatsapp-agent'
- `version` TEXT NOT NULL -- semver format
- `display_name` TEXT NOT NULL -- human-readable name
- `description` TEXT NULL
- `manifest_json` TEXT NOT NULL -- full agent manifest JSON
- `status` TEXT NOT NULL CHECK (status IN ('active','inactive','error')) DEFAULT 'active'
- `last_heartbeat` TEXT NULL -- ISO8601 timestamp
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_agent_manifests_status` on (`status`)
- `idx_agent_manifests_heartbeat` on (`last_heartbeat`)

### agent_capabilities
Individual capabilities provided by agents.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `agent_id` TEXT NOT NULL REFERENCES agent_manifests(agent_id)
- `verb` TEXT NOT NULL -- e.g., 'messages.search', 'calendar.propose_event'
- `input_schema` TEXT NOT NULL -- JSON Schema for inputs
- `output_schema` TEXT NOT NULL -- JSON Schema for outputs
- `safety_annotations` TEXT NOT NULL -- JSON array of safety flags
- `sla_json` TEXT NULL -- SLA parameters as JSON
- `description` TEXT NULL
- `is_active` INTEGER NOT NULL DEFAULT 1
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601

Constraints & Indexes:
- UNIQUE (`agent_id`, `verb`)
- `idx_agent_capabilities_verb` on (`verb`)
- `idx_agent_capabilities_active` on (`is_active`)

### agent_health
Health status and metrics for each agent.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `agent_id` TEXT NOT NULL REFERENCES agent_manifests(agent_id)
- `status` TEXT NOT NULL CHECK (status IN ('healthy','degraded','unhealthy','unknown'))
- `last_check` TEXT NOT NULL -- ISO8601 timestamp
- `response_time_ms` INTEGER NULL -- last health check response time
- `error_count` INTEGER NOT NULL DEFAULT 0 -- consecutive errors
- `last_error` TEXT NULL -- last error message
- `metrics_json` TEXT NULL -- additional health metrics as JSON
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_agent_health_status` on (`status`)
- `idx_agent_health_last_check` on (`last_check`)

## Coordination and Execution Tables

### agent_requests
Tracks incoming requests and their routing through the coordinator.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `request_id` TEXT NOT NULL UNIQUE -- external request identifier
- `session_id` TEXT NULL -- user session identifier
- `user_id` TEXT NULL -- user identifier
- `intent` TEXT NOT NULL -- classified user intent
- `status` TEXT NOT NULL CHECK (status IN ('pending','routing','executing','completed','failed','cancelled'))
- `priority` INTEGER NOT NULL DEFAULT 5 -- 1=high, 10=low
- `step_budget` INTEGER NOT NULL DEFAULT 10 -- maximum coordination steps
- `timeout_seconds` INTEGER NOT NULL DEFAULT 300 -- request timeout
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601
- `completed_at` TEXT NULL -- ISO8601

Indexes:
- `idx_agent_requests_status` on (`status`)
- `idx_agent_requests_session` on (`session_id`)
- `idx_agent_requests_created` on (`created_at`)

### task_dags
Directed Acyclic Graph representation of multi-agent task execution.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `request_id` TEXT NOT NULL REFERENCES agent_requests(id)
- `dag_json` TEXT NOT NULL -- JSON representation of the task DAG
- `current_step` TEXT NULL -- current execution step identifier
- `status` TEXT NOT NULL CHECK (status IN ('planned','executing','completed','failed','cancelled'))
- `execution_path` TEXT NULL -- JSON array of completed step IDs
- `error_details` TEXT NULL -- error information if failed
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_task_dags_request` on (`request_id`)
- `idx_task_dags_status` on (`status`)

### execution_traces
Detailed execution trace for each request and step.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `request_id` TEXT NOT NULL REFERENCES agent_requests(id)
- `step_id` TEXT NOT NULL -- step identifier within the DAG
- `agent_id` TEXT NOT NULL REFERENCES agent_manifests(agent_id)
- `capability_verb` TEXT NOT NULL -- capability being executed
- `input_data` TEXT NULL -- input data sent to agent (may be redacted for PII)
- `output_data` TEXT NULL -- output data from agent (may be redacted for PII)
- `execution_time_ms` INTEGER NULL -- step execution time
- `status` TEXT NOT NULL CHECK (status IN ('success','error','timeout'))
- `error_message` TEXT NULL -- error details if failed
- `policy_context` TEXT NULL -- policy context during execution
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_execution_traces_request` on (`request_id`)
- `idx_execution_traces_step` on (`step_id`)
- `idx_execution_traces_agent` on (`agent_id`)

## Policy and Security Tables

### policy_contexts
Policy context for request execution and agent access control.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `request_id` TEXT NOT NULL REFERENCES agent_requests(id)
- `user_id` TEXT NULL -- user identifier
- `data_scopes` TEXT NOT NULL -- JSON array of allowed data scopes
- `egress_domains` TEXT NOT NULL -- JSON array of allowed external domains
- `pii_sensitivity` TEXT NOT NULL CHECK (pii_sensitivity IN ('low','medium','high')) DEFAULT 'medium'
- `approval_required` INTEGER NOT NULL DEFAULT 0 -- 1 if explicit approval needed
- `retention_policy` TEXT NULL -- data retention policy as JSON
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_policy_contexts_request` on (`request_id`)
- `idx_policy_contexts_user` on (`user_id`)

### approval_workflows
Tracks approval workflows for operations requiring user consent.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `request_id` TEXT NOT NULL REFERENCES agent_requests(id)
- `step_id` TEXT NOT NULL -- step requiring approval
- `operation_type` TEXT NOT NULL -- e.g., 'calendar.write_event', 'whatsapp.send_message'
- `operation_data` TEXT NOT NULL -- operation details as JSON
- `approval_channel` TEXT NOT NULL -- 'web_chat', 'whatsapp', 'telegram', 'imessage'
- `status` TEXT NOT NULL CHECK (status IN ('pending','approved','rejected','expired'))
- `requested_at` TEXT NOT NULL -- ISO8601
- `responded_at` TEXT NULL -- ISO8601
- `responded_by` TEXT NULL -- user identifier
- `response_notes` TEXT NULL -- approval/rejection notes
- `expires_at` TEXT NOT NULL -- ISO8601 timestamp

Indexes:
- `idx_approval_workflows_status` on (`status`)
- `idx_approval_workflows_channel` on (`approval_channel`)
- `idx_approval_workflows_expires` on (`expires_at`)

### egress_logs
Audit trail for all external network requests.

- `id` TEXT PRIMARY KEY (UUIDv7)
- `request_id` TEXT NULL REFERENCES agent_requests(id)
- `agent_id` TEXT NOT NULL REFERENCES agent_manifests(agent_id)
- `domain` TEXT NOT NULL -- external domain accessed
- `endpoint` TEXT NOT NULL -- specific endpoint
- `method` TEXT NOT NULL -- HTTP method
- `status_code` INTEGER NULL -- HTTP response status
- `response_time_ms` INTEGER NULL -- response time
- `data_size_bytes` INTEGER NULL -- request/response data size
- `policy_allowed` INTEGER NOT NULL -- 1 if policy allowed, 0 if blocked
- `error_message` TEXT NULL -- error details if failed
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_egress_logs_domain` on (`domain`)
- `idx_egress_logs_agent` on (`agent_id`)
- `idx_egress_logs_created` on (`created_at`)

## Legacy Tables (Maintained for Backward Compatibility)

### sync_state
Stores cursors/checkpoints for incremental ETL.
- `source` TEXT PRIMARY KEY -- e.g., 'mail:Inbox', 'mail:Sent'
- `cursor` TEXT NULL -- ISO8601 timestamp or source-specific token
- `updated_at` TEXT NOT NULL

### insights (optional MVP)
- `id` TEXT PRIMARY KEY
- `message_id` INTEGER NOT NULL REFERENCES messages(id)
- `priority` INTEGER NULL
- `suggested_action` TEXT NULL
- `created_at` TEXT NOT NULL

### message_labels
- `message_id` INTEGER NOT NULL REFERENCES messages(id)
- `label` TEXT NOT NULL CHECK (label IN ('important','actionable','meeting_request','ignore'))
- `confidence` REAL NOT NULL
- `source` TEXT NOT NULL CHECK (source IN ('model','user'))
- `created_at` TEXT NOT NULL

### feedback_events
- `id` TEXT PRIMARY KEY (UUIDv7)
- `item_type` TEXT NOT NULL CHECK (item_type IN ('message','proposal'))
- `item_id` TEXT NOT NULL
- `action` TEXT NOT NULL CHECK (action IN ('approve','reject','mark_important','snooze','ignore'))
- `created_at` TEXT NOT NULL

### model_prompts
- `name` TEXT NOT NULL
- `version` TEXT NOT NULL
- `template` TEXT NOT NULL
- `created_at` TEXT NOT NULL

### prompt_exemplars
- `prompt_name` TEXT NOT NULL
- `example_json` TEXT NOT NULL
- `created_at` TEXT NOT NULL

### contact_relations
- `person_id` TEXT NOT NULL REFERENCES contacts(id)
- `related_person_id` TEXT NOT NULL REFERENCES contacts(id)
- `relation_type` TEXT NOT NULL -- e.g., spouse, child, manager

### contact_enrichment
- `contact_id` TEXT NOT NULL REFERENCES contacts(id)
- `attribute` TEXT NOT NULL -- e.g., occupation, birthday, interest
- `value` TEXT NOT NULL
- `confidence` REAL NOT NULL
- `source_id` TEXT NOT NULL REFERENCES knowledge_sources(id)
- `created_at` TEXT NOT NULL

### knowledge_sources
- `id` TEXT PRIMARY KEY (UUIDv7)
- `source_type` TEXT NOT NULL -- e.g., email, message, manual
- `source_ref` TEXT NOT NULL -- e.g., message_id
- `extracted_at` TEXT NOT NULL

### web_entries
- `id` TEXT PRIMARY KEY (UUIDv7)
- `site` TEXT NOT NULL
- `url` TEXT NOT NULL
- `title` TEXT NULL
- `published_at` TEXT NULL
- `content_text` TEXT NOT NULL
- `extracted_at` TEXT NOT NULL
- `source_snapshot_path` TEXT NULL

### sync_runs
- `id` TEXT PRIMARY KEY (UUIDv7)
- `source` TEXT NOT NULL -- e.g., imessage, mail:Inbox, mail:Sent, whatsapp
- `started_at` TEXT NOT NULL
- `ended_at` TEXT NULL
- `status` TEXT NOT NULL CHECK (status IN ('success','error','partial'))
- `items_fetched` INTEGER NOT NULL DEFAULT 0
- `errors` INTEGER NOT NULL DEFAULT 0

### metrics_counters_daily
- `date` TEXT NOT NULL -- YYYY-MM-DD
- `name` TEXT NOT NULL -- e.g., messages_analyzed_total, proposals_created_total
- `value` INTEGER NOT NULL DEFAULT 0
- PRIMARY KEY (`date`,`name`)

## Media and Extractions (Postgres)

> These tables live in Postgres to support richer metadata and future job orchestration. Links to `messages` are enforced in the application layer (cross-store).

### attachments
- `id` TEXT PRIMARY KEY (UUIDv7)
- `message_id` INTEGER NOT NULL -- references `messages.id` (app-enforced cross-store)
- `source` TEXT NOT NULL CHECK (source IN ('whatsapp'))
- `media_type` TEXT NOT NULL -- e.g., 'image/jpeg','image/png'
- `file_path` TEXT NOT NULL -- local filesystem path
- `checksum` TEXT NOT NULL -- sha256
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_attachments_message` on (`message_id`)

### extractions
- `id` TEXT PRIMARY KEY (UUIDv7)
- `attachment_id` TEXT NOT NULL -- references attachments(id)
- `extractor` TEXT NOT NULL -- e.g., 'tesseract','opencv-qr','vision-ocr'
- `text` TEXT NULL
- `confidence` REAL NULL
- `provenance` TEXT NULL -- JSON (bounding boxes, languages, model/version)
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_extractions_attachment` on (`attachment_id`)

## Agent Conversation and Memory Tables

### agent_conversations
- `id` TEXT PRIMARY KEY (UUIDv7)
- `session_id` TEXT NULL -- user session identifier
- `request_id` TEXT NULL REFERENCES agent_requests(id)
- `conversation_type` TEXT NOT NULL CHECK (conversation_type IN ('user_chat','agent_coordination','system_log'))
- `status` TEXT NOT NULL CHECK (status IN ('active','completed','archived'))
- `created_at` TEXT NOT NULL -- ISO8601
- `updated_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_agent_conversations_session` on (`session_id`)
- `idx_agent_conversations_type` on (`conversation_type`)

### agent_messages
- `id` TEXT PRIMARY KEY (UUIDv7)
- `conversation_id` TEXT NOT NULL REFERENCES agent_conversations(id)
- `role` TEXT NOT NULL CHECK (role IN ('user','assistant','system','agent'))
- `agent_id` TEXT NULL REFERENCES agent_manifests(agent_id) -- if role='agent'
- `content` TEXT NOT NULL
- `metadata_json` TEXT NULL -- additional message metadata
- `created_at` TEXT NOT NULL -- ISO8601

Indexes:
- `idx_agent_messages_conversation` on (`conversation_id`)
- `idx_agent_messages_role` on (`role`)
- `idx_agent_messages_agent` on (`agent_id`)

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
  - `source_table` TEXT NOT NULL CHECK (source_table IN ('messages','agent_messages','contacts','web_entries'))
  - `source_id` INTEGER/TEXT NOT NULL
  - `vector` VSS_VECTOR NOT NULL
  - `model` TEXT NOT NULL
  - `created_at` TEXT NOT NULL
  - Unique on (`source_table`,`source_id`,`model`)

## Data Retention & Privacy

### Retention Policies
- **Agent Data**: Agent manifests and capabilities retained indefinitely for system operation
- **Execution Traces**: Retained for 90 days for debugging and audit purposes
- **Policy Contexts**: Retained for 30 days after request completion
- **Egress Logs**: Retained for 180 days for security audit
- **User Conversations**: Retained per user preference (default: 1 year)

### Privacy Controls
- **PII Handling**: Input/output data in execution traces may be redacted based on PII sensitivity level
- **Local Processing**: All embeddings and analysis done locally with Ollama
- **Approval Workflows**: Explicit user consent required for any write operations
- **Data Scoping**: Agents access only data within their declared scopes

### Security Features
- **Egress Controls**: Network level egress blocking with coordinator whitelisting
- **Agent Isolation**: Agents operate with least privilege access
- **Audit Trails**: Comprehensive logging of all operations and policy decisions
- **Policy Enforcement**: Runtime policy validation for all agent operations
