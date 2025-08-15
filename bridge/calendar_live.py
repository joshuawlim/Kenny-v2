"""
Live Calendar integration using JXA (JavaScript for Automation).

This module provides functions to interact with Apple Calendar.app via JXA.
"""

import subprocess
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def list_calendars() -> List[Dict[str, Any]]:
    """
    Get list of all calendars from Calendar.app.
    
    Returns:
        List of calendar dictionaries with name, id, and properties
    """
    jxa_script = '''
    (function() {
        const app = Application("Calendar");
        const calendars = app.calendars;
        const result = [];
        
        for (let i = 0; i < calendars.length; i++) {
            const calendar = calendars[i];
            try {
                result.push({
                    id: calendar.id(),
                    name: calendar.name(),
                    description: calendar.description() || "",
                    color: calendar.color() || "blue",
                    writable: calendar.writable(),
                    visible: calendar.visible()
                });
            } catch (e) {
                // Skip calendars that can't be accessed
            }
        }
        
        return JSON.stringify(result);
    })();
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            calendars = json.loads(result.stdout.strip())
            print(f"[calendar_live] Found {len(calendars)} calendars")
            return calendars
        else:
            print(f"[calendar_live] JXA error: {result.stderr}")
            return []
            
    except subprocess.TimeoutExpired:
        print("[calendar_live] Calendar list timeout")
        return []
    except Exception as e:
        print(f"[calendar_live] Error listing calendars: {e}")
        return []


def list_events(calendar_name: Optional[str] = None, start_date: Optional[str] = None, 
                end_date: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Get events from Calendar.app.
    
    Args:
        calendar_name: Name of calendar to search (optional)
        start_date: ISO format start date (optional)
        end_date: ISO format end date (optional)
        limit: Maximum number of events to return
        
    Returns:
        List of event dictionaries
    """
    # Build date filter parameters
    date_filter = ""
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
            date_filter += f'const startDate = new Date("{start_dt.isoformat()}");'
        except:
            date_filter += f'const startDate = new Date();'
    else:
        date_filter += f'const startDate = new Date();'
        
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            date_filter += f'const endDate = new Date("{end_dt.isoformat()}");'
        except:
            date_filter += f'const endDate = new Date(startDate.getTime() + 7 * 24 * 60 * 60 * 1000);'
    else:
        date_filter += f'const endDate = new Date(startDate.getTime() + 7 * 24 * 60 * 60 * 1000);'
    
    calendar_filter = ""
    if calendar_name:
        calendar_filter = f'const targetCalendarName = "{calendar_name}";'
    else:
        calendar_filter = f'const targetCalendarName = null;'
    
    jxa_script = f'''
    (function() {{
        const app = Application("Calendar");
        {date_filter}
        {calendar_filter}
        const limit = {limit};
        
        const calendars = targetCalendarName ? 
            app.calendars.whose({{name: targetCalendarName}}) : 
            app.calendars;
        
        const result = [];
        let eventCount = 0;
        
        for (let i = 0; i < calendars.length && eventCount < limit; i++) {{
            const calendar = calendars[i];
            try {{
                const events = calendar.events.whose({{
                    startDate: {{">": startDate}},
                    endDate: {{"<": endDate}}
                }});
                
                for (let j = 0; j < events.length && eventCount < limit; j++) {{
                    const event = events[j];
                    try {{
                        const eventStart = event.startDate();
                        const eventEnd = event.endDate();
                        
                        result.push({{
                            id: event.id(),
                            title: event.summary() || "Untitled",
                            start: eventStart.toISOString(),
                            end: eventEnd.toISOString(),
                            all_day: event.allDayEvent(),
                            calendar: calendar.name(),
                            location: event.location() || "",
                            description: event.description() || "",
                            attendees: []  // JXA doesn't easily expose attendees
                        }});
                        eventCount++;
                    }} catch (e) {{
                        // Skip events that can't be accessed
                    }}
                }}
            }} catch (e) {{
                // Skip calendars that can't be accessed
            }}
        }}
        
        return JSON.stringify(result);
    }})();
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if result.returncode == 0 and result.stdout:
            events = json.loads(result.stdout.strip())
            print(f"[calendar_live] Found {len(events)} events")
            return events
        else:
            print(f"[calendar_live] JXA error: {result.stderr}")
            return []
            
    except subprocess.TimeoutExpired:
        print("[calendar_live] Calendar events timeout")
        return []
    except Exception as e:
        print(f"[calendar_live] Error listing events: {e}")
        return []


