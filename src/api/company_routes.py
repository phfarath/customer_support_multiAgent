"""
FastAPI routes for company configuration management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List
import logging

from src.models import CompanyConfig, CompanyConfigCreate, CompanyConfigUpdate
from src.database import get_collection, COLLECTION_COMPANY_CONFIGS
from src.middleware.auth import verify_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.post("/", response_model=CompanyConfig)
async def create_company_config(
    config: CompanyConfigCreate,
    api_key: dict = Depends(verify_api_key)
) -> CompanyConfig:
    """
    Create a new company configuration

    Requires: X-API-Key header
    Note: Can only create config for own company

    Args:
        config: Company configuration to create
        api_key: Authenticated API key (auto-injected)

    Returns:
        Created company configuration
    """
    # Enforce company isolation
    if config.company_id != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create config for different company"
        )

    try:
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)

        config_dict = config.model_dump()
        config_dict["created_at"] = None  # Will be set by MongoDB
        
        result = await collection.insert_one(config_dict)
        config_dict["_id"] = str(result.inserted_id)
        
        logger.info(f"Created company config for {config.company_id}")
        return CompanyConfig(**config_dict)
        
    except Exception as e:
        logger.error(f"Failed to create company config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company config: {str(e)}"
        )


@router.get("/{company_id}", response_model=CompanyConfig)
async def get_company_config(
    company_id: str,
    api_key: dict = Depends(verify_api_key)
) -> CompanyConfig:
    """
    Get company configuration by ID

    Requires: X-API-Key header
    Note: Can only access own company config

    Args:
        company_id: Unique company identifier
        api_key: Authenticated API key (auto-injected)

    Returns:
        Company configuration
    """
    # Enforce company isolation
    if company_id != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company config not found: {company_id}"
        )

    try:
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)
        config = await collection.find_one({"company_id": company_id})

        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company config not found: {company_id}"
            )
        
        config["_id"] = str(config.get("_id"))
        return CompanyConfig(**config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get company config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get company config: {str(e)}"
        )


@router.put("/{company_id}", response_model=CompanyConfig)
async def update_company_config(
    company_id: str,
    config: CompanyConfigUpdate,
    api_key: dict = Depends(verify_api_key)
) -> CompanyConfig:
    """
    Update company configuration

    Requires: X-API-Key header
    Note: Can only update own company config

    Args:
        company_id: Unique company identifier
        config: Updated configuration fields
        api_key: Authenticated API key (auto-injected)

    Returns:
        Updated company configuration
    """
    # Enforce company isolation
    if company_id != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company config not found: {company_id}"
        )

    try:
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)

        # Remove None values from update dict
        update_dict = {k: v for k, v in config.model_dump().items() if v is not None}
        
        result = await collection.update_one(
            {"company_id": company_id},
            {"$set": update_dict}
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company config not found: {company_id}"
            )
        
        # Return updated config
        updated_config = await collection.find_one({"company_id": company_id})
        updated_config["_id"] = str(updated_config.get("_id"))
        
        logger.info(f"Updated company config for {company_id}")
        return CompanyConfig(**updated_config)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update company config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update company config: {str(e)}"
        )


@router.delete("/{company_id}")
async def delete_company_config(
    company_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Delete company configuration

    Requires: X-API-Key header
    Note: Can only delete own company config

    Args:
        company_id: Unique company identifier
        api_key: Authenticated API key (auto-injected)

    Returns:
        Success message
    """
    # Enforce company isolation
    if company_id != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company config not found: {company_id}"
        )

    try:
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)

        result = await collection.delete_one({"company_id": company_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company config not found: {company_id}"
            )
        
        logger.info(f"Deleted company config for {company_id}")
        return {"message": "Company config deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete company config: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete company config: {str(e)}"
        )


@router.get("/", response_model=List[CompanyConfig])
async def list_company_configs(
    api_key: dict = Depends(verify_api_key)
) -> List[CompanyConfig]:
    """
    List company configurations

    Requires: X-API-Key header
    Note: Returns only own company config (company isolation)

    Args:
        api_key: Authenticated API key (auto-injected)

    Returns:
        List of company configurations (only own company)
    """
    try:
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)
        # Filter by company_id for isolation
        cursor = collection.find({"company_id": api_key["company_id"]})

        configs = []
        async for config in cursor:
            config["_id"] = str(config.get("_id"))
            configs.append(CompanyConfig(**config))

        return configs
        
    except Exception as e:
        logger.error(f"Failed to list company configs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list company configs: {str(e)}"
        )
