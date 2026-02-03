"""
Advanced Rate Limiting Middleware

Provides fingerprint-based rate limiting that combines IP, User-Agent, and API Key
to create unique rate limit keys. This makes it harder to bypass rate limits using
proxies or by rotating IP addresses.
"""
import hashlib
import logging
from typing import Optional
from fastapi import Request
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)


# Rate limits by operation type
RATE_LIMITS = {
    "default": "60/minute",
    "ingest": "15/minute",      # Message ingestion (prevents spam)
    "pipeline": "5/minute",     # Pipeline execution (expensive OpenAI calls)
    "read": "120/minute",       # Read-only operations
    "write": "30/minute",       # Write operations
    "admin": "5/minute",        # Admin operations (create/delete configs)
    "webhook": "30/minute",     # Public webhook endpoints
    "critical": "3/minute",     # Critical operations (delete company, etc)
}


def get_rate_limit_key(request: Request) -> str:
    """
    Generate a rate limit key based on client fingerprint.

    Creates a unique key by combining:
    - IP address (primary identifier)
    - User-Agent hash (first 50 chars to limit size)
    - API Key prefix (first 10 chars for differentiation)

    This makes it harder to bypass rate limits using proxies alone,
    as the User-Agent and API Key must also match.

    Args:
        request: FastAPI request object

    Returns:
        MD5 hash of the combined fingerprint
    """
    # Get IP address
    ip = get_remote_address(request)

    # Get User-Agent (truncate to 50 chars for consistency)
    user_agent = request.headers.get("User-Agent", "")[:50]

    # Get API Key prefix (first 10 chars for differentiation without exposing full key)
    api_key = request.headers.get("X-API-Key", "")[:10]

    # Create fingerprint string
    fingerprint = f"{ip}:{user_agent}:{api_key}"

    # Hash the fingerprint for consistent key length
    hashed_key = hashlib.md5(fingerprint.encode()).hexdigest()

    logger.debug(f"Rate limit key generated for IP {ip}: {hashed_key[:8]}...")

    return hashed_key


def get_rate_limit_key_ip_only(request: Request) -> str:
    """
    Fallback rate limit key using only IP address.

    Use this for endpoints where fingerprinting is not appropriate
    (e.g., public endpoints without User-Agent requirements).

    Args:
        request: FastAPI request object

    Returns:
        IP address as the rate limit key
    """
    return get_remote_address(request)


def get_rate_limit(operation_type: str) -> str:
    """
    Get the rate limit string for a specific operation type.

    Args:
        operation_type: Type of operation (e.g., 'ingest', 'read', 'admin')

    Returns:
        Rate limit string (e.g., '15/minute')
    """
    return RATE_LIMITS.get(operation_type, RATE_LIMITS["default"])
