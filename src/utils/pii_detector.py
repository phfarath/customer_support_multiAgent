"""
PII (Personally Identifiable Information) Detection & Redaction

Detects and redacts sensitive information to ensure LGPD/GDPR compliance.
Uses regex patterns for Brazilian and international PII formats.
"""
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class PIIMatch:
    """Represents a detected PII match"""
    pii_type: str
    original: str
    start: int
    end: int
    redacted: str


# PII Type Constants
PII_CPF = "cpf"
PII_RG = "rg"
PII_CREDIT_CARD = "credit_card"
PII_EMAIL = "email"
PII_PHONE = "phone"
PII_CEP = "cep"
PII_CNH = "cnh"
PII_PASSPORT = "passport"

# Redaction placeholders
REDACTION_PLACEHOLDERS = {
    PII_CPF: "[CPF REDACTED]",
    PII_RG: "[RG REDACTED]",
    PII_CREDIT_CARD: "[CREDIT CARD REDACTED]",
    PII_EMAIL: "[EMAIL REDACTED]",
    PII_PHONE: "[PHONE REDACTED]",
    PII_CEP: "[CEP REDACTED]",
    PII_CNH: "[CNH REDACTED]",
    PII_PASSPORT: "[PASSPORT REDACTED]",
}

# Regex patterns for PII detection (Brazilian + International formats)
PII_PATTERNS = {
    # CPF: 000.000.000-00 or 00000000000
    PII_CPF: re.compile(
        r'\b\d{3}[\.\s]?\d{3}[\.\s]?\d{3}[-\.\s]?\d{2}\b'
    ),
    
    # RG: Various formats (XX.XXX.XXX-X or similar)
    PII_RG: re.compile(
        r'\b\d{1,2}[\.\s]?\d{3}[\.\s]?\d{3}[-\s]?[\dXx]\b'
    ),
    
    # Credit Card: 16 digits with optional spaces/dashes
    # Supports Visa, MasterCard, Amex, etc
    PII_CREDIT_CARD: re.compile(
        r'\b(?:4[0-9]{3}|5[1-5][0-9]{2}|3[47][0-9]{2}|6(?:011|5[0-9]{2}))'
        r'[-\s]?[0-9]{4}[-\s]?[0-9]{4}[-\s]?[0-9]{3,4}\b'
    ),
    
    # Email: Standard email format
    PII_EMAIL: re.compile(
        r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
    ),
    
    # Phone: Brazilian and international formats
    # +55 (11) 99999-9999, (11) 99999-9999, 11999999999, etc
    PII_PHONE: re.compile(
        r'(?:\+\d{1,3}[-\s]?)?\(?\d{2,3}\)?[-\s]?\d{4,5}[-\s]?\d{4}\b'
    ),
    
    # CEP (Brazilian postal code): 00000-000 or 00000000
    PII_CEP: re.compile(
        r'\b\d{5}[-\s]?\d{3}\b'
    ),
    
    # CNH (Brazilian driver's license): 11 digits
    PII_CNH: re.compile(
        r'\b\d{11}\b'
    ),
    
    # Passport: Varies by country, common format AA000000
    PII_PASSPORT: re.compile(
        r'\b[A-Z]{2}\d{6,7}\b'
    ),
}

# Priority order for detection (higher priority first to avoid overlaps)
DETECTION_ORDER = [
    PII_CPF,
    PII_CREDIT_CARD,
    PII_EMAIL,
    PII_PHONE,
    PII_RG,
    PII_CEP,
    PII_CNH,
    PII_PASSPORT,
]


def validate_cpf(cpf: str) -> bool:
    """
    Validate CPF using checksum algorithm.
    
    Args:
        cpf: CPF string (with or without formatting)
        
    Returns:
        True if valid CPF, False otherwise
    """
    # Remove non-digits
    cpf_digits = re.sub(r'\D', '', cpf)
    
    if len(cpf_digits) != 11:
        return False
    
    # Check for known invalid patterns
    if cpf_digits == cpf_digits[0] * 11:
        return False
    
    # Validate first check digit
    sum1 = sum(int(cpf_digits[i]) * (10 - i) for i in range(9))
    d1 = (sum1 * 10 % 11) % 10
    
    if d1 != int(cpf_digits[9]):
        return False
    
    # Validate second check digit
    sum2 = sum(int(cpf_digits[i]) * (11 - i) for i in range(10))
    d2 = (sum2 * 10 % 11) % 10
    
    return d2 == int(cpf_digits[10])


