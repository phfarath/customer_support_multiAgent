"""
Security Module - AI Guardrails and Prompt Security

This module provides protection against:
- Prompt injection attacks
- Jailbreak attempts
- System prompt leakage
- Sensitive data exposure
- Offensive/inappropriate content
- XSS and injection in outputs

Usage:
    from src.security import (
        get_prompt_sanitizer,
        get_output_validator,
        get_content_moderator,
        ThreatLevel,
        ModerationCategory,
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
]
