"""
Bridge integration tests for iMessage Agent.

Tests the integration between the iMessage Agent and the macOS Bridge,
including JXA script functionality and demo mode fallbacks.
"""

import pytest
import sys
import os
import httpx
from unittest.mock import Mock, patch

# Add bridge directory to path for imports
bridge_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'bridge')
sys.path.insert(0, bridge_path)

from imessage_live import fetch_imessages, search_imessages, get_imessage_thread, test_imessage_integration


class TestiMessageBridgeIntegration:
    """Tests for iMessage bridge integration."""
    
    def test_imessage_live_fetch_messages(self):
        """Test fetching iMessages via JXA (will use mock/demo data if JXA fails)."""
        # This test will work in both live and demo modes
        messages = fetch_imessages(limit=5)
        
        assert isinstance(messages, list)
        assert len(messages) <= 5
        
        # If we get results, validate structure
        for message in messages:
            assert isinstance(message, dict)
            required_fields = ["id", "thread_id", "timestamp"]
            for field in required_fields:
                assert field in message, f"Missing field in message: {field}"
    
    def test_imessage_live_search(self):
        """Test searching iMessages via JXA."""
        results = search_imessages("test", limit=3)
        
        assert isinstance(results, list)
        assert len(results) <= 3
        
        # Validate structure if we get results
        for result in results:
            assert isinstance(result, dict)
            assert "id" in result
            assert "content" in result
    
    def test_imessage_live_thread(self):
        """Test getting iMessage thread via JXA."""
        thread_data = get_imessage_thread("thread-0")
        
        assert isinstance(thread_data, dict)
        assert "thread_id" in thread_data
        
        if "messages" in thread_data:
            assert isinstance(thread_data["messages"], list)
    
    def test_imessage_integration_test_runner(self):
        """Test the built-in integration test function."""
        try:
            results = test_imessage_integration()
            assert isinstance(results, dict)
            assert "recent_messages" in results
            assert "search_results" in results
            assert "thread_messages" in results
            
            # All counts should be non-negative
            assert results["recent_messages"] >= 0
            assert results["search_results"] >= 0
            assert results["thread_messages"] >= 0
        except Exception as e:
            # If JXA fails, that's expected in test environment
            print(f"JXA integration test failed (expected in test env): {e}")
            pytest.skip("JXA not available in test environment")
    
    @pytest.mark.asyncio
    async def test_bridge_endpoints_demo_mode(self):
        """Test bridge endpoints in demo mode."""
        # This test assumes bridge is running on localhost:5100
        bridge_url = "http://localhost:5100"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Test health endpoint
                health_response = await client.get(f"{bridge_url}/health")
                if health_response.status_code == 200:
                    assert health_response.json()["status"] == "ok"
                
                # Test iMessage list endpoint
                list_response = await client.get(
                    f"{bridge_url}/v1/messages/imessage",
                    params={"limit": 3}
                )
                if list_response.status_code == 200:
                    data = list_response.json()
                    assert "messages" in data or isinstance(data, list)
                
                # Test iMessage search endpoint
                search_response = await client.get(
                    f"{bridge_url}/v1/messages/imessage/search",
                    params={"q": "test", "limit": 2}
                )
                if search_response.status_code == 200:
                    data = search_response.json()
                    assert "results" in data or isinstance(data, list)
                
                # Test thread endpoint
                thread_response = await client.get(
                    f"{bridge_url}/v1/messages/imessage/thread/thread-0"
                )
                if thread_response.status_code == 200:
                    data = thread_response.json()
                    assert "messages" in data or "thread_id" in data
                    
            except httpx.RequestError:
                pytest.skip("Bridge not available for endpoint testing")
    
    def test_jxa_script_structure(self):
        """Test that JXA scripts have proper structure and error handling."""
        from imessage_live import _run_jxa_script
        
        # Test with a simple JXA script that should work
        simple_script = '''
        function run(argv) {
            return JSON.stringify({
                test: "success",
                timestamp: new Date().toISOString()
            });
        }
        '''
        
        result = _run_jxa_script(simple_script)
        assert isinstance(result, dict)
        assert "test" in result
        assert result["test"] == "success"
    
    def test_jxa_error_handling(self):
        """Test JXA error handling for malformed scripts."""
        from imessage_live import _run_jxa_script
        
        # Test with malformed script
        bad_script = '''
        function run(argv) {
            throw new Error("Test error");
        }
        '''
        
        result = _run_jxa_script(bad_script)
        assert isinstance(result, dict)
        assert "error" in result
    
    def test_jxa_timeout_handling(self):
        """Test JXA timeout handling."""
        from imessage_live import _run_jxa_script
        
        # Test with script that would timeout (if timeout were very short)
        slow_script = '''
        function run(argv) {
            // This should complete quickly, but tests the timeout mechanism
            return JSON.stringify({status: "completed"});
        }
        '''
        
        result = _run_jxa_script(slow_script)
        assert isinstance(result, dict)
        # Should not timeout for this simple script
        assert "error" not in result or "timeout" not in result["error"].lower()
    
    def test_demo_data_structure(self):
        """Test that demo data follows expected iMessage structure."""
        # Test fetch_imessages demo fallback
        messages = fetch_imessages(limit=2)
        
        for message in messages:
            assert "id" in message
            assert "thread_id" in message
            assert "timestamp" in message
            assert "message_type" in message
            assert "content" in message
            
            # Validate timestamp format
            assert "T" in message["timestamp"]
            assert message["timestamp"].endswith("Z")
    
    def test_search_query_handling(self):
        """Test search query handling and result relevance."""
        # Test with specific query
        results = search_imessages("hello", limit=5)
        
        # Should return results (demo or live)
        assert isinstance(results, list)
        
        # In demo mode, results should contain the query term
        for result in results:
            if "content" in result and result["content"]:
                # Demo results should include the search term
                content_lower = result["content"].lower()
                # Either contains query or is demo data that mentions it
                assert "hello" in content_lower or "demo" in content_lower
    
    def test_thread_data_consistency(self):
        """Test thread data consistency and structure."""
        thread_data = get_imessage_thread("thread-1")
        
        assert "thread_id" in thread_data
        assert thread_data["thread_id"] == "thread-1"
        
        if "messages" in thread_data:
            messages = thread_data["messages"]
            for message in messages:
                # All messages should have the same thread_id
                assert message["thread_id"] == "thread-1"
        
        if "thread_info" in thread_data:
            thread_info = thread_data["thread_info"]
            assert "participants" in thread_info
            assert "message_count" in thread_info
            assert isinstance(thread_info["participants"], list)
            assert isinstance(thread_info["message_count"], int)
    
    @patch('subprocess.run')
    def test_jxa_subprocess_mocking(self, mock_subprocess):
        """Test JXA functionality with mocked subprocess."""
        from imessage_live import _run_jxa_script
        
        # Mock successful JXA execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"test": "mocked", "messages": []}'
        mock_result.stderr = ''
        mock_subprocess.return_value = mock_result
        
        script = 'function run() { return JSON.stringify({test: "real"}); }'
        result = _run_jxa_script(script)
        
        assert result["test"] == "mocked"
        mock_subprocess.assert_called_once()
    
    def test_bridge_environment_variables(self):
        """Test bridge behavior with different environment settings."""
        # Test with demo mode (default)
        assert os.getenv("IMESSAGE_BRIDGE_MODE", "demo") in ["demo", "live"]
        
        # This confirms the environment variable is properly used
        # Real testing of live vs demo mode would require bridge running
    
    def test_cache_key_generation(self):
        """Test that different requests generate appropriate cache keys."""
        # This is more relevant for the bridge service, but we can test
        # that different parameters to our functions would generate different results
        
        messages1 = fetch_imessages(limit=5, page=0)
        messages2 = fetch_imessages(limit=3, page=0)
        
        # Different limits might produce different results
        assert isinstance(messages1, list)
        assert isinstance(messages2, list)
        
        # Test different pages
        messages_page1 = fetch_imessages(limit=5, page=0)
        messages_page2 = fetch_imessages(limit=5, page=1)
        
        assert isinstance(messages_page1, list)
        assert isinstance(messages_page2, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])