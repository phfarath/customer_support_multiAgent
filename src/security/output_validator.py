"""
Output Validator - Validates and sanitizes AI model outputs

This module ensures that AI-generated responses don't contain:
- System prompt leakage
- Sensitive data exposure
- XSS or injection content
- Inappropriate or harmful content
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List, Optional
from html import escape as html_escape

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of output validation"""
    is_valid: bool
    sanitized_output: str
    warnings: List[str] = field(default_factory=list)
    blocked_patterns: List[str] = field(default_factory=list)


# Patterns that indicate system prompt leakage
SYSTEM_PROMPT_LEAKAGE_PATTERNS = [
    r"my\s+(?:system\s+)?(?:prompt|instructions?)\s+(?:say|tell|are|is)",
    r"i\s+(?:was|am)\s+(?:told|instructed|programmed)\s+to",
    r"my\s+(?:original|initial)\s+(?:instructions?|programming)",
    r"according\s+to\s+my\s+(?:system\s+)?(?:prompt|instructions?)",
    r"the\s+system\s+(?:prompt|message)\s+(?:says|tells|instructs)",
    r"i\s+(?:can|cannot|can't)\s+reveal\s+my\s+(?:system\s+)?(?:prompt|instructions?)",
    r"here\s+(?:is|are)\s+my\s+(?:system\s+)?(?:prompt|instructions?)",
]

# Patterns that might indicate sensitive data exposure
SENSITIVE_DATA_PATTERNS = [
    r"(?:api[_\s]?key|apikey)\s*[:=]\s*['\"]?[\w\-]{20,}",
    r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s]{6,}",
    r"(?:secret|token)\s*[:=]\s*['\"]?[\w\-]{10,}",
    r"(?:mongodb|postgres|mysql)(?:\+srv)?://[^\s]+",
    r"(?:sk|pk)[-_](?:live|test)[-_][\w]{20,}",  # Stripe-style keys
    r"(?:AKIA|ASIA)[A-Z0-9]{16}",  # AWS access key pattern
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b.*(?:password|pwd)",  # Email with password context
]

# XSS patterns to sanitize in output
XSS_PATTERNS = [
    r"<script[^>]*>.*?</script>",
    r"<script[^>]*>",
    r"</script>",
    r"javascript\s*:",
    r"on(?:load|error|click|mouseover|submit|focus|blur)\s*=",
    r"<iframe[^>]*>",
    r"<object[^>]*>",
    r"<embed[^>]*>",
    r"<link[^>]*>",
    r"<meta[^>]*>",
]

# Patterns for potentially harmful instructions in output
HARMFUL_INSTRUCTION_PATTERNS = [
    r"to\s+(?:hack|attack|exploit|bypass|break\s+into)",
    r"how\s+to\s+(?:make|create|build)\s+(?:a\s+)?(?:bomb|weapon|explosive)",
    r"(?:credit\s+card|social\s+security)\s+number",
    r"illegal\s+(?:drugs?|substances?|activities?)",
]


