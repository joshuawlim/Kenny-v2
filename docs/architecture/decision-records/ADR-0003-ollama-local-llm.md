## ADR-0003: Local LLM via Ollama (host) + embeddings

### Status
Accepted

### Context
- Requirement: All AI inference should run locally on the Mac Mini (M4 Pro, 64 GB) with Metal acceleration.
- Developer workflow prefers Docker Compose for app services.

### Decision
- Run Ollama on the macOS host (not in Docker) and expose it at `http://localhost:11434` (reachable from containers via `http://host.docker.internal:11434`).
- Default models:
  - General LLM: `llama3.1:8b` (upgradeable later to 70b if needed).
  - Embeddings: `nomic-embed-text`.
- The Agent API and workers call Ollama’s HTTP API for generation and embeddings.

### Consequences
- Pros:
  - Uses Apple Metal effectively.
  - Keeps heavy model weights and GPU access on host, simplifying container images.
  - Easy model swaps and versioning with `ollama pull`.
- Cons:
  - Adds a host dependency outside Docker.
  - Requires network access from containers to `host.docker.internal`.

### Alternatives Considered
1) Containerize Ollama: less efficient on macOS for Metal; larger images.
2) Other local runtimes (text-generation-webui, llama.cpp raw): more manual setup.

### Implementation Notes
- Document `ollama pull llama3.1:8b` and `ollama pull nomic-embed-text` in README.
- Parameterize base URL via `OLLAMA_BASE_URL` env in services.


