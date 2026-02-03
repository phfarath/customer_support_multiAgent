"""
Secure Error Handler - Safe error handling without exposing internal details

This module provides:
- SecureError class for creating safe exceptions
- Error codes mapped to user-friendly messages
- Trace ID generation for log correlation
- Global FastAPI exception handler

Usage:
    from src.security.error_handler import SecureError, secure_exception_handler

    # Raise a secure error
    raise SecureError("E002", status_code=503)

    # In FastAPI main.py
    app.add_exception_handler(Exception, secure_exception_handler)
"""

import uuid
import logging
import traceback
from typing import Optional, Dict, Any
from datetime import datetime
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


# Error codes mapped to user-friendly messages
# These messages are safe to show to end users
ERROR_CODES: Dict[str, str] = {
    "E001": "An internal server error occurred. Please try again later.",
    "E002": "Database connection error. Our team has been notified.",
    "E003": "External service temporarily unavailable. Please try again.",
    "E004": "Invalid request format. Please check your input.",
    "E005": "Authentication failed. Please check your credentials.",
    "E006": "You don't have permission to access this resource.",
    "E007": "The requested resource was not found.",
    "E008": "Too many requests. Please wait before trying again.",
    "E009": "Validation error. Please check the provided data.",
    "E010": "Service temporarily unavailable. Please try again later.",
    "E011": "Request timeout. Please try again.",
    "E012": "Configuration error. Please contact support.",
}

# Default HTTP status codes for each error type
DEFAULT_STATUS_CODES: Dict[str, int] = {
    "E001": 500,
    "E002": 503,
    "E003": 503,
    "E004": 400,
    "E005": 401,
    "E006": 403,
    "E007": 404,
    "E008": 429,
    "E009": 422,
    "E010": 503,
    "E011": 504,
    "E012": 500,
}


def generate_trace_id() -> str:
    """
    Generate a unique trace ID for error correlation.

    Returns:
        A unique trace ID string (UUID4)
    """
    return str(uuid.uuid4())


