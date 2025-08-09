## Module Spec: Memory & Learning

### Purpose
Improve importance detection and proposal quality over time using local feedback and exemplars.

### Scope (MVP)
- Capture feedback from approvals and message actions.
- Curate exemplars for classifier prompts and heuristics.
- Adjustable thresholds per user.

### Flow
1) Collect signals: approvals (approve/reject), mark-important, snooze, ignore.
2) Persist `feedback_events` and derive `message_labels`.
3) Nightly curator job selects diverse, high-quality examples into `prompt_exemplars`.
4) Classifier prompts include exemplars; thresholds tuned from recent performance metrics.

### Data
- `message_labels(message_id, label, confidence, source, created_at)`
- `feedback_events(item_type, item_id, action, created_at)`
- `model_prompts(name, version, template, created_at)`
- `prompt_exemplars(prompt_name, example_json, created_at)`

### Config
- `LEARNING_ENABLED=true`
- `LEARNING_CURATE_DAILY_HOUR=02:00`


