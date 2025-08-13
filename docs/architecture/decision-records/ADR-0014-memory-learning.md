## ADR-0014: Memory and learning to improve importance detection and proposals

### Status
Accepted

### Context
- Requirement: Kenny should "learn" over time to better identify important messages/emails, detect meeting requests, and propose good calendar events.
- Constraint: Local-first; no cloud training. Learning must rely on local data and lightweight techniques.

### Decision
- Implement a lightweight, privacy-preserving learning loop:
  - Capture user feedback signals (e.g., approve/reject proposals, mark message important, snooze, ignore).
  - Store labeled examples locally and reuse them as few-shot exemplars for LLM prompting and as heuristics.
  - Maintain per-user tunables/thresholds for classifier prompts (e.g., confidence thresholds) and persist improvements.
- Prefer prompt+heuristics over training custom models for MVP. Revisit local fine-tuning/distillation later if needed.

### Consequences
- Pros: Fast to implement, fully local, directly aligned with approvals workflow.
- Cons: Improvements are incremental and depend on good feedback capture.

### Implementation Notes
- Data model: add `message_labels`, `feedback_events`, and `model_prompts` (versioned prompt templates) plus `prompt_exemplars`.
- Learning loop: nightly job curates exemplars from high-confidence and human-validated items (diversity by contact/channel).
- Safety: store only local data; expose an option to purge exemplars and reset.
