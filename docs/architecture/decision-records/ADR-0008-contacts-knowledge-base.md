# ADR-0008: Establish Contacts Knowledge Base module

Date: 2025-08-09
Status: Superseded by ADR-0016

## Context
Personalized assistance requires a local, structured view of contacts and relationships, with privacy-preserving storage and querying.

## Decision
- Introduce a Contacts Knowledge Base module responsible for ingesting contact info from approved channels and providing query APIs to other modules.
- Store data locally; avoid third-party sync unless explicitly allowlisted.

## Consequences
- Enables smarter context in approvals and recommendations.
- Requires data model alignment and minimal APIs.

## Supersession
- This ADR is superseded by ADR-0016, which defines the accepted schema extensions, provenance, and UI considerations.

## References
- diagrams/data.mmd
