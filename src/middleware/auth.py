"""
API Key Authentication Middleware
"""
from fastapi import Header, HTTPException, status
from fastapi.security import APIKeyHeader
from src.database import get_collection, COLLECTION_API_KEYS
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Define API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")) -> dict:
    """
    Validates API key and returns associated company_id.

    Args:
        x_api_key: API key from X-API-Key header

    Returns:
        dict with api_key document (includes company_id, permissions)

    Raises:
        HTTPException 401: If API key is missing
        HTTPException 403: If API key is invalid or expired
    """
    if not x_api_key:
        logger.warning("API request without X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Include X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    # Validate API key format
    if not x_api_key.startswith("sk_"):
        logger.warning(f"Invalid API key format: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key format"
        )

    # Query database
    api_keys_collection = get_collection(COLLECTION_API_KEYS)
    key_doc = await api_keys_collection.find_one({"api_key": x_api_key})

    if not key_doc:
        logger.warning(f"API key not found: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key"
        )

    # Check if active
    if not key_doc.get("active", False):
        logger.warning(f"Inactive API key used: {key_doc.get('key_id')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has been revoked"
        )

    # Check expiration
    expires_at = key_doc.get("expires_at")
    if expires_at and datetime.now() > expires_at:
        logger.warning(f"Expired API key used: {key_doc.get('key_id')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key has expired"
        )

    # Update last_used_at (fire and forget - don't await)
    api_keys_collection.update_one(
        {"api_key": x_api_key},
        {"$set": {"last_used_at": datetime.now()}}
    )

    logger.info(f"API key validated: {key_doc.get('key_id')} (company: {key_doc.get('company_id')})")
    return key_doc


# Public endpoints (no authentication required)
PUBLIC_PATHS = [
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/health"
]
