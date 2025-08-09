# ADR-0008: Establish Contacts Knowledge Base module

Date: 2025-08-09
Status: Proposed

## Context
Personalized assistance requires a local, structured view of contacts and relationships, with privacy-preserving storage and querying.

## Decision
- Introduce a Contacts Knowledge Base module responsible for ingesting contact info from approved channels and providing query APIs to other modules.
- Store data locally; avoid third-party sync unless explicitly allowlisted.

## Consequences
- Enables smarter context in approvals and recommendations.
- Requires data model alignment and minimal APIs.

## References
- diagrams/data.mmd
