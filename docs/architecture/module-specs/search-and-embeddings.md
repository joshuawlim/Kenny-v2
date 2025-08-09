## Module Spec: Local Search and Embeddings

### Purpose
Enable fast semantic and keyword search over local messages and agent chat using embeddings and SQLite FTS/VSS, fully local.

### Scope (MVP)
- Embed and index `messages.content_snippet` (and `subject` for mail) and `agent_messages.content`.
- Provide hybrid search: keyword (FTS) + semantic (VSS) reranking.
- Prepare interface to include `extractions.text` as a searchable source once image processing is enabled (later sprint).

### Models
- Embeddings: `nomic-embed-text` via Ollama (configurable). Vector dimension per model (e.g., 768) recorded in metadata.
 - Vision models are optional and deferred; any future use must be local-only and explicitly enabled.

### Data Stores
- Primary: `agent.db` (SQLite) for canonical records.
- Vector: `vectors.db` (SQLite with `sqlite-vss`) for embeddings.

### Ingestion & Consistency
1) On upsert to `messages`/`agent_messages`, enqueue embedding job.
2) Job computes embedding via `OLLAMA_BASE_URL` and writes to `vectors.db` with `{ source_table, source_id, vector, ts }`.
3) Best-effort dedupe on `{ source_table, source_id }`. Periodic reconciliation detects orphans and re-embeds if the model changed.

### Query Flow
1) Accept query text; compute query embedding.
2) Retrieve top-K by cosine similarity from VSS.
3) Retrieve top-K keyword matches from FTS.
4) Merge and rerank; return results with source references.

### Configuration
- `EMBEDDINGS_MODEL=nomic-embed-text`
- `EMBEDDINGS_DIM=768` (example; auto-detected at startup if not set)
- `SEARCH_TOPK_VSS=50`, `SEARCH_TOPK_FTS=50`, `SEARCH_TOPK_FINAL=20`

### Metrics
- `embeddings_jobs_enqueued/succeeded/failed`
- `search_latency_ms{mode=vss|fts|hybrid}`

### Operational Notes
- Record current embedding model/version in a metadata table; trigger re-embed when changed.
- Backoff on Ollama timeouts; cache query embeddings per session to reduce latency.


