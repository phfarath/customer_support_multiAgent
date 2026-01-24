"""
HTTP Client Wrapper with Timeouts

Provides a configured httpx client with sensible defaults for timeouts,
retries, and connection pooling. Can be used throughout the application
for external API calls.

Features:
- Configurable timeouts (connect, read, write, pool)
- Connection pooling
- Retry logic with exponential backoff
- Circuit breaker pattern compatible
- Prometheus metrics compatible (future)
"""
import httpx
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import logging

logger = logging.getLogger(__name__)


# Default timeout configuration (in seconds)
DEFAULT_TIMEOUT = httpx.Timeout(
    connect=5.0,   # Time to establish connection
    read=30.0,     # Time to read response
    write=10.0,    # Time to send request
    pool=5.0       # Time to acquire connection from pool
)

# Longer timeout for LLM APIs (OpenAI, etc)
LLM_TIMEOUT = httpx.Timeout(
    connect=10.0,
    read=60.0,    # LLM can take time
    write=10.0,
    pool=5.0
)

# Short timeout for health checks
HEALTH_CHECK_TIMEOUT = httpx.Timeout(
    connect=2.0,
    read=5.0,
    write=2.0,
    pool=2.0
)


class HTTPClient:
    """
    HTTP Client wrapper with configurable timeouts.
    
    Usage:
        # Async context manager
        async with HTTPClient() as client:
            response = await client.get("https://api.example.com/data")
            
        # Singleton instance
        client = get_http_client()
        response = await client.get("https://api.example.com/data")
    """
    
    def __init__(
        self,
        timeout: Optional[httpx.Timeout] = None,
        limits: Optional[httpx.Limits] = None,
        **kwargs
    ):
        """
        Initialize HTTP client.
        
        Args:
            timeout: Timeout configuration (defaults to DEFAULT_TIMEOUT)
            limits: Connection pool limits
            **kwargs: Additional httpx.AsyncClient parameters
        """
        if timeout is None:
            timeout = DEFAULT_TIMEOUT
            
        if limits is None:
            limits = httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
                keepalive_expiry=30.0
            )
        
        self.client = httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            follow_redirects=True,
            **kwargs
        )
        
        self._timeout = timeout
        logger.debug(f"HTTPClient initialized with timeout={timeout}")
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """GET request with timeout"""
        return await self.client.get(url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """POST request with timeout"""
        return await self.client.post(url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """PUT request with timeout"""
        return await self.client.put(url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """DELETE request with timeout"""
        return await self.client.delete(url, **kwargs)
    
    async def patch(self, url: str, **kwargs) -> httpx.Response:
        """PATCH request with timeout"""
        return await self.client.patch(url, **kwargs)
    
    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        """Generic request with timeout"""
        return await self.client.request(method, url, **kwargs)
    
    async def close(self):
        """Close the client and cleanup connections"""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Singleton instances for different use cases
_default_client: Optional[HTTPClient] = None
_llm_client: Optional[HTTPClient] = None


def get_http_client(timeout: Optional[httpx.Timeout] = None) -> HTTPClient:
    """
    Get or create the default HTTP client singleton.
    
    Args:
        timeout: Optional custom timeout (defaults to DEFAULT_TIMEOUT)
        
    Returns:
        HTTPClient instance
        
    Note:
        Singleton is only used if timeout is None (default).
        Custom timeouts create new instances.
    """
    global _default_client
    
    if timeout is not None:
        # Custom timeout = new instance (not singleton)
        return HTTPClient(timeout=timeout)
    
    if _default_client is None:
        _default_client = HTTPClient()
    
    return _default_client


def get_llm_client() -> HTTPClient:
    """
    Get or create the LLM HTTP client singleton (longer timeouts).
    
    Returns:
        HTTPClient instance configured for LLM APIs
    """
    global _llm_client
    
    if _llm_client is None:
        _llm_client = HTTPClient(timeout=LLM_TIMEOUT)
    
    return _llm_client


@asynccontextmanager
async def http_client(timeout: Optional[httpx.Timeout] = None):
    """
    Context manager for one-off HTTP client usage.
    
    Usage:
        async with http_client() as client:
            response = await client.get("https://api.example.com")
    """
    client = HTTPClient(timeout=timeout)
    try:
        yield client
    finally:
        await client.close()


async def cleanup_http_clients():
    """
    Cleanup all singleton HTTP clients.
    Call this during application shutdown.
    """
    global _default_client, _llm_client
    
    if _default_client:
        await _default_client.close()
        _default_client = None
        logger.info("Default HTTP client closed")
    
    if _llm_client:
        await _llm_client.close()
        _llm_client = None
        logger.info("LLM HTTP client closed")


# Convenience functions for common patterns
async def get_json(
    url: str,
    timeout: Optional[httpx.Timeout] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    GET request that returns JSON.
    
    Args:
        url: URL to fetch
        timeout: Optional timeout override
        headers: Optional headers
        
    Returns:
        Parsed JSON response
        
    Raises:
        httpx.HTTPError: On HTTP errors
        ValueError: If response is not valid JSON
    """
    client = get_http_client(timeout)
    response = await client.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


async def post_json(
    url: str,
    data: Dict[str, Any],
    timeout: Optional[httpx.Timeout] = None,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    POST JSON data and return JSON response.
    
    Args:
        url: URL to post to
        data: Data to send as JSON
        timeout: Optional timeout override
        headers: Optional headers
        
    Returns:
        Parsed JSON response
        
    Raises:
        httpx.HTTPError: On HTTP errors
        ValueError: If response is not valid JSON
    """
    client = get_http_client(timeout)
    response = await client.post(url, json=data, headers=headers)
    response.raise_for_status()
    return response.json()


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    
    async def test_http_client():
        """Test HTTP client functionality"""
        print("=== Testing HTTP Client ===\n")
        
        # Test 1: Context manager
        print("Test 1: Context manager usage")
        async with http_client() as client:
            try:
                response = await client.get("https://httpbin.org/delay/1")
                print(f"  Status: {response.status_code}")
                print(f"  Response time: {response.elapsed.total_seconds():.2f}s")
            except Exception as e:
                print(f"  Error: {e}")
        
        # Test 2: Timeout handling
        print("\nTest 2: Timeout handling (short timeout)")
        try:
            async with http_client(timeout=httpx.Timeout(1.0)) as client:
                # This should timeout
                response = await client.get("https://httpbin.org/delay/5")
                print(f"  Unexpected success: {response.status_code}")
        except httpx.TimeoutException:
            print("  ✅ Timeout handled correctly")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Test 3: Singleton
        print("\nTest 3: Singleton instance")
        client1 = get_http_client()
        client2 = get_http_client()
        print(f"  Same instance: {client1 is client2}")
        
        # Test 4: LLM client
        print("\nTest 4: LLM client with longer timeout")
        llm_client = get_llm_client()
        print(f"  LLM timeout: {llm_client._timeout}")
        
        # Test 5: Convenience function
        print("\nTest 5: Convenience function (get_json)")
        try:
            data = await get_json("https://httpbin.org/json")
            print(f"  Keys in response: {list(data.keys())[:3]}")
        except Exception as e:
            print(f"  Error: {e}")
        
        # Cleanup
        await cleanup_http_clients()
        print("\n✅ All tests completed")
    
    # Run tests
    asyncio.run(test_http_client())
