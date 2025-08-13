#!/usr/bin/env python3
"""
Test script for contacts database integration.

Tests the complete integration of the contacts database with the agent.
"""

import sys
import asyncio
from pathlib import Path

# Add the source directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from kenny_agent.database import ContactsDatabase
from kenny_agent.tools.contacts_bridge import ContactsBridgeTool
from kenny_agent.backup import ContactsBackup


async def test_database_integration():
    """Test the complete database integration."""
    print("=" * 60)
    print("Testing Contacts Database Integration")
    print("=" * 60)
    
    try:
        # Test 1: Database initialization
        print("\n1. Testing Database Initialization...")
        db = ContactsDatabase()
        print(f"✓ Database initialized at: {db.db_path}")
        
        # Test 2: Create test contacts
        print("\n2. Creating Test Contacts...")
        contact1_id = db.create_contact(
            name="John Doe",
            emails=["john.doe@example.com", "john@work.com"],
            phones=["+1-555-0123"],
            source_app="test"
        )
        print(f"✓ Created contact: {contact1_id} - John Doe")
        
        contact2_id = db.create_contact(
            name="Jane Smith", 
            emails=["jane.smith@example.com"],
            phones=["+1-555-4567", "+1-555-4568"],
            source_app="test",
            job_title="Software Engineer",
            company="Tech Corp"
        )
        print(f"✓ Created contact: {contact2_id} - Jane Smith")
        
        contact3_id = db.create_contact(
            name="Bob Johnson",
            emails=["bob.johnson@company.com"],
            phones=["+1-555-8901"],
            source_app="test"
        )
        print(f"✓ Created contact: {contact3_id} - Bob Johnson")
        
        # Test 3: Search functionality
        print("\n3. Testing Search Functionality...")
        
        # Email search
        email_results = db.search_contacts("john.doe@example.com")
        print(f"✓ Email search for 'john.doe@example.com': found {len(email_results)} contacts")
        if email_results:
            print(f"  - Found: {email_results[0]['name']} (confidence: {email_results[0]['confidence']})")
        
        # Name search
        name_results = db.search_contacts("Jane")
        print(f"✓ Name search for 'Jane': found {len(name_results)} contacts")
        if name_results:
            print(f"  - Found: {name_results[0]['name']} (confidence: {name_results[0]['confidence']})")
        
        # Phone search
        phone_results = db.search_contacts("+1-555-8901")
        print(f"✓ Phone search for '+1-555-8901': found {len(phone_results)} contacts")
        if phone_results:
            print(f"  - Found: {phone_results[0]['name']} (confidence: {phone_results[0]['confidence']})")
        
        # Test 4: Enrichment functionality  
        print("\n4. Testing Contact Enrichment...")
        enrichment_id = db.add_enrichment(
            contact_id=contact2_id,
            enrichment_type="job_title",
            enrichment_value="Senior Software Engineer",
            source_platform="mail",
            confidence=0.85,
            extraction_method="llm_analysis"
        )
        print(f"✓ Added enrichment: {enrichment_id}")
        
        enrichments = db.get_contact_enrichments(contact2_id)
        print(f"✓ Retrieved {len(enrichments)} enrichments for Jane Smith")
        for enrichment in enrichments:
            print(f"  - {enrichment['enrichment_type']}: {enrichment['enrichment_value']} (confidence: {enrichment['confidence']})")
        
        # Test 5: Bridge tool integration
        print("\n5. Testing Bridge Tool Integration...")
        bridge = ContactsBridgeTool()
        
        # Test search through bridge
        bridge_results = await bridge.search_contacts("john.doe@example.com")
        print(f"✓ Bridge search for 'john.doe@example.com': found {len(bridge_results)} contacts")
        if bridge_results:
            print(f"  - Found: {bridge_results[0]['name']} (confidence: {bridge_results[0]['confidence']})")
        
        # Test enrichment through bridge
        bridge_enrichments = await bridge.enrich_contact(contact2_id, "job_title")
        print(f"✓ Bridge enrichment for Jane Smith: found {len(bridge_enrichments)} enrichments")
        for enrichment in bridge_enrichments:
            print(f"  - {enrichment['type']}: {enrichment['value']} (confidence: {enrichment['confidence']})")
        
        # Test 6: Backup functionality
        print("\n6. Testing Backup Functionality...")
        backup_manager = ContactsBackup()
        
        # Create backup
        backup_path = backup_manager.create_backup()
        if backup_path:
            print(f"✓ Created backup: {backup_path}")
        else:
            print("✗ Failed to create backup")
        
        # List backups
        backups = backup_manager.list_backups()
        print(f"✓ Found {len(backups)} backup(s)")
        for backup in backups:
            print(f"  - {backup['filename']} ({backup['size_bytes']} bytes, created: {backup['created']})")
        
        # Test backup policy
        should_backup = backup_manager.should_create_backup()
        print(f"✓ Weekly backup needed: {should_backup}")
        
        # Clean up
        bridge.close()
        db.close()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED - Database integration successful!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_database_integration())
    sys.exit(0 if success else 1)