# Contacts Agent

Contact management and enrichment agent for the Kenny v2 multi-agent system.

## Overview

The Contacts Agent provides intelligent contact management capabilities including:
- **Contact Resolution**: Find and disambiguate contacts by email, phone, or name
- **Contact Enrichment**: Add additional information from various sources
- **Contact Merging**: Merge duplicate contacts with conflict resolution
- **Local Database Management**: SQLite3 database for comprehensive contact storage
- **Mac Contacts Integration**: Ongoing sync with local Contacts.app
- **Message Analysis**: Extract contact information from iMessage and WhatsApp
- **Human Approval Workflow**: All modifications require explicit human approval

## Capabilities

### `contacts.resolve`
Resolve contacts by identifier with fuzzy matching support.

**Input**:
- `identifier` (required): Email, phone, or name to resolve
- `platform` (optional): Platform context for resolution
- `fuzzy_match` (optional): Enable fuzzy name matching (default: true)

**Output**:
- `contacts`: Array of resolved contacts with confidence scores
- `resolved_count`: Number of contacts found

### `contacts.enrich`
Enrich contact information from various sources.

**Input**:
- `contact_id` (required): Contact ID to enrich
- `enrichment_type` (required): Type of enrichment (job_title, interests, relationships, interaction_history)
- `source_platform` (optional): Platform providing enrichment data

**Output**:
- `contact_id`: The enriched contact ID
- `enrichments`: Array of enrichment objects with confidence and source
- `enrichment_count`: Number of enrichments added

### `contacts.merge`
Merge duplicate contacts with conflict resolution.

**Input**:
- `primary_contact_id` (required): Primary contact to keep
- `duplicate_contact_ids` (required): Array of duplicate contact IDs to merge
- `merge_strategy` (optional): How to handle conflicts (merge_all, selective, manual)

**Output**:
- `merged_contact_id`: New merged contact ID
- `merged_attributes`: Combined contact attributes
- `merged_count`: Total number of contacts merged
- `conflicts_resolved`: Number of conflicts resolved

## Quick Start

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start the agent
python -m uvicorn src.main:app --port 8003
```

### Docker
```bash
# Build the image
docker build -t contacts-agent .

# Run the container
docker run -p 8003:8003 contacts-agent
```

### Environment Variables
- `CONTACTS_AGENT_PORT`: Port to run on (default: 8003)
- `AGENT_REGISTRY_URL`: Agent registry URL (default: http://localhost:8001)
- `CONTACTS_DB_PATH`: Database path (default: ~/Library/Application Support/Kenny/contacts.db)
- `CONTACTS_BACKUP_PATH`: Backup directory (default: ~/Library/Application Support/Kenny/backups)
- `CONTACTS_SYNC_INTERVAL`: Mac Contacts sync interval in minutes (default: 60)
- `CONTACTS_BACKUP_INTERVAL`: Backup interval in hours (default: 168 - weekly)

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check
- `GET /agent/info` - Agent manifest and capabilities
- `POST /capabilities/contacts.resolve` - Resolve contacts
- `POST /capabilities/contacts.enrich` - Enrich contacts
- `POST /capabilities/contacts.merge` - Merge contacts

## Testing

### Unit Tests
```bash
# Run tests
python -m pytest tests/ -v
```

### Integration Tests
```bash
# Test contact resolution
curl -X POST http://localhost:8003/capabilities/contacts.resolve \
  -H "Content-Type: application/json" \
  -d '{"input": {"identifier": "john.doe@example.com"}}'

# Test contact enrichment
curl -X POST http://localhost:8003/capabilities/contacts.enrich \
  -H "Content-Type: application/json" \
  -d '{"input": {"contact_id": "contact-001", "enrichment_type": "job_title"}}'

# Test contact merging
curl -X POST http://localhost:8003/capabilities/contacts.merge \
  -H "Content-Type: application/json" \
  -d '{"input": {"primary_contact_id": "contact-001", "duplicate_contact_ids": ["contact-002"]}}'
```

## Architecture

The Contacts Agent follows the Kenny v2 agent architecture:

- **BaseAgent**: Inherits from the Agent SDK base class
- **Capability Handlers**: Implement specific capabilities (resolve, enrich, merge)
- **Tools**: Integrate with external services (macOS bridge, database)
- **Health Monitoring**: Built-in health checks and monitoring
- **Registry Integration**: Automatic registration with the agent registry

## Data Sources

The agent integrates with multiple data sources for comprehensive contact management:

- **Local SQLite Database**: Primary storage in `~/Library/Application Support/Kenny/contacts.db`
- **Mac Contacts.app**: Ongoing sync with local Contacts database
- **iMessage**: Full message content analysis for contact enrichment
- **WhatsApp**: Message content analysis for contact information
- **Apple Mail**: Email content analysis for contact details
- **Calendar Events**: Relationship and event information

## Development Status

- ✅ **Phase 1.2**: Basic agent structure and capabilities
- 🔄 **Current**: Mock data implementation for testing
- 📋 **Next**: Local SQLite database implementation
- 📋 **Future**: Mac Contacts integration and message analysis
- 📋 **Integration**: Human approval workflow via Coordinator

## Dependencies

- FastAPI: Web framework
- Uvicorn: ASGI server
- Pydantic: Data validation
- httpx: HTTP client
- Agent SDK: Base agent functionality
- SQLite3: Local database storage
- Apple Contacts Framework: Mac Contacts integration

## Database & Storage

### Database Location
The contacts database is stored locally at:
```
~/Library/Application Support/Kenny/contacts.db
```

### Database Schema
- **contacts**: Core contact information with deep enrichment
- **contact_relationships**: Relationship mapping between contacts
- **contact_enrichments**: Extracted information from messages
- **contact_sync_log**: Sync operations with Mac Contacts

### Backup & Recovery
- **Backup Schedule**: Weekly automatic backup
- **Recovery Point Objective (RPO)**: 1 week
- **Backup Retention**: 1 backup maintained
- **Location**: Local backup directory (configurable)

## Workflow

### New Person Detection
1. System analyzes incoming messages for new persons
2. Checks against existing contacts database
3. Presents new person to Coordinator for human approval
4. Creates contact after approval with extracted information

### Contact Enrichment
1. Analyzes message content for contact information
2. Extracts occupations, interests, relationships, events
3. Assigns confidence scores to extracted information
4. Presents enrichment suggestions for human approval
5. Updates contact database after approval

### Human Approval
All contact modifications require explicit human approval via the Coordinator:
- New contact creation
- Contact merging and deduplication
- Information enrichment and updates
- Relationship modifications

## Contributing

1. Follow the Kenny v2 development patterns
2. Add tests for new capabilities
3. Update documentation for API changes
4. Ensure all tests pass before submitting

## License

Part of the Kenny v2 project - see project root for license information.
