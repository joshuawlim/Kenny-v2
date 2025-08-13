# Contacts Knowledge Base Module Specification

## Overview
Contacts knowledge base module provides unified contact management across all platforms (Mail, WhatsApp, iMessage) with intelligent deduplication, relationship mapping, and deep contact enrichment. The system maintains a local SQLite database that serves as a "second brain" for contact information, helping users be better friends and family members.

## Design Decisions
- **Unified storage**: Per ADR-0008, single source of truth for all contacts
- **Local-first**: All contact data stored locally, no cloud sync
- **Intelligent deduplication**: Merge contacts across platforms based on multiple identifiers
- **Privacy-focused**: No external contact sharing or synchronization
- **Deep enrichment**: Extract and store comprehensive contact information from messages
- **Human approval**: All contact modifications require explicit human approval
- **Soft deletion**: No hard deletion of contacts without explicit approval

## Interface
```python
class ContactsKnowledge:
    def add_contact(self, contact: Contact) -> str
    def find_contact(self, identifier: str) -> Optional[Contact]
    def merge_contacts(self, contact_ids: List[str]) -> str
    def get_relationships(self, contact_id: str) -> List[Relationship]
    def update_contact(self, contact_id: str, updates: Dict) -> None
    def sync_with_mac_contacts(self) -> SyncResult
    def detect_new_persons(self, message: Message) -> List[PersonDetection]
    def enrich_contact_from_message(self, contact_id: str, message: Message) -> List[Enrichment]
    def suggest_duplicates(self, contact_data: Dict) -> List[DuplicateSuggestion]
    def request_human_approval(self, action: ContactAction) -> ApprovalRequest
```

## Data Model
- `Contact`: id, name, emails, phones, job_title, company, occupation, interests, family_members, events, notes, created_at, updated_at, last_synced, is_deleted
- `ContactRelationship`: contact_id, related_contact_id, relationship_type, relationship_details, strength, source_platform, source_message_id, confidence
- `ContactEnrichment`: contact_id, enrichment_type, enrichment_value, source_platform, source_message_id, confidence, extraction_method
- `ContactSyncLog`: sync_type, contacts_processed, contacts_added, contacts_updated, contacts_deleted, sync_started_at, sync_completed_at, status
- `PersonDetection`: identifier, confidence, source_message, suggested_contact_data, duplicate_suggestions

## Deduplication Strategy
1. **Exact match**: Email addresses, phone numbers
2. **Fuzzy match**: Names with high similarity scores (suggestions only)
3. **Platform correlation**: Same external ID across platforms
4. **Human approval**: All merges require explicit human approval
5. **Soft deletion**: No hard deletion without explicit approval
6. **Duplicate suggestions**: Present potential duplicates for human review

## Platform Integration
- **Apple Mail**: Extract from email headers and full message content
- **WhatsApp**: Parse from message metadata, contact list, and full message content
- **iMessage**: Extract from message participants and full message content
- **Calendar**: Parse from event attendees and event details
- **Mac Contacts**: Ongoing sync with local Contacts.app database

## Privacy & Security
- **Local storage**: No cloud backup of contact data
- **Access control**: Only Kenny persona can access contact information
- **Audit logging**: Track all contact data access and modifications
- **Data retention**: Respect user preferences for contact cleanup
- **Human approval**: All contact modifications require explicit approval
- **Soft deletion**: No hard deletion without explicit approval
- **Database location**: Stored in user's Application Support directory
- **Backup**: Weekly backup with 1-week RPO

## Performance
- **Indexing**: Fast lookup by email, phone, and name
- **Caching**: Frequently accessed contact information
- **Batch operations**: Efficient bulk contact updates
- **Message analysis**: LLM-powered content analysis for enrichment
- **Sync optimization**: Incremental sync with Mac Contacts
- **Database optimization**: SQLite with proper indexing and FTS

## Workflow

### New Person Detection
1. **Message Analysis**: Analyze incoming messages for new persons
2. **Duplicate Check**: Check against existing contacts database
3. **Human Approval**: Present new person to Coordinator for human approval
4. **Contact Creation**: Create contact after human approval
5. **Enrichment**: Extract additional information from message content

### Contact Enrichment
1. **Message Processing**: Analyze message content for contact information
2. **Information Extraction**: Extract occupations, interests, relationships, events
3. **Confidence Scoring**: Assign confidence scores to extracted information
4. **Human Review**: Present enrichment suggestions for human approval
5. **Database Update**: Update contact after human approval

### Mac Contacts Sync
1. **Incremental Sync**: Check for changes in Mac Contacts.app
2. **Conflict Detection**: Identify conflicts between local and Mac data
3. **Human Resolution**: Present conflicts for human resolution
4. **Database Update**: Update local database after resolution
5. **Sync Logging**: Log all sync operations for audit trail

### Human Approval Workflow
1. **Action Request**: System identifies action needed (new contact, merge, enrichment)
2. **Context Presentation**: Present full context and suggested data
3. **Duplicate Suggestions**: Show potential duplicates for human review
4. **Approval Collection**: Collect human approval via Coordinator
5. **Action Execution**: Execute approved action
6. **Audit Trail**: Log all actions for compliance
