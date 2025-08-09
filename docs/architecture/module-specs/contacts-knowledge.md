## Module Spec: Contacts Knowledge Base

### Purpose
Maintain enriched contact profiles (occupation, relationships, birthdays, interests) with provenance and confidence.

### Scope (MVP)
- Enrich from messages/emails (NER via LLM) and user edits.
- Dedupe and merge into canonical contacts.

### Flow
1) ETL extracts candidate facts from recent messages/emails.
2) Normalize and propose `contact_enrichment` entries with confidence and source.
3) On user confirmation, merge into `contacts` fields or maintain as structured enrichment with provenance.

### Data
- `contact_relations(person_id, related_person_id, relation_type)`
- `contact_enrichment(contact_id, attribute, value, confidence, source_id, created_at)`
- `knowledge_sources(id, source_type, source_ref, extracted_at)`

### UI
- Contact detail page shows enriched attributes with source and confidence; quick approve/edit controls.


