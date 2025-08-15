"""
iMessage Live Integration using JXA (JavaScript for Automation).

This module provides functions to interact with macOS Messages.app
to fetch, search, and read iMessage conversations and messages.
"""

import json
import subprocess
import tempfile
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional


def _run_jxa_script(script: str) -> Dict[str, Any]:
    """
    Run a JXA script and return the parsed JSON result.
    
    Args:
        script: JXA script code to execute
        
    Returns:
        Parsed JSON result from the script
    """
    try:
        # Write script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(script)
            script_path = f.name
        
        try:
            # Run the JXA script using osascript
            result = subprocess.run(
                ['osascript', '-l', 'JavaScript', script_path],
                capture_output=True,
                text=True,
                timeout=45  # JXA can be slow
            )
            
            if result.returncode != 0:
                print(f"[imessage_live] JXA script error: {result.stderr}")
                return {"error": result.stderr, "results": []}
            
            # Parse JSON result
            if result.stdout.strip():
                return json.loads(result.stdout.strip())
            else:
                return {"results": []}
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(script_path)
            except:
                pass
                
    except subprocess.TimeoutExpired:
        print("[imessage_live] JXA script timed out")
        return {"error": "Script timeout", "results": []}
    except json.JSONDecodeError as e:
        print(f"[imessage_live] JSON parse error: {e}")
        print(f"[imessage_live] Raw output: {result.stdout}")
        return {"error": f"JSON parse error: {e}", "results": []}
    except Exception as e:
        print(f"[imessage_live] Unexpected error: {e}")
        return {"error": str(e), "results": []}


def fetch_imessages(limit: int = 100, page: int = 0) -> List[Dict[str, Any]]:
    """
    Fetch recent iMessages from Messages.app.
    
    Args:
        limit: Maximum number of messages to return
        page: Page number for pagination
        
    Returns:
        List of message dictionaries
    """
    offset = page * limit
    
    jxa_script = f"""
    function run(argv) {{
        const Messages = Application('Messages');
        const results = [];
        
        try {{
            // Get all chats
            const chats = Messages.chats();
            let messageCount = 0;
            let skipped = 0;
            
            // Iterate through chats to collect recent messages
            for (let i = 0; i < chats.length && messageCount < {limit + offset}; i++) {{
                const chat = chats[i];
                
                try {{
                    const messages = chat.messages();
                    
                    // Process messages from newest to oldest
                    for (let j = messages.length - 1; j >= 0 && messageCount < {limit + offset}; j--) {{
                        const message = messages[j];
                        
                        if (skipped < {offset}) {{
                            skipped++;
                            continue;
                        }}
                        
                        const messageData = {{
                            id: `imessage-${{i}}-${{j}}`,
                            thread_id: `thread-${{i}}`,
                            from: message.direction() === "incoming" ? (message.handle() || "Unknown") : "Me",
                            to: message.direction() === "outgoing" ? (message.handle() || "Unknown") : "Me",
                            content: message.text() || "",
                            timestamp: new Date(message.date()).toISOString(),
                            message_type: message.service() === "iMessage" ? "text" : "sms",
                            has_attachments: false,
                            contact_name: message.handle() || "Unknown",
                            phone_number: message.handle() || "",
                            attachments: []
                        }};
                        
                        results.push(messageData);
                        messageCount++;
                        
                        if (messageCount >= {limit}) break;
                    }}
                }} catch (msgError) {{
                    // Skip problematic chats
                    continue;
                }}
            }}
        }} catch (error) {{
            return JSON.stringify({{
                error: error.toString(),
                results: results
            }});
        }}
        
        return JSON.stringify({{
            results: results,
            total: results.length
        }});
    }}
    """
    
    result = _run_jxa_script(jxa_script)
    return result.get("results", [])


