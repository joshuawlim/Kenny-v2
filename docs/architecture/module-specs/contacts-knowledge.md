# Contacts Knowledge Base Module Specification

## Overview
Contacts knowledge base module provides unified contact management across all platforms (Mail, WhatsApp, iMessage) with intelligent deduplication and relationship mapping.

## Design Decisions
- **Unified storage**: Per ADR-0008, single source of truth for all contacts
- **Local-first**: All contact data stored locally, no cloud sync
- **Intelligent deduplication**: Merge contacts across platforms based on multiple identifiers
- **Privacy-focused**: No external contact sharing or synchronization

## Interface
```python
class ContactsKnowledge:
    def add_contact(self, contact: Contact) -> str
    def find_contact(self, identifier: str) -> Optional[Contact]
    def merge_contacts(self, contact_ids: List[str]) -> str
    def get_relationships(self, contact_id: str) -> List[Relationship]
    def update_contact(self, contact_id: str, updates: Dict) -> None
```

## Data Model
- `Contact`: id, name, emails, phones, platforms, created_at, updated_at
- `ContactPlatform`: contact_id, platform, external_id, last_seen
- `Relationship`: contact_id, related_contact_id, relationship_type, strength
- `Interaction`: contact_id, platform, message_count, last_interaction

## Deduplication Strategy
1. **Exact match**: Email addresses, phone numbers
2. **Fuzzy match**: Names with high similarity scores
3. **Platform correlation**: Same external ID across platforms
4. **Manual merge**: User-initiated contact consolidation

## Platform Integration
- **Apple Mail**: Extract from email headers and contacts
- **WhatsApp**: Parse from message metadata and contact list
- **iMessage**: Extract from message participants
- **Calendar**: Parse from event attendees

## Privacy & Security
- **Local storage**: No cloud backup of contact data
- **Access control**: Only Kenny persona can access contact information
- **Audit logging**: Track all contact data access and modifications
- **Data retention**: Respect user preferences for contact cleanup

## Performance
- **Indexing**: Fast lookup by email, phone, and name
- **Caching**: Frequently accessed contact information
- **Batch operations**: Efficient bulk contact updates
