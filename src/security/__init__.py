"""
Security Module - Comprehensive Security for Customer Support System

This module provides protection against:
- Prompt injection attacks
- Jailbreak attempts
- System prompt leakage
- Sensitive data exposure
- Offensive/inappropriate content
- XSS and injection in outputs
- Secrets exposure in logs
- Internal error disclosure

Usage:
    from src.security import (
        # AI Guardrails
        get_prompt_sanitizer,
        get_output_validator,
        get_content_moderator,
        ThreatLevel,
        ModerationCategory,
        # Secrets Management
        get_secrets_manager,
        mask_secret,
        # Error Handling
        SecureError,
        secure_exception_handler,
    )

    # Check for threats
    sanitizer = get_prompt_sanitizer()
    threat_level, threats = sanitizer.detect_threat(user_input)

    # Moderate content
    moderator = get_content_moderator()
    result = moderator.moderate(user_input)

    # Validate output
    validator = get_output_validator()
    validation = validator.validate_and_sanitize(ai_output)

    # Manage secrets
    secrets = get_secrets_manager()
    api_key = secrets.get_secret("OPENAI_API_KEY")

    # Raise secure errors
    raise SecureError("E007", message="Resource not found")
"""

from .prompt_sanitizer import (
    PromptSanitizer,
    get_prompt_sanitizer,
    ThreatLevel,
    INJECTION_PATTERNS,
    JAILBREAK_PATTERNS,
)

from .output_validator import (
    OutputValidator,
    get_output_validator,
    ValidationResult,
)

from .content_moderator import (
    ContentModerator,
    get_content_moderator,
    ModerationCategory,
    ModerationResult,
)

from .secrets_manager import (
    SecretsManager,
    get_secrets_manager,
    reset_secrets_manager,
    mask_secret,
    mask_sensitive_data,
    SENSITIVE_PATTERNS,
)

from .error_handler import (
    SecureError,
    ERROR_CODES,
    DEFAULT_STATUS_CODES,
    generate_trace_id,
    create_error_response,
    secure_exception_handler,
    raise_not_found,
    raise_unauthorized,
    raise_forbidden,
    raise_validation_error,
    raise_rate_limit,
    raise_internal_error,
)

__all__ = [
    # Prompt Sanitizer
    "PromptSanitizer",
    "get_prompt_sanitizer",
    "ThreatLevel",
    "INJECTION_PATTERNS",
    "JAILBREAK_PATTERNS",
    # Output Validator
    "OutputValidator",
    "get_output_validator",
    "ValidationResult",
    # Content Moderator
    "ContentModerator",
    "get_content_moderator",
    "ModerationCategory",
    "ModerationResult",
    # Secrets Manager
    "SecretsManager",
    "get_secrets_manager",
    "reset_secrets_manager",
    "mask_secret",
    "mask_sensitive_data",
    "SENSITIVE_PATTERNS",
    # Error Handler
    "SecureError",
    "ERROR_CODES",
    "DEFAULT_STATUS_CODES",
    "generate_trace_id",
    "create_error_response",
    "secure_exception_handler",
    "raise_not_found",
    "raise_unauthorized",
    "raise_forbidden",
    "raise_validation_error",
    "raise_rate_limit",
    "raise_internal_error",
]
