import json
import subprocess
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _run_jxa(script: str) -> str:
    """Run a JXA (JavaScript for Automation) script via osascript and return stdout.

    Raises RuntimeError on non-zero exit.
    """
    result = subprocess.run(
        ["osascript", "-l", "JavaScript", "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"osascript failed with code {result.returncode}")
    return result.stdout.strip()


def _build_contacts_fetch_script(limit: int = 100) -> str:
    """Build JXA script to fetch contacts from macOS Contacts.app.

    The script returns a JSON string array with contact information.
    """
    return f"""
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;

    const Contacts = Application('Contacts');

    function toJs(contact) {{
      function safe(fn, dflt) {{
        try {{ return fn(); }} catch (e) {{ return dflt; }}
      }}
      
      // Get basic info
      const id = safe(() => contact.id(), '');
      const firstName = safe(() => contact.firstName(), '');
      const lastName = safe(() => contact.lastName(), '');
      const fullName = safe(() => {{
        const first = firstName || '';
        const last = lastName || '';
        return (first + ' ' + last).trim() || contact.name() || '';
      }}, '');
      
      // Get emails
      let emails = [];
      try {{
        const emailList = contact.emails();
        emails = (emailList || []).map(email => {{
          try {{ return email.value(); }} catch (e) {{ return ''; }}
        }}).filter(e => e);
      }} catch (e) {{ emails = []; }}
      
      // Get phones
      let phones = [];
      try {{
        const phoneList = contact.phones();
        phones = (phoneList || []).map(phone => {{
          try {{ return phone.value(); }} catch (e) {{ return ''; }}
        }}).filter(p => p);
      }} catch (e) {{ phones = []; }}
      
      // Get organization
      const organization = safe(() => contact.organization(), '');
      
      // Get note
      const note = safe(() => contact.note(), '');
      
      // Get creation/modification dates
      const creationDate = safe(() => {{
        const date = contact.creationDate();
        return date ? new Date(date).toISOString() : null;
      }}, null);
      
      const modificationDate = safe(() => {{
        const date = contact.modificationDate();
        return date ? new Date(date).toISOString() : null;
      }}, null);
      
      return {{
        id: id,
        name: fullName,
        firstName: firstName,
        lastName: lastName,
        emails: emails,
        phones: phones,
        organization: organization,
        note: note,
        creationDate: creationDate,
        modificationDate: modificationDate
      }};
    }}

    try {{
      const allContacts = Contacts.people();
      let contactsArray = [];
      
      // Convert to JS objects and filter out empty contacts
      for (let i = 0; i < Math.min(allContacts.length, {int(limit)}); i++) {{
        try {{
          const contact = allContacts[i];
          const jsContact = toJs(contact);
          // Only include contacts that have at least a name or email/phone
          if (jsContact.name || jsContact.emails.length > 0 || jsContact.phones.length > 0) {{
            contactsArray.push(jsContact);
          }}
        }} catch (e) {{
          // Skip problematic contacts
          continue;
        }}
      }}
      
      // Sort by name
      contactsArray.sort((a, b) => {{
        const nameA = (a.name || '').toLowerCase();
        const nameB = (b.name || '').toLowerCase();
        return nameA.localeCompare(nameB);
      }});
      
      JSON.stringify(contactsArray);
    }} catch (e) {{
      JSON.stringify([]);
    }}
    """


def _build_contact_search_script(query: str, limit: int = 50) -> str:
    """Build JXA script to search for contacts by name, email, or phone.

    The script returns a JSON string array with matching contacts.
    """
    # Escape query for inclusion in JS string
    escaped_query = query.replace("\\", "\\\\").replace("\"", "\\\"")
    
    return f"""
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;

    const Contacts = Application('Contacts');

    function toJs(contact) {{
      function safe(fn, dflt) {{
        try {{ return fn(); }} catch (e) {{ return dflt; }}
      }}
      
      const id = safe(() => contact.id(), '');
      const firstName = safe(() => contact.firstName(), '');
      const lastName = safe(() => contact.lastName(), '');
      const fullName = safe(() => {{
        const first = firstName || '';
        const last = lastName || '';
        return (first + ' ' + last).trim() || contact.name() || '';
      }}, '');
      
      let emails = [];
      try {{
        const emailList = contact.emails();
        emails = (emailList || []).map(email => {{
          try {{ return email.value(); }} catch (e) {{ return ''; }}
        }}).filter(e => e);
      }} catch (e) {{ emails = []; }}
      
      let phones = [];
      try {{
        const phoneList = contact.phones();
        phones = (phoneList || []).map(phone => {{
          try {{ return phone.value(); }} catch (e) {{ return ''; }}
        }}).filter(p => p);
      }} catch (e) {{ phones = []; }}
      
      const organization = safe(() => contact.organization(), '');
      const note = safe(() => contact.note(), '');
      
      return {{
        id: id,
        name: fullName,
        firstName: firstName,
        lastName: lastName,
        emails: emails,
        phones: phones,
        organization: organization,
        note: note
      }};
    }}

    function matchesQuery(contact, query) {{
      const lowerQuery = query.toLowerCase();
      const name = (contact.name || '').toLowerCase();
      const firstName = (contact.firstName || '').toLowerCase();
      const lastName = (contact.lastName || '').toLowerCase();
      const org = (contact.organization || '').toLowerCase();
      
      // Check name matches
      if (name.includes(lowerQuery) || firstName.includes(lowerQuery) || lastName.includes(lowerQuery)) {{
        return true;
      }}
      
      // Check organization
      if (org.includes(lowerQuery)) {{
        return true;
      }}
      
      // Check emails
      for (const email of contact.emails) {{
        if (email.toLowerCase().includes(lowerQuery)) {{
          return true;
        }}
      }}
      
      // Check phones (remove formatting for comparison)
      const cleanQuery = lowerQuery.replace(/[^0-9]/g, '');
      if (cleanQuery) {{
        for (const phone of contact.phones) {{
          const cleanPhone = phone.replace(/[^0-9]/g, '');
          if (cleanPhone.includes(cleanQuery)) {{
            return true;
          }}
        }}
      }}
      
      return false;
    }}

    try {{
      const allContacts = Contacts.people();
      let matchingContacts = [];
      const query = "{escaped_query}";
      
      for (let i = 0; i < allContacts.length && matchingContacts.length < {int(limit)}; i++) {{
        try {{
          const contact = allContacts[i];
          const jsContact = toJs(contact);
          
          // Only include contacts that have at least a name or email/phone
          if ((jsContact.name || jsContact.emails.length > 0 || jsContact.phones.length > 0) &&
              matchesQuery(jsContact, query)) {{
            matchingContacts.push(jsContact);
          }}
        }} catch (e) {{
          // Skip problematic contacts
          continue;
        }}
      }}
      
      // Sort by relevance (exact matches first, then partial matches)
      matchingContacts.sort((a, b) => {{
        const queryLower = query.toLowerCase();
        const aName = (a.name || '').toLowerCase();
        const bName = (b.name || '').toLowerCase();
        
        // Exact name matches first
        if (aName === queryLower && bName !== queryLower) return -1;
        if (bName === queryLower && aName !== queryLower) return 1;
        
        // Then by name length (shorter names first for better matches)
        return aName.length - bName.length;
      }});
      
      JSON.stringify(matchingContacts);
    }} catch (e) {{
      JSON.stringify([]);
    }}
    """


def fetch_all_contacts(limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch contacts from macOS Contacts.app.

    Args:
        limit: Maximum number of contacts to return

    Returns:
        List of contact dictionaries
    """
    script = _build_contacts_fetch_script(limit)
    raw = _run_jxa(script)
    try:
        contacts = json.loads(raw or "[]")
        if not isinstance(contacts, list):
            raise ValueError("JXA returned non-list")
    except Exception as parse_err:
        raise RuntimeError(f"Failed to parse JXA output: {parse_err}")

    # Normalize the contact data
    normalized: List[Dict[str, Any]] = []
    for contact in contacts:
        try:
            normalized.append({
                "id": str(contact.get("id", "")),
                "name": str(contact.get("name", "")),
                "firstName": contact.get("firstName", ""),
                "lastName": contact.get("lastName", ""),
                "emails": list(contact.get("emails", [])),
                "phones": list(contact.get("phones", [])),
                "organization": contact.get("organization", ""),
                "note": contact.get("note", ""),
                "creationDate": contact.get("creationDate"),
                "modificationDate": contact.get("modificationDate"),
                "platforms": ["contacts"],  # Mark as coming from macOS Contacts
                "source": "macos_contacts"
            })
        except Exception:
            # Skip malformed contacts
            continue

    return normalized


def search_contacts(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Search for contacts in macOS Contacts.app.

    Args:
        query: Search query (name, email, phone, etc.)
        limit: Maximum number of results to return

    Returns:
        List of matching contact dictionaries
    """
    if not query or not query.strip():
        return []

    script = _build_contact_search_script(query.strip(), limit)
    raw = _run_jxa(script)
    try:
        contacts = json.loads(raw or "[]")
        if not isinstance(contacts, list):
            raise ValueError("JXA returned non-list")
    except Exception as parse_err:
        raise RuntimeError(f"Failed to parse JXA output: {parse_err}")

    # Normalize and add confidence scores
    normalized: List[Dict[str, Any]] = []
    query_lower = query.lower()
    
    for i, contact in enumerate(contacts):
        try:
            # Calculate confidence based on match quality
            confidence = _calculate_match_confidence(contact, query_lower)
            
            normalized.append({
                "id": str(contact.get("id", "")),
                "name": str(contact.get("name", "")),
                "firstName": contact.get("firstName", ""),
                "lastName": contact.get("lastName", ""),
                "emails": list(contact.get("emails", [])),
                "phones": list(contact.get("phones", [])),
                "organization": contact.get("organization", ""),
                "note": contact.get("note", ""),
                "platforms": ["contacts"],
                "source": "macos_contacts",
                "confidence": confidence,
                "match_rank": i  # Preserve JXA ranking
            })
        except Exception:
            # Skip malformed contacts
            continue

    return normalized


def _calculate_match_confidence(contact: Dict[str, Any], query_lower: str) -> float:
    """Calculate confidence score for a contact match."""
    name = (contact.get("name", "") or "").lower()
    emails = [email.lower() for email in contact.get("emails", [])]
    phones = [phone.lower() for phone in contact.get("phones", [])]
    
    # Exact name match
    if name == query_lower:
        return 1.0
    
    # Exact email match
    if query_lower in emails:
        return 0.95
    
    # Phone number match (normalized)
    clean_query = ''.join(c for c in query_lower if c.isdigit())
    if clean_query:
        for phone in phones:
            clean_phone = ''.join(c for c in phone if c.isdigit())
            if clean_query in clean_phone or clean_phone in clean_query:
                return 0.90
    
    # Name starts with query
    if name.startswith(query_lower):
        return 0.85
    
    # Name contains query
    if query_lower in name:
        return 0.75
    
    # Email domain or partial match
    for email in emails:
        if query_lower in email:
            return 0.70
    
    # Organization match
    org = (contact.get("organization", "") or "").lower()
    if query_lower in org:
        return 0.65
    
    # Default for matches found by JXA search
    return 0.60


def get_contact_by_id(contact_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific contact by ID from macOS Contacts.app.

    Args:
        contact_id: The contact ID to retrieve

    Returns:
        Contact dictionary or None if not found
    """
    # For now, search all contacts and find by ID
    # This could be optimized with a specific JXA script if needed
    try:
        contacts = fetch_all_contacts(limit=1000)  # Get more contacts to find the specific ID
        for contact in contacts:
            if contact.get("id") == contact_id:
                return contact
    except Exception:
        pass
    
    return None