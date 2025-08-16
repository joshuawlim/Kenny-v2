"""
Live Calendar integration using JXA (JavaScript for Automation).

This module provides functions to interact with Apple Calendar.app via JXA.
Enhanced with robust error handling, retry mechanisms, and performance optimizations
for Phase 3.5 emergency stabilization.
"""

import subprocess
import json
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from functools import wraps

# Configure logging
logger = logging.getLogger("calendar_live")

# Retry configuration
DEFAULT_RETRY_COUNT = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_TIMEOUT = 30  # seconds


def retry_on_failure(max_retries=DEFAULT_RETRY_COUNT, delay=DEFAULT_RETRY_DELAY, backoff_factor=2.0):
    """
    Retry decorator with exponential backoff for JXA operations.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay on each retry
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(f"Retrying {func.__name__} (attempt {attempt + 1}/{max_retries + 1})")
                        time.sleep(current_delay)
                        current_delay *= backoff_factor
                    
                    return func(*args, **kwargs)
                    
                except subprocess.TimeoutExpired as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} timed out on attempt {attempt + 1}")
                    continue
                    
                except subprocess.CalledProcessError as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} failed with return code {e.returncode} on attempt {attempt + 1}")
                    # Don't retry on permission errors (return code 1)
                    if e.returncode == 1:
                        break
                    continue
                    
                except json.JSONDecodeError as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} returned invalid JSON on attempt {attempt + 1}")
                    continue
                    
                except Exception as e:
                    last_exception = e
                    logger.warning(f"{func.__name__} failed with unexpected error on attempt {attempt + 1}: {e}")
                    continue
            
            # All retries exhausted
            logger.error(f"{func.__name__} failed after {max_retries + 1} attempts")
            if last_exception:
                logger.error(f"Last error: {last_exception}")
            return [] if func.__name__.startswith('list_') else None
            
        return wrapper
    return decorator


def execute_jxa_script(script: str, timeout: int = DEFAULT_TIMEOUT) -> subprocess.CompletedProcess:
    """
    Execute a JXA script with robust error handling.
    
    Args:
        script: JXA script to execute
        timeout: Timeout in seconds
        
    Returns:
        CompletedProcess result
        
    Raises:
        subprocess.TimeoutExpired: If script times out
        subprocess.CalledProcessError: If script fails
    """
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", script],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True  # Raises CalledProcessError on non-zero exit
        )
        return result
        
    except subprocess.TimeoutExpired:
        logger.error(f"JXA script timed out after {timeout} seconds")
        raise
        
    except subprocess.CalledProcessError as e:
        logger.error(f"JXA script failed with return code {e.returncode}: {e.stderr}")
        raise


def parse_jxa_result(result: subprocess.CompletedProcess, operation_name: str) -> Any:
    """
    Parse JXA script result with error handling.
    
    Args:
        result: subprocess result
        operation_name: Name of operation for logging
        
    Returns:
        Parsed JSON data or None on error
    """
    try:
        if not result.stdout.strip():
            logger.warning(f"{operation_name}: Empty response from JXA script")
            return None
            
        data = json.loads(result.stdout.strip())
        logger.debug(f"{operation_name}: Successfully parsed JXA response")
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"{operation_name}: Invalid JSON response: {e}")
        logger.error(f"Raw output: {result.stdout}")
        return None


@retry_on_failure(max_retries=2, delay=0.5)
def list_calendars() -> List[Dict[str, Any]]:
    """
    Get list of all calendars from Calendar.app.
    
    Returns:
        List of calendar dictionaries with name, id, and properties
    """
    jxa_script = '''
    (function() {
        try {
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
                    console.log("Skipping calendar due to access error: " + e.toString());
                }
            }
            
            return JSON.stringify(result);
        } catch (e) {
            return JSON.stringify({error: "Failed to access Calendar app: " + e.toString()});
        }
    })();
    '''
    
    try:
        result = execute_jxa_script(jxa_script, timeout=20)
        data = parse_jxa_result(result, "list_calendars")
        
        if data is None:
            return []
        
        if isinstance(data, dict) and "error" in data:
            logger.error(f"Calendar app error: {data['error']}")
            return []
        
        if isinstance(data, list):
            logger.info(f"Found {len(data)} calendars")
            return data
        
        logger.warning(f"Unexpected data format: {type(data)}")
        return []
        
    except Exception as e:
        logger.error(f"Error listing calendars: {e}")
        return []


@retry_on_failure(max_retries=3, delay=1.0)
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
        try {{
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
                            console.log("Skipping event due to access error: " + e.toString());
                        }}
                    }}
                }} catch (e) {{
                    // Skip calendars that can't be accessed
                    console.log("Skipping calendar due to access error: " + e.toString());
                }}
            }}
            
            return JSON.stringify(result);
        }} catch (e) {{
            return JSON.stringify({{error: "Failed to access Calendar app: " + e.toString()}});
        }}
    }})();
    '''
    
    try:
        result = execute_jxa_script(jxa_script, timeout=35)
        data = parse_jxa_result(result, "list_events")
        
        if data is None:
            return []
        
        if isinstance(data, dict) and "error" in data:
            logger.error(f"Calendar app error: {data['error']}")
            return []
        
        if isinstance(data, list):
            logger.info(f"Found {len(data)} events")
            return data
        
        logger.warning(f"Unexpected data format: {type(data)}")
        return []
        
    except Exception as e:
        logger.error(f"Error listing events: {e}")
        return []


@retry_on_failure(max_retries=2, delay=0.5)
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
        try {{
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
                            console.log("Skipping event due to access error: " + e.toString());
                        }}
                    }}
                }} catch (e) {{
                    // Skip calendars that can't be accessed
                    console.log("Skipping calendar due to access error: " + e.toString());
                }}
            }}
            
            return JSON.stringify(null);
        }} catch (e) {{
            return JSON.stringify({{error: "Failed to access Calendar app: " + e.toString()}});
        }}
    }})();
    '''
    
    try:
        result = execute_jxa_script(jxa_script, timeout=25)
        data = parse_jxa_result(result, "get_event_by_id")
        
        if data is None:
            logger.info(f"Event {event_id} not found")
            return None
        
        if isinstance(data, dict) and "error" in data:
            logger.error(f"Calendar app error: {data['error']}")
            return None
        
        if isinstance(data, dict):
            logger.info(f"Found event {event_id}")
            return data
        
        logger.info(f"Event {event_id} not found")
        return None
        
    except Exception as e:
        logger.error(f"Error getting event {event_id}: {e}")
        return None


@retry_on_failure(max_retries=3, delay=1.0)
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
        result = execute_jxa_script(jxa_script, timeout=25)
        data = parse_jxa_result(result, "create_event")
        
        if data is None:
            return None
        
        if isinstance(data, dict) and "error" in data:
            logger.error(f"Event creation error: {data['error']}")
            return None
        
        if isinstance(data, dict) and data.get("created"):
            logger.info(f"Created event: {data.get('title')}")
            return data
        
        logger.warning(f"Unexpected create event response: {data}")
        return None
        
    except Exception as e:
        logger.error(f"Error creating event: {e}")
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