def get_event_by_id(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific event by ID from Calendar.app.
    
    Args:
        event_id: The event ID to search for
        
    Returns:
        Event dictionary or None if not found
    """
    jxa_script = f'''
    (function() {{
        const app = Application("Calendar");
        const targetId = "{event_id}";
        const calendars = app.calendars;
        
        for (let i = 0; i < calendars.length; i++) {{
            const calendar = calendars[i];
            try {{
                const events = calendar.events;
                for (let j = 0; j < events.length; j++) {{
                    const event = events[j];
                    try {{
                        if (event.id() === targetId) {{
                            const eventStart = event.startDate();
                            const eventEnd = event.endDate();
                            
                            return JSON.stringify({{
                                id: event.id(),
                                title: event.summary() || "Untitled",
                                start: eventStart.toISOString(),
                                end: eventEnd.toISOString(),
                                all_day: event.allDayEvent(),
                                calendar: calendar.name(),
                                location: event.location() || "",
                                description: event.description() || "",
                                attendees: []  // JXA doesn't easily expose attendees
                            }});
                        }}
                    }} catch (e) {{
                        // Skip events that can't be accessed
                    }}
                }}
            }} catch (e) {{
                // Skip calendars that can't be accessed
            }}
        }}
        
        return JSON.stringify(null);
    }})();
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            event_data = json.loads(result.stdout.strip())
            if event_data:
                print(f"[calendar_live] Found event {event_id}")
                return event_data
            else:
                print(f"[calendar_live] Event {event_id} not found")
                return None
        else:
            print(f"[calendar_live] JXA error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[calendar_live] Calendar event lookup timeout")
        return None
    except Exception as e:
        print(f"[calendar_live] Error getting event: {e}")
        return None


def create_event(event_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Create a new event in Calendar.app.
    
    Args:
        event_data: Event data dictionary
        
    Returns:
        Created event dictionary or None if failed
    """
    title = event_data.get("title", "New Event")
    start = event_data.get("start")
    end = event_data.get("end")
    all_day = event_data.get("all_day", False)
    calendar_name = event_data.get("calendar", "Calendar")
    location = event_data.get("location", "")
    description = event_data.get("description", "")
    
    if not start or not end:
        print("[calendar_live] Missing start or end time for event creation")
        return None
    
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        
        start_js = start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_js = end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        
    except Exception as e:
        print(f"[calendar_live] Invalid date format: {e}")
        return None
    
    jxa_script = f'''
    (function() {{
        const app = Application("Calendar");
        const calendars = app.calendars.whose({{name: "{calendar_name}"}});
        
        if (calendars.length === 0) {{
            return JSON.stringify({{error: "Calendar not found: {calendar_name}"}});
        }}
        
        const calendar = calendars[0];
        
        try {{
            const startDate = new Date("{start_js}");
            const endDate = new Date("{end_js}");
            
            const newEvent = app.Event({{
                summary: "{title}",
                startDate: startDate,
                endDate: endDate,
                allDayEvent: {str(all_day).lower()},
                location: "{location}",
                description: "{description}"
            }});
            
            calendar.events.push(newEvent);
            
            return JSON.stringify({{
                id: newEvent.id(),
                title: newEvent.summary(),
                start: startDate.toISOString(),
                end: endDate.toISOString(),
                all_day: {str(all_day).lower()},
                calendar: calendar.name(),
                location: "{location}",
                description: "{description}",
                created: true
            }});
            
        }} catch (e) {{
            return JSON.stringify({{error: "Failed to create event: " + e.toString()}});
        }}
    }})();
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and result.stdout:
            event_result = json.loads(result.stdout.strip())
            if "error" in event_result:
                print(f"[calendar_live] Event creation error: {event_result['error']}")
                return None
            else:
                print(f"[calendar_live] Created event: {event_result.get('title')}")
                return event_result
        else:
            print(f"[calendar_live] JXA error: {result.stderr}")
            return None
            
    except subprocess.TimeoutExpired:
        print("[calendar_live] Calendar event creation timeout")
        return None
    except Exception as e:
        print(f"[calendar_live] Error creating event: {e}")
        return None


# Test functions for development
if __name__ == "__main__":
    print("Testing Calendar live integration...")
    
    print("\n1. Testing calendar list:")
    calendars = list_calendars()
    for cal in calendars[:3]:  # Show first 3
        print(f"  - {cal['name']} (id: {cal['id']}, writable: {cal['writable']})")
    
    print("\n2. Testing event list:")
    events = list_events(limit=5)
    for event in events[:3]:  # Show first 3
        print(f"  - {event['title']} at {event['start']}")
    
    print("\nCalendar live integration test complete!")