class SecureError(Exception):
    """
    Secure exception class that doesn't expose internal details.

    Attributes:
        code: Error code (E001-E012)
        message: User-friendly message (auto-generated from code if not provided)
        status_code: HTTP status code to return
        trace_id: Unique ID for log correlation
        internal_message: Detailed message for logging (never exposed to client)
        context: Additional context for logging (never exposed to client)
    """

    def __init__(
        self,
        code: str,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        internal_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize SecureError.

        Args:
            code: Error code (E001-E012)
            message: Optional custom user-friendly message
            status_code: Optional HTTP status code (defaults based on code)
            internal_message: Detailed message for logging (not exposed)
            context: Additional context for logging (not exposed)
        """
        self.code = code
        self.message = message or ERROR_CODES.get(code, ERROR_CODES["E001"])
        self.status_code = status_code or DEFAULT_STATUS_CODES.get(code, 500)
        self.trace_id = generate_trace_id()
        self.internal_message = internal_message
        self.context = context or {}
        self.timestamp = datetime.utcnow().isoformat()

        super().__init__(self.message)

    def to_response(self) -> Dict[str, Any]:
        """
        Convert to a safe response dict.

        Returns:
            Dict with error details safe for client
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "trace_id": self.trace_id,
                "timestamp": self.timestamp,
            }
        }

    def log_error(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """
        Log the error with full details (for debugging).

        Args:
            logger_instance: Optional logger to use
        """
        log = logger_instance or logger
        log.error(
            f"SecureError [{self.code}]: {self.internal_message or self.message}",
            extra={
                "error_code": self.code,
                "trace_id": self.trace_id,
                "status_code": self.status_code,
                "context": self.context,
                "timestamp": self.timestamp,
            }
        )


def create_error_response(
    code: str,
    message: Optional[str] = None,
    status_code: Optional[int] = None,
    internal_error: Optional[Exception] = None,
    context: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """
    Create a secure JSON error response.

    Args:
        code: Error code (E001-E012)
        message: Optional custom user-friendly message
        status_code: Optional HTTP status code
        internal_error: Original exception (for logging only)
        context: Additional context for logging

    Returns:
        FastAPI JSONResponse with error details
    """
    trace_id = generate_trace_id()
    timestamp = datetime.utcnow().isoformat()
    final_status = status_code or DEFAULT_STATUS_CODES.get(code, 500)
    final_message = message or ERROR_CODES.get(code, ERROR_CODES["E001"])

    # Log the full error details
    logger.error(
        f"Error [{code}] trace_id={trace_id}",
        extra={
            "error_code": code,
            "trace_id": trace_id,
            "status_code": final_status,
            "context": context or {},
            "internal_error": str(internal_error) if internal_error else None,
        },
        exc_info=internal_error is not None,
    )

    return JSONResponse(
        status_code=final_status,
        content={
            "error": {
                "code": code,
                "message": final_message,
                "trace_id": trace_id,
                "timestamp": timestamp,
            }
        }
    )


async def secure_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Global exception handler for FastAPI that never exposes internal details.

    Register with: app.add_exception_handler(Exception, secure_exception_handler)

    Args:
        request: FastAPI request
        exc: Exception that was raised

    Returns:
        Secure JSONResponse
    """
    # Handle our custom SecureError
    if isinstance(exc, SecureError):
        exc.log_error()
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response()
        )

    # Handle FastAPI/Starlette HTTPException
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        trace_id = generate_trace_id()
        timestamp = datetime.utcnow().isoformat()

        # Map HTTP status codes to our error codes
        code = _http_status_to_error_code(exc.status_code)

        logger.warning(
            f"HTTPException [{code}] trace_id={trace_id}: {exc.detail}",
            extra={
                "trace_id": trace_id,
                "status_code": exc.status_code,
                "path": str(request.url),
                "method": request.method,
            }
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": exc.detail if _is_safe_message(str(exc.detail)) else ERROR_CODES.get(code, ERROR_CODES["E001"]),
                    "trace_id": trace_id,
                    "timestamp": timestamp,
                }
            }
        )

    # Handle unexpected exceptions - never expose details
    trace_id = generate_trace_id()
    timestamp = datetime.utcnow().isoformat()

    # Log full exception details internally
    logger.error(
        f"Unhandled exception trace_id={trace_id}",
        extra={
            "trace_id": trace_id,
            "exception_type": type(exc).__name__,
            "path": str(request.url),
            "method": request.method,
        },
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "E001",
                "message": ERROR_CODES["E001"],
                "trace_id": trace_id,
                "timestamp": timestamp,
            }
        }
    )


def _http_status_to_error_code(status_code: int) -> str:
    """Map HTTP status codes to our error codes."""
    mapping = {
        400: "E004",
        401: "E005",
        403: "E006",
        404: "E007",
        422: "E009",
        429: "E008",
        500: "E001",
        502: "E003",
        503: "E010",
        504: "E011",
    }
    return mapping.get(status_code, "E001")


def _is_safe_message(message: str) -> bool:
    """
    Check if an error message is safe to expose to clients.

    Unsafe patterns include stack traces, file paths, internal errors, etc.
    """
    unsafe_patterns = [
        "Traceback",
        "File \"",
        "line ",
        "Exception:",
        "Error:",
        "at 0x",
        "/usr/",
        "/home/",
        "/var/",
        "pymongo",
        "motor",
        "asyncio",
        "openai",
        "mongodb",
        "localhost",
        "127.0.0.1",
        ".py",
    ]

    message_lower = message.lower()
    return not any(pattern.lower() in message_lower for pattern in unsafe_patterns)


# Convenience functions for common errors
def raise_not_found(resource: str = "Resource", internal_msg: Optional[str] = None) -> None:
    """Raise a 404 Not Found error."""
    raise SecureError(
        "E007",
        message=f"{resource} not found.",
        internal_message=internal_msg,
    )


def raise_unauthorized(internal_msg: Optional[str] = None) -> None:
    """Raise a 401 Unauthorized error."""
    raise SecureError(
        "E005",
        internal_message=internal_msg,
    )


def raise_forbidden(internal_msg: Optional[str] = None) -> None:
    """Raise a 403 Forbidden error."""
    raise SecureError(
        "E006",
        internal_message=internal_msg,
    )


def raise_validation_error(field: str, message: str) -> None:
    """Raise a 422 Validation error."""
    raise SecureError(
        "E009",
        message=f"Validation error: {message}",
        context={"field": field},
    )


def raise_rate_limit() -> None:
    """Raise a 429 Rate Limit error."""
    raise SecureError("E008")


def raise_internal_error(internal_msg: Optional[str] = None, context: Optional[Dict] = None) -> None:
    """Raise a 500 Internal Server error."""
    raise SecureError(
        "E001",
        internal_message=internal_msg,
        context=context,
    )


__all__ = [
    'SecureError',
    'ERROR_CODES',
    'DEFAULT_STATUS_CODES',
    'generate_trace_id',
    'create_error_response',
    'secure_exception_handler',
    'raise_not_found',
    'raise_unauthorized',
    'raise_forbidden',
    'raise_validation_error',
    'raise_rate_limit',
    'raise_internal_error',
]
