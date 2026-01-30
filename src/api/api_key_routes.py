"""
API Key Management Routes
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from src.models.api_key import APIKey
from src.database import get_collection, COLLECTION_API_KEYS
from src.middleware.auth import verify_api_key
from datetime import datetime
import logging
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(prefix="/api/keys", tags=["api-keys"])
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


@router.post("/", response_model=APIKey)
@limiter.limit("10/minute")  # Admin operation
async def create_api_key(
    request: Request,  # Required by slowapi
    company_id: str,
    name: str,
    permissions: list[str] = ["read", "write"],
    api_key: dict = Depends(verify_api_key)
):
    """
    Create a new API key for a company

    NOTE: This should only be accessible by admin users.
    For MVP, requires existing API key (bootstrap problem - create first key manually).

    Args:
        company_id: Company ID for the new key
        name: Description/name for the key
        permissions: List of permissions (default: read, write)
        api_key: Authenticated API key from dependency

    Returns:
        Newly created API key

    Raises:
        403: If trying to create key for different company
    """
    # Only allow creating keys for own company (or if super-admin)
    if company_id != api_key["company_id"]:
        logger.warning(f"Unauthorized attempt to create key for different company: {company_id}")
        raise HTTPException(
            status_code=403,
            detail="Cannot create key for different company"
        )

    # Create new API key
    new_key = APIKey(
        company_id=company_id,
        name=name,
        permissions=permissions
    )

    # Save to database
    collection = get_collection(COLLECTION_API_KEYS)
    await collection.insert_one(new_key.dict())

    logger.info(f"API key created: {new_key.key_id} for company {company_id}")
    return new_key


@router.get("/", response_model=list[dict])
@limiter.limit("100/minute")  # Read operation
async def list_api_keys(
    request: Request,  # Required by slowapi
    api_key: dict = Depends(verify_api_key)
):
    """
    List all API keys for authenticated company

    API key values are masked in the response for security.

    Args:
        api_key: Authenticated API key from dependency

    Returns:
        List of API keys (with masked key values)
    """
    collection = get_collection(COLLECTION_API_KEYS)
    keys = await collection.find(
        {"company_id": api_key["company_id"]}
    ).to_list(length=100)

    # Hide actual API key value in list
    for key in keys:
        key["_id"] = str(key["_id"])  # Convert ObjectId to string
        key["api_key"] = key["api_key"][:10] + "..." + key["api_key"][-4:]

    logger.info(f"Listed {len(keys)} API keys for company {api_key['company_id']}")
    return keys


@router.delete("/{key_id}")
@limiter.limit("10/minute")  # Admin operation
async def revoke_api_key(
    request: Request,  # Required by slowapi
    key_id: str,
    api_key: dict = Depends(verify_api_key)
):
    """
    Revoke (deactivate) an API key

    Args:
        key_id: ID of the key to revoke
        api_key: Authenticated API key from dependency

    Returns:
        Success message

    Raises:
        404: If key not found
        403: If key belongs to different company
    """
    collection = get_collection(COLLECTION_API_KEYS)

    # Find key
    key_doc = await collection.find_one({"key_id": key_id})
    if not key_doc:
        raise HTTPException(status_code=404, detail="API key not found")

    # Check ownership
    if key_doc["company_id"] != api_key["company_id"]:
        logger.warning(f"Unauthorized attempt to revoke key {key_id}")
        raise HTTPException(
            status_code=403,
            detail="Cannot revoke key from different company"
        )

    # Revoke (set active=False)
    result = await collection.update_one(
        {"key_id": key_id},
        {
            "$set": {
                "active": False,
                "revoked_at": datetime.now()
            }
        }
    )

    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="API key not found")

    logger.info(f"API key revoked: {key_id}")
    return {"message": "API key revoked successfully", "key_id": key_id}
