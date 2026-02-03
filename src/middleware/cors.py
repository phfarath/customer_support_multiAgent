"""
CORS Middleware Configuration

Provides production-safe CORS origin filtering that automatically
removes localhost origins in production environment.
"""
import logging
from typing import List

from src.config import settings

logger = logging.getLogger(__name__)


def get_cors_origins() -> List[str]:
    """
    Get CORS allowed origins, filtering localhost in production.

    In production environment, this function:
    - Filters out any localhost or 127.0.0.1 origins
    - Raises ValueError if no valid origins remain

    In development/staging:
    - Returns all configured origins as-is

    Returns:
        List of allowed CORS origins

    Raises:
        ValueError: If in production and no valid (non-localhost) origins
    """
    origins = settings.cors_allowed_origins.copy()

    if settings.environment == "production":
        # Filter out localhost origins
        filtered_origins = [
            origin for origin in origins
            if "localhost" not in origin.lower() and "127.0.0.1" not in origin
        ]

        if not filtered_origins:
            raise ValueError(
                "No valid CORS origins for production environment. "
                "All configured origins contain localhost/127.0.0.1. "
                "Please configure production domain(s) in CORS_ALLOWED_ORIGINS."
            )

        # Log the filtering if any origins were removed
        removed_origins = set(origins) - set(filtered_origins)
        if removed_origins:
            logger.warning(
                f"CORS: Filtered out localhost origins in production: {removed_origins}"
            )

        return filtered_origins

    return origins


def is_origin_allowed(origin: str) -> bool:
    """
    Check if a specific origin is allowed.

    Args:
        origin: The origin to check

    Returns:
        True if origin is in the allowed list
    """
    allowed = get_cors_origins()
    return origin in allowed
