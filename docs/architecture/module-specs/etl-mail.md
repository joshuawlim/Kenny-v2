# Mail ETL Module Specification

## Overview
Mail ETL module handles ingestion of Apple Mail data (Inbox & Sent folders) with read-only access and 30-day scan window enforcement.

## Design Decisions
- **Read-only access**: Per ADR-0004, only read operations on Apple Mail
- **Scope limitation**: Inbox and Sent folders only (ADR-0005)
- **Time window**: 30-day scan window enforced (ADR-0006)
- **Local processing**: No cloud egress; data processed locally

## Interface
```python
class MailETL:
    def sync_inbox_sent(self) -> SyncResult
    def get_messages(self, folder: str, limit: int = 100) -> List[Message]
    def enforce_scan_window(self, messages: List[Message]) -> List[Message]
```

## Data Model
- `Message`: id, subject, sender, recipient, body, timestamp, folder, read_status
- `SyncResult`: count, timestamp, status, error_details

## Error Handling
- Graceful degradation when Mail.app unavailable
- Retry logic with exponential backoff
- Audit logging for sync operations

## Security
- No persistent storage of mail credentials
- Local-only processing per security posture
- Audit trail for all sync operations


