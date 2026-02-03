"""
Input sanitization utilities
"""
import re
import html
from typing import Optional, Tuple, List
import logging

from src.utils.pii_detector import redact_pii, has_pii

logger = logging.getLogger(__name__)

# Maximum lengths
MAX_TEXT_LENGTH = 4000          # Messages, descriptions
MAX_SUBJECT_LENGTH = 200        # Ticket subjects
MAX_NAME_LENGTH = 100           # Names, titles
MAX_EMAIL_LENGTH = 255          # Email addresses
MAX_PHONE_LENGTH = 20           # Phone numbers
MAX_ID_LENGTH = 100             # IDs (ticket_id, customer_id, etc)


def sanitize_text(
    text: str, 
    max_length: int = MAX_TEXT_LENGTH,
    redact_pii_data: bool = False
) -> str:
    """
    Sanitize user text input (messages, descriptions, etc)

    Actions:
    - Truncate to max length
    - Remove null bytes
    - Escape HTML entities (prevent XSS)
    - Normalize excessive whitespace
    - Strip leading/trailing whitespace
    - Optionally redact PII (LGPD/GDPR compliance)

    Args:
        text: Raw input text
        max_length: Maximum allowed length
        redact_pii_data: If True, redact detected PII

    Returns:
        Sanitized text safe for storage and display

    Example:
        >>> sanitize_text("<script>alert('XSS')</script>Hello")
        '&lt;script&gt;alert(&#x27;XSS&#x27;)&lt;/script&gt;Hello'
    """
    if not text:
        return ""

    # Truncate
    text = text[:max_length]

    # Remove null bytes (can break databases)
    text = text.replace('\x00', '')

    # Escape HTML to prevent XSS attacks
    text = html.escape(text)

    # Normalize excessive whitespace (but keep newlines)
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs → single space
    text = re.sub(r'\n{3,}', '\n\n', text)  # More than 2 newlines → 2 newlines

    # Strip leading/trailing whitespace
    text = text.strip()

    # Optionally redact PII
    if redact_pii_data:
        text, _, _ = redact_pii(text)

    return text


def sanitize_text_with_pii_detection(
    text: str, 
    max_length: int = MAX_TEXT_LENGTH
) -> Tuple[str, bool, List[str]]:
    """
    Sanitize user text and detect/redact PII.
    
    Combines standard sanitization with PII detection for LGPD/GDPR compliance.
    
    Args:
        text: Raw input text
        max_length: Maximum allowed length
        
    Returns:
        Tuple of (sanitized_text, pii_detected, pii_types)
        - sanitized_text: Sanitized and PII-redacted text
        - pii_detected: True if any PII was found
        - pii_types: List of PII types that were detected
        
    Example:
        >>> sanitize_text_with_pii_detection("Meu CPF é 123.456.789-09")
        ('[CPF REDACTED]', True, ['cpf'])
    """
    if not text:
        return "", False, []
    
    # First apply standard sanitization (without PII redaction)
    sanitized = sanitize_text(text, max_length=max_length, redact_pii_data=False)
    
    # Then detect and redact PII
    redacted_text, pii_detected, pii_types = redact_pii(sanitized)
    
    return redacted_text, pii_detected, pii_types


def sanitize_identifier(identifier: str, max_length: int = MAX_ID_LENGTH) -> str:
    """
    Sanitize identifiers (ticket_id, customer_id, external_user_id, etc)

    Actions:
    - Truncate to max length
    - Remove whitespace
    - Escape HTML
    - Remove null bytes

    Args:
        identifier: Raw identifier
        max_length: Maximum allowed length

    Returns:
        Sanitized identifier

    Example:
        >>> sanitize_identifier("  ticket-123  ")
        'ticket-123'
    """
    if not identifier:
        return ""

    # Remove all whitespace
    identifier = identifier.strip()[:max_length]

    # Remove null bytes
    identifier = identifier.replace('\x00', '')

    # Escape HTML
    identifier = html.escape(identifier)

    return identifier


def sanitize_email(email: str) -> str:
    """
    Sanitize and validate email address

    Actions:
    - Convert to lowercase
    - Trim whitespace
    - Truncate to max length
    - Validate format

    Args:
        email: Email address

    Returns:
        Sanitized email

    Raises:
        ValueError: If email format is invalid

    Example:
        >>> sanitize_email("  User@EXAMPLE.com  ")
        'user@example.com'
    """
    if not email:
        raise ValueError("Email cannot be empty")

    email = email.strip().lower()[:MAX_EMAIL_LENGTH]

    # Basic email validation (RFC 5322 simplified)
    email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_regex.match(email):
        raise ValueError(f"Invalid email format: {email}")

    return email


def sanitize_phone(phone: str) -> str:
    """
    Sanitize phone number

    Actions:
    - Remove all non-digit characters except +
    - Ensure starts with +
    - Truncate to max length

    Args:
        phone: Phone number (can include spaces, dashes, parentheses)

    Returns:
        Normalized phone number (e.g., "+5511999999999")

    Example:
        >>> sanitize_phone("(11) 9999-9999")
        '+11999999999'
        >>> sanitize_phone("11 9999 9999")
        '+11999999999'
    """
    if not phone:
        return ""

    # Remove all except digits and +
    phone = re.sub(r'[^\d+]', '', phone)

    # Ensure starts with +
    if not phone.startswith('+'):
        phone = '+' + phone

    # Truncate
    return phone[:MAX_PHONE_LENGTH]


def sanitize_company_id(company_id: str) -> str:
    """
    Sanitize company_id (alphanumeric + underscores only)

    Args:
        company_id: Company identifier

    Returns:
        Sanitized company_id

    Raises:
        ValueError: If contains invalid characters

    Example:
        >>> sanitize_company_id("techcorp_001")
        'techcorp_001'
        >>> sanitize_company_id("tech corp")
        ValueError: Invalid company_id
    """
    if not company_id:
        raise ValueError("Company ID cannot be empty")

    company_id = company_id.strip()[:50]

    # Only allow alphanumeric + underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', company_id):
        raise ValueError(f"Invalid company_id: must be alphanumeric + underscores")

    return company_id


def sanitize_dict_keys(data: dict, allowed_keys: set) -> dict:
    """
    Filter dictionary to only allowed keys (prevent parameter pollution)

    Args:
        data: Input dictionary
        allowed_keys: Set of allowed keys

    Returns:
        Filtered dictionary

    Example:
        >>> sanitize_dict_keys({"a": 1, "b": 2, "c": 3}, {"a", "b"})
        {'a': 1, 'b': 2}
    """
    filtered = {k: v for k, v in data.items() if k in allowed_keys}

    # Log if any keys were filtered out (security monitoring)
    removed_keys = set(data.keys()) - allowed_keys
    if removed_keys:
        logger.warning(f"Filtered out unexpected keys: {removed_keys}")

    return filtered


# Export all functions
__all__ = [
    "sanitize_text",
    "sanitize_text_with_pii_detection",
    "sanitize_identifier",
    "sanitize_email",
    "sanitize_phone",
    "sanitize_company_id",
    "sanitize_dict_keys",
    "MAX_TEXT_LENGTH",
    "MAX_SUBJECT_LENGTH",
    "MAX_NAME_LENGTH",
]
