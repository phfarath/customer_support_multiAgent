"""
Secure Logging - Logging with automatic sensitive data masking

This module provides:
- SensitiveDataFilter for automatically masking secrets in logs
- configure_secure_logging() for global secure logging setup
- Patterns for common sensitive data (API keys, passwords, URIs, PII)

Usage:
    from src.utils.secure_logging import configure_secure_logging

    # Configure secure logging globally
    configure_secure_logging()

    # Now all loggers will automatically mask sensitive data
    logger.info(f"Connecting with key {api_key}")  # Key will be masked
"""

import re
import logging
import json
from typing import List, Tuple, Optional, Any, Dict
from logging import LogRecord, Filter, Formatter


# Patterns for sensitive data detection and masking
# Each tuple: (compiled regex pattern, replacement string)
SENSITIVE_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # API Keys (various formats)
    (re.compile(r'(sk_live_|sk_test_|pk_live_|pk_test_)[a-zA-Z0-9]{20,}', re.IGNORECASE), '[API_KEY_REDACTED]'),
    (re.compile(r'(api[_-]?key|apikey)["\s:=]+["\']?([a-zA-Z0-9_-]{20,})["\']?', re.IGNORECASE), r'\1=[REDACTED]'),
    (re.compile(r'(key_)[a-zA-Z0-9]{16,}', re.IGNORECASE), '[KEY_REDACTED]'),

    # OpenAI API Keys
    (re.compile(r'sk-[a-zA-Z0-9]{48,}'), '[OPENAI_KEY_REDACTED]'),
    (re.compile(r'sk-proj-[a-zA-Z0-9_-]{50,}'), '[OPENAI_PROJECT_KEY_REDACTED]'),

    # Bearer/Auth tokens
    (re.compile(r'(Bearer\s+)[a-zA-Z0-9_.-]+', re.IGNORECASE), r'\1[TOKEN_REDACTED]'),
    (re.compile(r'(Authorization:\s*)[^\s]+', re.IGNORECASE), r'\1[REDACTED]'),

    # JWT tokens (3 base64 parts separated by dots)
    (re.compile(r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+'), '[JWT_REDACTED]'),

    # Passwords
    (re.compile(r'(password|passwd|pwd|secret|token)["\s:=]+["\']?([^\s"\']{4,})["\']?', re.IGNORECASE), r'\1=[REDACTED]'),

    # MongoDB URIs with credentials
    (re.compile(r'mongodb(\+srv)?://([^:]+):([^@]+)@'), r'mongodb\1://[USER]:[PASS]@'),

    # PostgreSQL/MySQL URIs with credentials
    (re.compile(r'(postgres|mysql|postgresql)://([^:]+):([^@]+)@'), r'\1://[USER]:[PASS]@'),

    # Redis URIs with credentials
    (re.compile(r'redis://(:?)([^@]+)@'), r'redis://[PASS]@'),

    # AWS credentials
    (re.compile(r'(AKIA|ABIA|ACCA|ASIA)[A-Z0-9]{16}'), '[AWS_KEY_REDACTED]'),
    (re.compile(r'(aws_secret_access_key|aws_access_key_id)["\s:=]+["\']?([^\s"\']+)["\']?', re.IGNORECASE), r'\1=[REDACTED]'),

    # Email addresses (aggressive masking - hide both local part and most of domain)
    (re.compile(r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+)\.([a-zA-Z]{2,})'), lambda m: f"{m.group(1)[:1]}***@***.{m.group(3)}"),

    # Brazilian CPF
    (re.compile(r'\b(\d{3})[.-]?(\d{3})[.-]?(\d{3})[.-]?(\d{2})\b'), r'***.\1.***-**'),

    # Brazilian CNPJ
    (re.compile(r'\b(\d{2})[.-]?(\d{3})[.-]?(\d{3})[/]?(\d{4})[.-]?(\d{2})\b'), r'**.\1.***/****.***-**'),

    # Credit card numbers (basic Luhn-compatible patterns)
    (re.compile(r'\b(\d{4})[- ]?(\d{4})[- ]?(\d{4})[- ]?(\d{4})\b'), r'****-****-****-\4'),

    # Phone numbers (Brazilian format)
    (re.compile(r'(\+?55\s*)?(\(?[1-9]{2}\)?)\s*(\d{4,5})[- ]?(\d{4})'), r'+55 (**) *****-\4'),

    # IP addresses (internal)
    (re.compile(r'\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3})\b'), '[INTERNAL_IP]'),
    (re.compile(r'\b(192\.168\.\d{1,3}\.\d{1,3})\b'), '[INTERNAL_IP]'),
    (re.compile(r'\b(172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3})\b'), '[INTERNAL_IP]'),

    # File paths that might contain sensitive info
    (re.compile(r'/home/[^/\s]+'), '/home/[USER]'),
    (re.compile(r'/Users/[^/\s]+'), '/Users/[USER]'),
    (re.compile(r'C:\\Users\\[^\\]+'), r'C:\\Users\\[USER]'),

    # Telegram bot tokens
    (re.compile(r'\b(\d{8,10}):([A-Za-z0-9_-]{35})\b'), '[TELEGRAM_TOKEN_REDACTED]'),

    # SMTP credentials in URLs
    (re.compile(r'smtp://([^:]+):([^@]+)@'), r'smtp://[USER]:[PASS]@'),

    # Generic secret patterns
    (re.compile(r'(secret[_-]?key|private[_-]?key|access[_-]?token)["\s:=]+["\']?([^\s"\']{8,})["\']?', re.IGNORECASE), r'\1=[REDACTED]'),
]


class SensitiveDataFilter(Filter):
    """
    Logging filter that masks sensitive data in log messages.

    Automatically detects and masks:
    - API keys
    - Passwords
    - Tokens
    - Database URIs
    - PII (CPF, credit cards, phone numbers)
    - Internal IP addresses
    """

    def __init__(self, name: str = '', additional_patterns: Optional[List[Tuple[re.Pattern, str]]] = None):
        """
        Initialize SensitiveDataFilter.

        Args:
            name: Filter name
            additional_patterns: Additional regex patterns to mask
        """
        super().__init__(name)
        self.patterns = SENSITIVE_PATTERNS.copy()
        if additional_patterns:
            self.patterns.extend(additional_patterns)

    def filter(self, record: LogRecord) -> bool:
        """
        Filter log record and mask sensitive data.

        Args:
            record: Log record to process

        Returns:
            True (always passes the record, but masks sensitive data)
        """
        # Mask the main message
        if record.msg:
            record.msg = self._mask_sensitive(str(record.msg))

        # Mask arguments if present
        if record.args:
            if isinstance(record.args, dict):
                record.args = {k: self._mask_sensitive(str(v)) for k, v in record.args.items()}
            elif isinstance(record.args, (list, tuple)):
                record.args = tuple(self._mask_sensitive(str(arg)) for arg in record.args)

        # Mask extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ('msg', 'args', 'name', 'levelname', 'levelno', 'pathname',
                               'filename', 'module', 'lineno', 'funcName', 'created',
                               'msecs', 'relativeCreated', 'thread', 'threadName',
                               'processName', 'process', 'exc_info', 'exc_text', 'stack_info'):
                    if isinstance(value, str):
                        setattr(record, key, self._mask_sensitive(value))
                    elif isinstance(value, dict):
                        setattr(record, key, self._mask_dict(value))

        return True

    def _mask_sensitive(self, text: str) -> str:
        """Apply all masking patterns to text."""
        if not text:
            return text

        result = text
        for pattern, replacement in self.patterns:
            if callable(replacement):
                result = pattern.sub(replacement, result)
            else:
                result = pattern.sub(replacement, result)

        return result

    def _mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive data in a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._mask_sensitive(value)
            elif isinstance(value, dict):
                result[key] = self._mask_dict(value)
            elif isinstance(value, (list, tuple)):
                result[key] = [
                    self._mask_sensitive(str(v)) if isinstance(v, str) else v
                    for v in value
                ]
            else:
                result[key] = value
        return result


class SecureFormatter(Formatter):
    """
    Log formatter that includes trace ID and masks sensitive data.

    Format includes:
    - Timestamp
    - Log level
    - Logger name
    - Trace ID (if present)
    - Message (with sensitive data masked)
    """

    def __init__(
        self,
        fmt: Optional[str] = None,
        datefmt: Optional[str] = None,
        include_trace_id: bool = True,
    ):
        """
        Initialize SecureFormatter.

        Args:
            fmt: Log format string
            datefmt: Date format string
            include_trace_id: Whether to include trace_id in output
        """
        if fmt is None:
            if include_trace_id:
                fmt = '%(asctime)s - %(name)s - %(levelname)s - [%(trace_id)s] - %(message)s'
            else:
                fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        super().__init__(fmt, datefmt)
        self.include_trace_id = include_trace_id
        self._sensitive_filter = SensitiveDataFilter()

    def format(self, record: LogRecord) -> str:
        """Format log record with sensitive data masking."""
        # Ensure trace_id exists (use '-' if not present)
        if self.include_trace_id and not hasattr(record, 'trace_id'):
            record.trace_id = '-'

        # Apply sensitive data masking
        self._sensitive_filter.filter(record)

        return super().format(record)


class JSONSecureFormatter(Formatter):
    """
    JSON log formatter with sensitive data masking.

    Outputs structured JSON logs suitable for log aggregation systems.
    """

    def __init__(self):
        super().__init__()
        self._sensitive_filter = SensitiveDataFilter()

    def format(self, record: LogRecord) -> str:
        """Format log record as JSON with sensitive data masked."""
        # Apply sensitive data masking
        self._sensitive_filter.filter(record)

        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
        }

        # Add trace_id if present
        if hasattr(record, 'trace_id'):
            log_data['trace_id'] = record.trace_id

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ('msg', 'args', 'name', 'levelname', 'levelno', 'pathname',
                           'filename', 'module', 'lineno', 'funcName', 'created',
                           'msecs', 'relativeCreated', 'thread', 'threadName',
                           'processName', 'process', 'exc_info', 'exc_text', 'stack_info',
                           'message', 'trace_id'):
                if not key.startswith('_'):
                    log_data[key] = value

        return json.dumps(log_data)