class OutputValidator:
    """
    Validates and sanitizes AI model outputs before returning to users.

    Usage:
        validator = OutputValidator()
        result = validator.validate_and_sanitize(model_output)
        if result.is_valid:
            return result.sanitized_output
        else:
            return fallback_response
    """

    def __init__(self, max_output_length: int = 2000):
        """
        Initialize the output validator.

        Args:
            max_output_length: Maximum allowed output length
        """
        self.max_output_length = max_output_length

        # Compile patterns
        self.leakage_regex = re.compile(
            "|".join(SYSTEM_PROMPT_LEAKAGE_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )
        self.sensitive_regex = re.compile(
            "|".join(SENSITIVE_DATA_PATTERNS),
            re.IGNORECASE
        )
        self.xss_regex = re.compile(
            "|".join(XSS_PATTERNS),
            re.IGNORECASE | re.DOTALL
        )
        self.harmful_regex = re.compile(
            "|".join(HARMFUL_INSTRUCTION_PATTERNS),
            re.IGNORECASE
        )

    def validate_and_sanitize(
        self,
        output: str,
        strict_mode: bool = False
    ) -> ValidationResult:
        """
        Validate and sanitize the model output.

        Args:
            output: The model's raw output
            strict_mode: If True, block output on any warning

        Returns:
            ValidationResult with sanitized output and any warnings
        """
        if not output:
            return ValidationResult(
                is_valid=True,
                sanitized_output="",
                warnings=["Empty output"]
            )

        warnings = []
        blocked_patterns = []
        sanitized = output

        # Check for system prompt leakage
        leakage_matches = self.leakage_regex.findall(sanitized)
        if leakage_matches:
            unique_matches = list(set(leakage_matches))[:3]
            blocked_patterns.extend([f"system_leakage: {m}" for m in unique_matches])
            warnings.append("Potential system prompt leakage detected")
            logger.warning(f"System prompt leakage detected: {unique_matches}")

            if strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_output="",
                    warnings=warnings,
                    blocked_patterns=blocked_patterns
                )

            # Redact the leaking content
            for pattern in SYSTEM_PROMPT_LEAKAGE_PATTERNS:
                sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        # Check for sensitive data exposure
        sensitive_matches = self.sensitive_regex.findall(sanitized)
        if sensitive_matches:
            unique_matches = list(set(sensitive_matches))[:3]
            blocked_patterns.extend([f"sensitive_data: {m[:20]}..." for m in unique_matches])
            warnings.append("Potential sensitive data in output")
            logger.warning("Sensitive data pattern detected in output")

            # Always redact sensitive data
            for pattern in SENSITIVE_DATA_PATTERNS:
                sanitized = re.sub(pattern, "[SENSITIVE_REDACTED]", sanitized, flags=re.IGNORECASE)

        # Check for harmful instructions
        harmful_matches = self.harmful_regex.findall(sanitized)
        if harmful_matches:
            blocked_patterns.extend([f"harmful: {m}" for m in list(set(harmful_matches))[:2]])
            warnings.append("Potentially harmful content detected")
            logger.warning(f"Harmful content detected: {harmful_matches}")

            if strict_mode:
                return ValidationResult(
                    is_valid=False,
                    sanitized_output="",
                    warnings=warnings,
                    blocked_patterns=blocked_patterns
                )

        # Sanitize XSS patterns
        xss_matches = self.xss_regex.findall(sanitized)
        if xss_matches:
            warnings.append("XSS patterns removed from output")
            for pattern in XSS_PATTERNS:
                sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE | re.DOTALL)

        # Truncate if too long
        if len(sanitized) > self.max_output_length:
            sanitized = sanitized[:self.max_output_length]
            warnings.append(f"Output truncated to {self.max_output_length} characters")

        # Final cleanup
        sanitized = self._final_cleanup(sanitized)

        # Determine validity
        is_valid = len(blocked_patterns) == 0 or not strict_mode

        return ValidationResult(
            is_valid=is_valid,
            sanitized_output=sanitized,
            warnings=warnings,
            blocked_patterns=blocked_patterns
        )

    def _final_cleanup(self, text: str) -> str:
        """
        Perform final cleanup on the output.

        Args:
            text: Text to clean

        Returns:
            Cleaned text
        """
        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove any remaining suspicious patterns
        text = re.sub(r'<\|[^|]+\|>', '', text)

        return text.strip()

    def escape_for_html(self, text: str) -> str:
        """
        Escape output for safe HTML rendering.

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text
        """
        return html_escape(text)

    def check_response_quality(self, output: str) -> bool:
        """
        Check if the response meets basic quality criteria.

        Args:
            output: The model output

        Returns:
            True if response appears to be quality
        """
        if not output:
            return False

        # Too short responses are suspicious
        if len(output.strip()) < 10:
            return False

        # Check for obvious error/failure patterns
        error_patterns = [
            r"^(?:error|failed|unable|cannot|sorry,?\s+i\s+(?:can't|cannot))",
            r"^i\s+(?:don't|do\s+not)\s+(?:know|understand)",
        ]

        for pattern in error_patterns:
            if re.match(pattern, output.strip(), re.IGNORECASE):
                return False

        return True


# Singleton instance
_output_validator: Optional[OutputValidator] = None


def get_output_validator() -> OutputValidator:
    """Get or create the singleton OutputValidator instance"""
    global _output_validator
    if _output_validator is None:
        _output_validator = OutputValidator()
    return _output_validator
