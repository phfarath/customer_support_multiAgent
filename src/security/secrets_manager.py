"""
Secrets Manager - Secure secrets handling for different environments

This module provides:
- Unified interface for secrets access across environments
- Support for environment variables (development)
- Support for AWS Secrets Manager (production)
- Secret masking for secure logging

Usage:
    from src.security.secrets_manager import get_secrets_manager, mask_secret

    # Get secrets
    secrets = get_secrets_manager()
    api_key = secrets.get_secret("OPENAI_API_KEY")

    # Mask for logging
    masked = mask_secret(api_key)
    logger.info(f"Using API key: {masked}")
"""

import os
import re
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

logger = logging.getLogger(__name__)


class SecretsManager:
    """
    Unified secrets manager with support for multiple backends.

    In development: reads from environment variables
    In production: reads from AWS Secrets Manager with env var fallback
    """

    def __init__(self, environment: str = "development"):
        """
        Initialize SecretsManager.

        Args:
            environment: Current environment (development, staging, production)
        """
        self.environment = environment
        self._cache: Dict[str, str] = {}
        self._aws_client = None
        self._aws_secret_name: Optional[str] = None

        # Initialize AWS client for production
        if environment == "production":
            self._init_aws_client()

    def _init_aws_client(self) -> None:
        """Initialize AWS Secrets Manager client for production."""
        try:
            import boto3
            self._aws_client = boto3.client(
                'secretsmanager',
                region_name=os.getenv('AWS_REGION', 'us-east-1')
            )
            self._aws_secret_name = os.getenv('AWS_SECRET_NAME', 'customer-support/secrets')
            logger.info("AWS Secrets Manager client initialized")
        except ImportError:
            logger.warning(
                "boto3 not installed. AWS Secrets Manager will not be available. "
                "Install with: pip install boto3"
            )
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager: {e}")

    def _get_from_aws(self, key: str) -> Optional[str]:
        """
        Retrieve secret from AWS Secrets Manager.

        Args:
            key: Secret key to retrieve

        Returns:
            Secret value or None if not found
        """
        if not self._aws_client or not self._aws_secret_name:
            return None

        try:
            import json

            # Check cache first
            if key in self._cache:
                return self._cache[key]

            # Retrieve from AWS
            response = self._aws_client.get_secret_value(
                SecretId=self._aws_secret_name
            )

            # Parse secrets JSON
            if 'SecretString' in response:
                secrets = json.loads(response['SecretString'])
                # Cache all secrets
                self._cache.update(secrets)
                return secrets.get(key)

        except Exception as e:
            logger.warning(f"Failed to retrieve secret from AWS: {e}")

        return None

    def get_secret(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret value by key.

        In production, tries AWS Secrets Manager first, then env vars.
        In development, reads directly from environment variables.

        Args:
            key: Secret key to retrieve
            default: Default value if secret not found

        Returns:
            Secret value or default
        """
        # Production: try AWS first
        if self.environment == "production":
            value = self._get_from_aws(key)
            if value:
                return value

        # Fallback to environment variable
        return os.getenv(key, default)

    def get_secret_required(self, key: str) -> str:
        """
        Get a required secret value. Raises if not found.

        Args:
            key: Secret key to retrieve

        Returns:
            Secret value

        Raises:
            ValueError: If secret is not found
        """
        value = self.get_secret(key)
        if value is None:
            raise ValueError(
                f"Required secret '{key}' not found. "
                f"Set it as an environment variable or in AWS Secrets Manager."
            )
        return value

    def clear_cache(self) -> None:
        """Clear the secrets cache."""
        self._cache.clear()

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"


# Sensitive patterns for masking
SENSITIVE_PATTERNS = [
    # API keys (sk_, api_, pk_, etc.)
    (re.compile(r'(sk_|api_|pk_|key_)[a-zA-Z0-9_-]{20,}', re.IGNORECASE), '[API_KEY_MASKED]'),
    # Bearer tokens
    (re.compile(r'Bearer\s+[a-zA-Z0-9_.-]+', re.IGNORECASE), 'Bearer [TOKEN_MASKED]'),
    # JWT tokens
    (re.compile(r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'), '[JWT_MASKED]'),
    # MongoDB URI with credentials
    (re.compile(r'mongodb(\+srv)?://[^:]+:[^@]+@'), 'mongodb://[MASKED]:[MASKED]@'),
    # Generic passwords in strings
    (re.compile(r'(password|passwd|pwd|secret)["\s:=]+["\']?([^"\'\s]+)["\']?', re.IGNORECASE), r'\1=[MASKED]'),
    # Email addresses (partial mask)
    (re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'), r'\1[at]\2'),
    # Brazilian CPF
    (re.compile(r'\b\d{3}[.-]?\d{3}[.-]?\d{3}[.-]?\d{2}\b'), '[CPF_MASKED]'),
    # Credit card numbers (basic pattern)
    (re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'), '[CARD_MASKED]'),
    # Phone numbers (Brazilian format)
    (re.compile(r'\+?55\s*\d{2}\s*\d{4,5}[- ]?\d{4}'), '[PHONE_MASKED]'),
]


def mask_secret(value: str, show_chars: int = 4) -> str:
    """
    Mask a secret value for safe logging.

    Shows first and last N characters, masks the middle.

    Args:
        value: Secret value to mask
        show_chars: Number of characters to show at start and end

    Returns:
        Masked secret string

    Examples:
        >>> mask_secret("sk_live_abc123def456ghi789")
        'sk_l...i789'
        >>> mask_secret("short")
        '***'
    """
    if not value:
        return "***"

    # Too short to meaningfully mask
    if len(value) <= show_chars * 2:
        return "***"

    return f"{value[:show_chars]}...{value[-show_chars:]}"


def mask_sensitive_data(text: str) -> str:
    """
    Mask all sensitive data patterns in a text string.

    Useful for sanitizing log messages or error outputs.

    Args:
        text: Text that may contain sensitive data

    Returns:
        Text with sensitive data masked

    Examples:
        >>> mask_sensitive_data("API key: sk_live_abc123def456ghi789")
        'API key: [API_KEY_MASKED]'
    """
    if not text:
        return text

    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


# Global secrets manager instance
_secrets_manager: Optional[SecretsManager] = None


def get_secrets_manager(environment: Optional[str] = None) -> SecretsManager:
    """
    Get or create the global SecretsManager instance.

    Args:
        environment: Optional environment override (development, staging, production)

    Returns:
        SecretsManager instance
    """
    global _secrets_manager

    if _secrets_manager is None:
        env = environment or os.getenv('ENVIRONMENT', 'development')
        _secrets_manager = SecretsManager(environment=env)

    return _secrets_manager


def reset_secrets_manager() -> None:
    """Reset the global secrets manager. Useful for testing."""
    global _secrets_manager
    _secrets_manager = None


__all__ = [
    'SecretsManager',
    'get_secrets_manager',
    'reset_secrets_manager',
    'mask_secret',
    'mask_sensitive_data',
    'SENSITIVE_PATTERNS',
]
