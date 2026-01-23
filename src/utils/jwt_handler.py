"""
JWT token handler for dashboard authentication
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional
from src.config import settings
import logging

logger = logging.getLogger(__name__)


def create_jwt_token(
    user_id: str,
    company_id: str,
    email: str,
    full_name: str = None,
    role: str = "operator"
) -> str:
    """
    Create JWT token for dashboard authentication

    Args:
        user_id: User ID
        company_id: Company ID (for isolation)
        email: User email
        full_name: User's full name (optional)
        role: User role (operator or admin)

    Returns:
        JWT token string
    """
    payload = {
        "user_id": user_id,
        "company_id": company_id,
        "email": email,
        "full_name": full_name or email,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=settings.jwt_expiration_hours),
        "iat": datetime.utcnow()
    }

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    logger.info(f"JWT token created for user {user_id} (company: {company_id})")
    return token


def verify_jwt_token(token: str) -> Optional[dict]:
    """
    Verify and decode JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid, None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        logger.debug(f"JWT token verified for user {payload.get('user_id')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT token expired")
        return None  # Token expired
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid JWT token: {str(e)}")
        return None  # Invalid token


def refresh_jwt_token(token: str) -> Optional[str]:
    """
    Refresh JWT token if still valid

    Args:
        token: Current JWT token

    Returns:
        New JWT token if valid, None if invalid
    """
    payload = verify_jwt_token(token)
    if not payload:
        return None

    # Create new token with same data
    new_token = create_jwt_token(
        user_id=payload["user_id"],
        company_id=payload["company_id"],
        email=payload["email"],
        full_name=payload.get("full_name"),
        role=payload.get("role", "operator")
    )
    return new_token
