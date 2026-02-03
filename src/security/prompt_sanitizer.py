"""
Prompt Sanitizer - Protection against prompt injection and jailbreak attacks

This module provides detection and sanitization of potentially malicious prompts
that could be used to manipulate the AI's behavior or extract sensitive information.
"""
import re
import logging
from enum import Enum
from typing import Tuple, List
from html import escape as html_escape

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Threat level classification for detected attacks"""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Patterns for detecting prompt injection attempts
INJECTION_PATTERNS = [
    # Instruction override attempts
    r"ignore\s+(?:all\s+|the\s+|previous\s+|above\s+)?(?:instructions?|rules?|guidelines?)",
    r"disregard\s+(?:all\s+|the\s+|previous\s+|above\s+)?(?:instructions?|rules?|guidelines?)",
    r"forget\s+(?:all\s+|the\s+|previous\s+|above\s+)?(?:instructions?|rules?|guidelines?)",
    r"override\s+(?:all\s+|the\s+|previous\s+|above\s+)?(?:instructions?|rules?|guidelines?)",
    r"new\s+instructions?\s*:",
    r"system\s+prompt\s*:",
    r"you\s+are\s+now\b",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?",
    r"pretend\s+(?:to\s+be|you\s+are|that\s+you)",
    r"roleplay\s+as",
    r"from\s+now\s+on\s*,?\s*you",

    # Role/context manipulation (token delimiters used by various models)
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[/INST\]",
    r"<<SYS>>",
    r"<</SYS>>",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",

    # Data exfiltration attempts
    r"reveal\s+(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?|rules?)",
    r"what\s+(?:are|is)\s+your\s+(?:system\s+)?(?:prompt|instructions?|rules?)",
    r"show\s+(?:me\s+)?(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?|rules?)",
    r"print\s+(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?)",
    r"output\s+(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?)",
    r"repeat\s+(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?)",
    r"tell\s+me\s+(?:your\s+|the\s+)?(?:system\s+)?(?:prompt|instructions?)",

    # Code execution attempts
    r"execute\s+(?:this\s+)?(?:code|command|script)",
    r"run\s+(?:this\s+)?(?:code|command|script)",
    r"eval\s*\(",
    r"exec\s*\(",
]

# Patterns for detecting jailbreak attempts
JAILBREAK_PATTERNS = [
    r"DAN\s*mode",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"bypass\s+(?:safety|content|moderation|filter|restriction)",
    r"evil\s+mode",
    r"developer\s+mode",
    r"unrestricted\s+mode",
    r"sudo\s+mode",
    r"god\s+mode",
    r"no\s+(?:rules?|restrictions?|limits?|filters?)",
    r"without\s+(?:rules?|restrictions?|limits?|filters?)",
    r"remove\s+(?:all\s+)?(?:restrictions?|limits?|filters?|safety)",
    r"disable\s+(?:safety|content|moderation|filter)",
    r"turn\s+off\s+(?:safety|content|moderation|filter)",
    r"uncensored",
    r"unfiltered",
    r"no\s+censorship",
]

# Patterns for delimiter injection (content boundary manipulation)
DELIMITER_PATTERNS = [
    r"```(?:system|assistant|user)",
    r"={3,}",
    r"-{3,}",
    r"\*{3,}",
    r"#{3,}\s*(?:system|instructions?|rules?)",
]


class PromptSanitizer:
    """
    Sanitizes user inputs and detects potential prompt injection/jailbreak attempts.

    Usage:
        sanitizer = PromptSanitizer()
        threat_level, threats = sanitizer.detect_threat(user_input)
        if threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            # Refuse to process
            pass
        else:
            sanitized = sanitizer.wrap_user_content(user_input, "CUSTOMER_MESSAGE")
    """

    def __init__(self):
        """Initialize the sanitizer with compiled regex patterns"""
        # Compile patterns for efficiency
        self.injection_regex = re.compile(
            "|".join(INJECTION_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
        self.jailbreak_regex = re.compile(
            "|".join(JAILBREAK_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
        self.delimiter_regex = re.compile(
            "|".join(DELIMITER_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )

    def detect_threat(self, text: str) -> Tuple[ThreatLevel, List[str]]:
        """
        Detect potential threats in the input text.

        Args:
            text: The text to analyze

        Returns:
            Tuple of (ThreatLevel, list of detected threat descriptions)
        """
        if not text:
            return ThreatLevel.SAFE, []

        threats = []
        text_lower = text.lower()

        # Check jailbreak patterns (highest priority - these are intentional attacks)
        jailbreak_matches = self.jailbreak_regex.findall(text_lower)
        if jailbreak_matches:
            unique_matches = list(set(jailbreak_matches))
            threats.extend([f"jailbreak_attempt: {m}" for m in unique_matches[:3]])
            logger.warning(f"Jailbreak attempt detected: {unique_matches}")
            return ThreatLevel.CRITICAL, threats

        # Check injection patterns
        injection_matches = self.injection_regex.findall(text_lower)
        if injection_matches:
            unique_matches = list(set(injection_matches))
            threats.extend([f"prompt_injection: {m}" for m in unique_matches[:3]])
            logger.warning(f"Prompt injection detected: {unique_matches}")

            # Multiple injection attempts = higher threat
            if len(unique_matches) >= 3:
                return ThreatLevel.HIGH, threats
            elif len(unique_matches) >= 2:
                return ThreatLevel.MEDIUM, threats
            return ThreatLevel.LOW, threats

        # Check delimiter injection (potential context escape)
        delimiter_matches = self.delimiter_regex.findall(text)
        if delimiter_matches:
            unique_matches = list(set(delimiter_matches))
            threats.extend([f"delimiter_injection: {m}" for m in unique_matches[:2]])
            logger.info(f"Delimiter patterns detected: {unique_matches}")
            return ThreatLevel.LOW, threats

        return ThreatLevel.SAFE, []

    def sanitize_user_input(self, text: str, max_length: int = 4000) -> str:
        """
        Sanitize user input for safe inclusion in prompts.

        Args:
            text: The user input to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Truncate to max length
        text = text[:max_length]

        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace (but preserve single newlines for readability)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove or escape special tokens that could be used for context manipulation
        # Replace common delimiter patterns with safe alternatives
        text = re.sub(r'```+', '[code]', text)
        text = re.sub(r'===+', '---', text)
        text = re.sub(r'---{3,}', '---', text)

        # Remove role manipulation tokens
        text = re.sub(r'<\|[^|]+\|>', '', text)
        text = re.sub(r'\[/?INST\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'<<?/?SYS>?>?', '', text, flags=re.IGNORECASE)

        return text.strip()

    def wrap_user_content(self, text: str, label: str = "USER_INPUT") -> str:
        """
        Wrap user content with clear delimiters to prevent context escape.

        The XML-style tags help the model understand the boundary between
        user content and system instructions.

        Args:
            text: The user content to wrap
            label: Label for the content (e.g., CUSTOMER_MESSAGE, CONVERSATION_HISTORY)

        Returns:
            Wrapped and sanitized content
        """
        sanitized = self.sanitize_user_input(text)

        # Use XML-style tags that are unlikely to appear in user content
        return f"<{label}>\n{sanitized}\n</{label}>"

    def sanitize_kb_result(self, text: str, max_length: int = 2000) -> str:
        """
        Sanitize knowledge base results before including in prompt.

        KB results could potentially contain injected content if the
        knowledge base was compromised.

        Args:
            text: The KB result text
            max_length: Maximum allowed length

        Returns:
            Sanitized KB text
        """
        if not text:
            return ""

        # Apply same sanitization as user input
        sanitized = self.sanitize_user_input(text, max_length)

        # Wrap in clear delimiter
        return f"<KNOWLEDGE_BASE>\n{sanitized}\n</KNOWLEDGE_BASE>"

    def escape_for_display(self, text: str) -> str:
        """
        Escape text for safe display (prevents XSS if rendered in HTML).

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text
        """
        return html_escape(text)


# Singleton instance for convenience
_prompt_sanitizer: PromptSanitizer = None


def get_prompt_sanitizer() -> PromptSanitizer:
    """Get or create the singleton PromptSanitizer instance"""
    global _prompt_sanitizer
    if _prompt_sanitizer is None:
        _prompt_sanitizer = PromptSanitizer()
    return _prompt_sanitizer