def search_imessages(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search iMessages by query text.
    
    Args:
        query: Search query string
        limit: Maximum number of results to return
        
    Returns:
        List of matching message dictionaries
    """
    jxa_script = f"""
    function run(argv) {{
        const Messages = Application('Messages');
        const results = [];
        const searchQuery = "{query}".toLowerCase();
        
        try {{
            // Get all chats
            const chats = Messages.chats();
            let foundCount = 0;
            
            // Iterate through chats to search messages
            for (let i = 0; i < chats.length && foundCount < {limit}; i++) {{
                const chat = chats[i];
                
                try {{
                    const messages = chat.messages();
                    
                    // Search through messages
                    for (let j = messages.length - 1; j >= 0 && foundCount < {limit}; j--) {{
                        const message = messages[j];
                        const messageText = (message.text() || "").toLowerCase();
                        
                        // Check if message contains search query
                        if (messageText.includes(searchQuery)) {{
                            const messageData = {{
                                id: `search-imessage-${{i}}-${{j}}`,
                                thread_id: `search-thread-${{i}}`,
                                from: message.direction() === "incoming" ? (message.handle() || "Unknown") : "Me",
                                to: message.direction() === "outgoing" ? (message.handle() || "Unknown") : "Me",
                                content: message.text() || "",
                                timestamp: new Date(message.date()).toISOString(),
                                message_type: message.service() === "iMessage" ? "text" : "sms",
                                has_attachments: false,
                                contact_name: message.handle() || "Unknown",
                                phone_number: message.handle() || "",
                                attachments: []
                            }};
                            
                            results.push(messageData);
                            foundCount++;
                        }}
                    }}
                }} catch (msgError) {{
                    // Skip problematic chats
                    continue;
                }}
            }}
        }} catch (error) {{
            return JSON.stringify({{
                error: error.toString(),
                results: results
            }});
        }}
        
        return JSON.stringify({{
            results: results,
            total: results.length,
            query: "{query}"
        }});
    }}
    """
    
    result = _run_jxa_script(jxa_script)
    return result.get("results", [])


def get_imessage_thread(thread_id: str) -> Dict[str, Any]:
    """
    Get all messages from a specific thread.
    
    Args:
        thread_id: Thread identifier
        
    Returns:
        Thread data with messages and thread info
    """
    # Extract chat index from thread_id (assuming format "thread-N")
    try:
        chat_index = int(thread_id.split("-")[-1])
    except:
        chat_index = 0
    
    jxa_script = f"""
    function run(argv) {{
        const Messages = Application('Messages');
        const messages = [];
        
        try {{
            const chats = Messages.chats();
            
            if ({chat_index} >= chats.length) {{
                return JSON.stringify({{
                    error: "Thread not found",
                    thread_id: "{thread_id}",
                    messages: []
                }});
            }}
            
            const chat = chats[{chat_index}];
            const chatMessages = chat.messages();
            
            // Get all messages from this chat
            for (let i = 0; i < chatMessages.length; i++) {{
                const message = chatMessages[i];
                
                const messageData = {{
                    id: `thread-msg-{thread_id}-${{i}}`,
                    thread_id: "{thread_id}",
                    from: message.direction() === "incoming" ? (message.handle() || "Unknown") : "Me",
                    to: message.direction() === "outgoing" ? (message.handle() || "Unknown") : "Me",
                    content: message.text() || "",
                    timestamp: new Date(message.date()).toISOString(),
                    message_type: message.service() === "iMessage" ? "text" : "sms",
                    has_attachments: false,
                    contact_name: message.handle() || "Unknown",
                    phone_number: message.handle() || "",
                    attachments: []
                }};
                
                messages.push(messageData);
            }}
            
            // Sort messages by timestamp (newest first)
            messages.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
        }} catch (error) {{
            return JSON.stringify({{
                error: error.toString(),
                thread_id: "{thread_id}",
                messages: []
            }});
        }}
        
        return JSON.stringify({{
            thread_id: "{thread_id}",
            messages: messages,
            thread_info: {{
                id: "{thread_id}",
                participants: messages.length > 0 ? [messages[0].contact_name, "Me"] : ["Unknown", "Me"],
                message_count: messages.length,
                last_message: messages.length > 0 ? messages[0].timestamp : null
            }}
        }});
    }}
    """
    
    result = _run_jxa_script(jxa_script)
    return result


def test_imessage_integration():
    """Test function to verify iMessage integration works."""
    print("Testing iMessage integration...")
    
    # Test fetching recent messages
    print("1. Fetching recent messages...")
    messages = fetch_imessages(limit=5)
    print(f"   Found {len(messages)} messages")
    
    # Test searching messages
    print("2. Searching messages...")
    search_results = search_imessages("test", limit=3)
    print(f"   Found {len(search_results)} search results")
    
    # Test getting thread
    print("3. Getting thread...")
    thread_data = get_imessage_thread("thread-0")
    thread_messages = thread_data.get("messages", [])
    print(f"   Found {len(thread_messages)} messages in thread")
    
    print("iMessage integration test complete!")
    
    return {
        "recent_messages": len(messages),
        "search_results": len(search_results),
        "thread_messages": len(thread_messages)
    }


if __name__ == "__main__":
    # Run test when executed directly
    test_results = test_imessage_integration()
    print(f"Test results: {test_results}")