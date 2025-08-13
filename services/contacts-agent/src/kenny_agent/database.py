"""
SQLite database implementation for Contacts Agent.

Provides local contact storage at ~/Library/Application Support/Kenny/contacts.db
following the data model specifications.
"""

import sqlite3
import os
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class ContactsDatabase:
    """SQLite database for contacts management."""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize the contacts database.
        
        Args:
            db_path: Optional custom database path. Defaults to Kenny app support directory.
        """
        if db_path is None:
            # Use the path specified in roadmap
            app_support = Path.home() / "Library" / "Application Support" / "Kenny"
            app_support.mkdir(parents=True, exist_ok=True)
            self.db_path = str(app_support / "contacts.db")
        else:
            self.db_path = db_path
        
        self._connection = None
        self._initialize_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection, creating if needed."""
        if self._connection is None:
            self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self._connection.row_factory = sqlite3.Row  # Enable dict-like access
            # Enable WAL mode for better concurrency
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection
    
    def _initialize_database(self):
        """Initialize database with contacts schema from data-model.md."""
        conn = self._get_connection()
        
        # Create contacts table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                external_id TEXT NULL,
                name TEXT NOT NULL,
                phones TEXT NOT NULL,
                emails TEXT NOT NULL,
                job_title TEXT NULL,
                company TEXT NULL,
                occupation TEXT NULL,
                interests TEXT NULL,
                family_members TEXT NULL,
                events TEXT NULL,
                notes TEXT NULL,
                source_app TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_synced TEXT NULL,
                is_deleted INTEGER NOT NULL DEFAULT 0
            )
        ''')
        
        # Create contact_enrichments table  
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contact_enrichments (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL,
                enrichment_type TEXT NOT NULL,
                enrichment_value TEXT NOT NULL,
                source_platform TEXT NOT NULL,
                source_message_id INTEGER NULL,
                confidence REAL NOT NULL,
                extraction_method TEXT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contacts(id)
            )
        ''')
        
        # Create contact_relationships table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contact_relationships (
                id TEXT PRIMARY KEY,
                contact_id TEXT NOT NULL,
                related_contact_id TEXT NULL,
                relationship_type TEXT NOT NULL,
                relationship_details TEXT NULL,
                strength REAL NULL,
                source_platform TEXT NOT NULL,
                source_message_id INTEGER NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (contact_id) REFERENCES contacts(id),
                FOREIGN KEY (related_contact_id) REFERENCES contacts(id)
            )
        ''')
        
        # Create contact_sync_log table
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contact_sync_log (
                id TEXT PRIMARY KEY,
                sync_type TEXT NOT NULL,
                contacts_processed INTEGER NOT NULL DEFAULT 0,
                contacts_added INTEGER NOT NULL DEFAULT 0,
                contacts_updated INTEGER NOT NULL DEFAULT 0,
                contacts_deleted INTEGER NOT NULL DEFAULT 0,
                sync_started_at TEXT NOT NULL,
                sync_completed_at TEXT NULL,
                status TEXT NOT NULL,
                error_message TEXT NULL,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Create indexes
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_external_id ON contacts(external_id)')  
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contacts_last_synced ON contacts(last_synced)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contact_enrichments_contact_id ON contact_enrichments(contact_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contact_enrichments_type ON contact_enrichments(enrichment_type)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contact_relationships_contact_id ON contact_relationships(contact_id)')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_contact_sync_log_status ON contact_sync_log(status)')
        
        conn.commit()
        logger.info(f"Database initialized at {self.db_path}")
    
    def get_contact_by_id(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact by ID."""
        conn = self._get_connection()
        cursor = conn.execute('SELECT * FROM contacts WHERE id = ? AND is_deleted = 0', (contact_id,))
        row = cursor.fetchone()
        if row:
            return self._row_to_contact_dict(row)
        return None
    
    def search_contacts(self, identifier: str, platform: Optional[str] = None, fuzzy_match: bool = True) -> List[Dict[str, Any]]:
        """Search for contacts by identifier (email, phone, name)."""
        conn = self._get_connection()
        contacts = []
        
        # Search by email (exact match in JSON array)
        if "@" in identifier:
            cursor = conn.execute(
                "SELECT * FROM contacts WHERE emails LIKE ? AND is_deleted = 0",
                (f'%"{identifier}"%',)
            )
            contacts.extend([self._row_to_contact_dict(row) for row in cursor.fetchall()])
        
        # Search by phone (exact match in JSON array)  
        elif any(c.isdigit() for c in identifier):
            cursor = conn.execute(
                "SELECT * FROM contacts WHERE phones LIKE ? AND is_deleted = 0",
                (f'%"{identifier}"%',)
            )
            contacts.extend([self._row_to_contact_dict(row) for row in cursor.fetchall()])
        
        # Search by name
        if fuzzy_match:
            cursor = conn.execute(
                "SELECT * FROM contacts WHERE name LIKE ? AND is_deleted = 0",
                (f'%{identifier}%',)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM contacts WHERE name = ? AND is_deleted = 0",
                (identifier,)
            )
        contacts.extend([self._row_to_contact_dict(row) for row in cursor.fetchall()])
        
        # Remove duplicates and add confidence scores
        unique_contacts = {}
        for contact in contacts:
            contact_id = contact['id']
            if contact_id not in unique_contacts:
                contact['confidence'] = self._calculate_confidence(contact, identifier)
                unique_contacts[contact_id] = contact
        
        return list(unique_contacts.values())
    
    def create_contact(self, name: str, emails: List[str] = None, phones: List[str] = None, 
                      source_app: str = "contacts-agent", **kwargs) -> str:
        """Create a new contact."""
        contact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        conn.execute('''
            INSERT INTO contacts (
                id, name, emails, phones, source_app, created_at, updated_at,
                external_id, job_title, company, occupation, interests, 
                family_members, events, notes, last_synced, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            contact_id, name,
            json.dumps(emails or []),
            json.dumps(phones or []),
            source_app, now, now,
            kwargs.get('external_id'),
            kwargs.get('job_title'), 
            kwargs.get('company'),
            kwargs.get('occupation'),
            json.dumps(kwargs.get('interests', [])),
            json.dumps(kwargs.get('family_members', [])),
            json.dumps(kwargs.get('events', [])),
            kwargs.get('notes'),
            kwargs.get('last_synced'),
            0
        ))
        conn.commit()
        
        logger.info(f"Created contact {contact_id}: {name}")
        return contact_id
    
    def add_enrichment(self, contact_id: str, enrichment_type: str, enrichment_value: str,
                      source_platform: str, confidence: float, **kwargs) -> str:
        """Add enrichment data for a contact."""
        enrichment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        conn = self._get_connection()
        conn.execute('''
            INSERT INTO contact_enrichments (
                id, contact_id, enrichment_type, enrichment_value, source_platform,
                source_message_id, confidence, extraction_method, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            enrichment_id, contact_id, enrichment_type, enrichment_value, source_platform,
            kwargs.get('source_message_id'), confidence, kwargs.get('extraction_method'),
            now, now
        ))
        conn.commit()
        
        logger.info(f"Added enrichment {enrichment_type} for contact {contact_id}")
        return enrichment_id
    
    def get_contact_enrichments(self, contact_id: str, enrichment_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get enrichments for a contact."""
        conn = self._get_connection()
        
        if enrichment_type:
            cursor = conn.execute(
                "SELECT * FROM contact_enrichments WHERE contact_id = ? AND enrichment_type = ?",
                (contact_id, enrichment_type)
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM contact_enrichments WHERE contact_id = ?",
                (contact_id,)
            )
        
        return [dict(row) for row in cursor.fetchall()]
    
    def close(self):
        """Close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def _row_to_contact_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert SQLite row to contact dictionary."""
        contact = dict(row)
        
        # Parse JSON fields
        try:
            contact['emails'] = json.loads(contact['emails']) if contact['emails'] else []
            contact['phones'] = json.loads(contact['phones']) if contact['phones'] else []
            contact['interests'] = json.loads(contact['interests']) if contact['interests'] else []
            contact['family_members'] = json.loads(contact['family_members']) if contact['family_members'] else []
            contact['events'] = json.loads(contact['events']) if contact['events'] else []
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON fields for contact {contact.get('id')}: {e}")
        
        return contact
    
    def _calculate_confidence(self, contact: Dict[str, Any], identifier: str) -> float:
        """Calculate confidence score for contact match."""
        # Simple confidence scoring - can be enhanced
        name = contact.get('name', '').lower()
        identifier_lower = identifier.lower()
        
        if identifier_lower == name:
            return 1.0
        elif identifier_lower in name or name in identifier_lower:
            return 0.85
        elif "@" in identifier and any(identifier in email for email in contact.get('emails', [])):
            return 0.95
        elif any(c.isdigit() for c in identifier) and any(identifier in phone for phone in contact.get('phones', [])):
            return 0.90
        else:
            return 0.70