def validate_credit_card(card: str) -> bool:
    """
    Validate credit card using Luhn algorithm.
    
    Args:
        card: Credit card number string
        
    Returns:
        True if valid, False otherwise
    """
    # Remove non-digits
    card_digits = re.sub(r'\D', '', card)
    
    if len(card_digits) < 13 or len(card_digits) > 19:
        return False
    
    # Luhn algorithm
    digits = [int(d) for d in card_digits]
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    
    total = sum(odd_digits)
    for d in even_digits:
        total += sum(divmod(d * 2, 10))
    
    return total % 10 == 0


def detect_pii(text: str, validate: bool = True) -> List[PIIMatch]:
    """
    Detect PII in text using regex patterns.
    
    Args:
        text: Input text to scan
        validate: If True, validate CPF/credit card checksums
        
    Returns:
        List of PIIMatch objects for detected PII
    """
    if not text:
        return []
    
    matches: List[PIIMatch] = []
    used_ranges: List[Tuple[int, int]] = []
    
    for pii_type in DETECTION_ORDER:
        pattern = PII_PATTERNS[pii_type]
        
        for match in pattern.finditer(text):
            start, end = match.span()
            original = match.group()
            
            # Skip if overlaps with already detected PII
            if any(start < r_end and end > r_start for r_start, r_end in used_ranges):
                continue
            
            # Validate if applicable
            if validate:
                if pii_type == PII_CPF and not validate_cpf(original):
                    continue
                if pii_type == PII_CREDIT_CARD and not validate_credit_card(original):
                    continue
            
            # Skip CNH if it doesn't look like a valid document number
            # (too generic - 11 digits can match many things)
            if pii_type == PII_CNH:
                # Only match if preceded by "CNH", "carteira", or "habilitação"
                context_start = max(0, start - 30)
                context = text[context_start:start].lower()
                if not any(kw in context for kw in ['cnh', 'carteira', 'habilitação', 'habilitacao']):
                    continue
            
            matches.append(PIIMatch(
                pii_type=pii_type,
                original=original,
                start=start,
                end=end,
                redacted=REDACTION_PLACEHOLDERS[pii_type]
            ))
            used_ranges.append((start, end))
    
    # Sort by start position
    matches.sort(key=lambda m: m.start)
    
    return matches


def redact_pii(text: str, validate: bool = True) -> Tuple[str, bool, List[str]]:
    """
    Detect and redact PII from text.
    
    Args:
        text: Input text to sanitize
        validate: If True, validate CPF/credit card checksums
        
    Returns:
        Tuple of (redacted_text, pii_detected, pii_types)
        - redacted_text: Text with PII replaced by placeholders
        - pii_detected: True if any PII was found
        - pii_types: List of PII types that were detected
    """
    if not text:
        return text, False, []
    
    matches = detect_pii(text, validate=validate)
    
    if not matches:
        return text, False, []
    
    # Build redacted text by replacing from end to start
    # (to preserve positions)
    redacted_text = text
    pii_types = []
    
    for match in reversed(matches):
        redacted_text = (
            redacted_text[:match.start] + 
            match.redacted + 
            redacted_text[match.end:]
        )
        if match.pii_type not in pii_types:
            pii_types.append(match.pii_type)
    
    # Log PII detection (without revealing the actual data)
    logger.info(f"PII detected and redacted: {pii_types}")
    
    return redacted_text, True, list(reversed(pii_types))


def has_pii(text: str, validate: bool = True) -> bool:
    """
    Check if text contains PII without redacting.
    
    Args:
        text: Input text to check
        validate: If True, validate CPF/credit card checksums
        
    Returns:
        True if PII is detected, False otherwise
    """
    return len(detect_pii(text, validate=validate)) > 0


def get_pii_summary(text: str, validate: bool = True) -> Dict[str, int]:
    """
    Get a summary of PII types found in text.
    
    Args:
        text: Input text to scan
        validate: If True, validate CPF/credit card checksums
        
    Returns:
        Dict mapping PII type to count
    """
    matches = detect_pii(text, validate=validate)
    summary: Dict[str, int] = {}
    
    for match in matches:
        summary[match.pii_type] = summary.get(match.pii_type, 0) + 1
    
    return summary


# Export all public functions and constants
__all__ = [
    "detect_pii",
    "redact_pii",
    "has_pii",
    "get_pii_summary",
    "validate_cpf",
    "validate_credit_card",
    "PIIMatch",
    "PII_CPF",
    "PII_RG",
    "PII_CREDIT_CARD",
    "PII_EMAIL",
    "PII_PHONE",
    "PII_CEP",
    "PII_CNH",
    "PII_PASSPORT",
    "REDACTION_PLACEHOLDERS",
]