def configure_secure_logging(
    level: int = logging.INFO,
    format_type: str = 'text',  # 'text' or 'json'
    include_trace_id: bool = True,
    additional_patterns: Optional[List[Tuple[re.Pattern, str]]] = None,
) -> None:
    """
    Configure secure logging globally.

    Sets up logging with automatic sensitive data masking.

    Args:
        level: Logging level
        format_type: 'text' for human-readable, 'json' for structured logs
        include_trace_id: Include trace_id in log output
        additional_patterns: Additional regex patterns to mask

    Example:
        configure_secure_logging(level=logging.DEBUG, format_type='json')
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter(additional_patterns=additional_patterns)
    console_handler.addFilter(sensitive_filter)

    # Set formatter
    if format_type == 'json':
        formatter = JSONSecureFormatter()
    else:
        formatter = SecureFormatter(include_trace_id=include_trace_id)

    console_handler.setFormatter(formatter)

    # Add handler to root logger
    root_logger.addHandler(console_handler)


def get_secure_logger(name: str) -> logging.Logger:
    """
    Get a logger with secure filtering already applied.

    Args:
        name: Logger name

    Returns:
        Logger with SensitiveDataFilter applied
    """
    logger = logging.getLogger(name)

    # Check if filter already applied
    has_filter = any(isinstance(f, SensitiveDataFilter) for f in logger.filters)
    if not has_filter:
        logger.addFilter(SensitiveDataFilter())

    return logger


__all__ = [
    'SensitiveDataFilter',
    'SecureFormatter',
    'JSONSecureFormatter',
    'SENSITIVE_PATTERNS',
    'configure_secure_logging',
    'get_secure_logger',
]
