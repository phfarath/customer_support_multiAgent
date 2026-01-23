"""
Sentry Integration for Error Tracking and Performance Monitoring

This module configures Sentry for:
- Automatic error tracking
- Performance monitoring (APM)
- Request tracking
- User context
- Custom tags and breadcrumbs
- Release tracking
- Environment-specific configuration

Usage:
    from src.utils.monitoring import init_sentry

    # In main.py or app startup
    init_sentry()
"""

import logging
import os
from typing import Optional, Dict, Any
from functools import wraps

try:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.pymongo import PyMongoIntegration
    SENTRY_AVAILABLE = True
except ImportError:
    SENTRY_AVAILABLE = False
    logging.warning("sentry-sdk not installed. Error tracking disabled.")


logger = logging.getLogger(__name__)


def init_sentry(
    dsn: Optional[str] = None,
    environment: Optional[str] = None,
    release: Optional[str] = None,
    traces_sample_rate: float = 1.0,
    profiles_sample_rate: float = 1.0,
    enable_tracing: bool = True,
    send_default_pii: bool = False,
) -> bool:
    """
    Initialize Sentry SDK with FastAPI integration

    Args:
        dsn: Sentry DSN (or set SENTRY_DSN env var)
        environment: Environment name (production/staging/development)
        release: Release version (e.g., git commit hash)
        traces_sample_rate: APM sampling rate (0.0 - 1.0)
        profiles_sample_rate: Profiling sampling rate (0.0 - 1.0)
        enable_tracing: Enable performance monitoring
        send_default_pii: Send personally identifiable information

    Returns:
        bool: True if Sentry initialized successfully, False otherwise

    Environment Variables:
        SENTRY_DSN: Sentry project DSN
        SENTRY_ENVIRONMENT: Environment name (default: production)
        SENTRY_RELEASE: Release version (default: auto-detected from git)
        SENTRY_TRACES_SAMPLE_RATE: APM sample rate (default: 1.0)
        SENTRY_PROFILES_SAMPLE_RATE: Profiling sample rate (default: 1.0)
    """

    if not SENTRY_AVAILABLE:
        logger.warning("Sentry SDK not available. Skipping initialization.")
        return False

    # Get configuration from environment or parameters
    dsn = dsn or os.getenv("SENTRY_DSN")

    if not dsn:
        logger.info("SENTRY_DSN not configured. Error tracking disabled.")
        return False

    environment = environment or os.getenv("SENTRY_ENVIRONMENT", "production")
    release = release or os.getenv("SENTRY_RELEASE") or _get_git_release()

    traces_sample_rate = float(
        os.getenv("SENTRY_TRACES_SAMPLE_RATE", str(traces_sample_rate))
    )
    profiles_sample_rate = float(
        os.getenv("SENTRY_PROFILES_SAMPLE_RATE", str(profiles_sample_rate))
    )

    # Configure integrations
    integrations = [
        # FastAPI integration for automatic request tracking
        FastApiIntegration(
            transaction_style="url",  # Use URL pattern as transaction name
            failed_request_status_codes=[500, 599],  # Track 5xx as errors
        ),

        # Logging integration (capture logs as breadcrumbs)
        LoggingIntegration(
            level=logging.INFO,  # Capture info and above as breadcrumbs
            event_level=logging.ERROR  # Send errors as events
        ),

        # MongoDB integration (if using pymongo)
        PyMongoIntegration(),
    ]

    # Initialize Sentry
    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            integrations=integrations,
            traces_sample_rate=traces_sample_rate if enable_tracing else 0.0,
            profiles_sample_rate=profiles_sample_rate if enable_tracing else 0.0,
            send_default_pii=send_default_pii,

            # Additional configuration
            attach_stacktrace=True,  # Attach stack traces to messages
            request_bodies="medium",  # Include request body in events
            max_breadcrumbs=50,  # Keep last 50 breadcrumbs

            # Filter out health check noise
            before_send=_before_send_filter,

            # Custom tags
            _experiments={
                "profiles_sample_rate": profiles_sample_rate,
            }
        )

        logger.info(
            f"✓ Sentry initialized - Environment: {environment}, "
            f"Release: {release}, Tracing: {enable_tracing}"
        )

        # Set default tags
        _set_default_tags()

        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def _get_git_release() -> Optional[str]:
    """Get git commit hash as release version"""
    try:
        import subprocess
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        return f"customer-support@{git_hash}"
    except Exception:
        return None


def _set_default_tags():
    """Set default tags for all Sentry events"""
    if not SENTRY_AVAILABLE:
        return

    sentry_sdk.set_tag("application", "customer-support-multiagent")
    sentry_sdk.set_tag("service", "api")

    # Add Python version
    import sys
    sentry_sdk.set_tag("python_version", f"{sys.version_info.major}.{sys.version_info.minor}")


def _before_send_filter(event: Dict[str, Any], hint: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Filter events before sending to Sentry

    Args:
        event: Sentry event dict
        hint: Additional context

    Returns:
        Event dict or None to drop the event
    """
    # Don't send health check requests
    if event.get("request", {}).get("url", "").endswith("/api/health"):
        return None

    # Don't send specific error types (if needed)
    if "exc_info" in hint:
        exc_type, exc_value, tb = hint["exc_info"]

        # Example: Ignore specific exceptions
        # if isinstance(exc_value, SomeIgnoredException):
        #     return None

    return event


# ============================================================
# Context Management
# ============================================================

def set_user_context(
    user_id: Optional[str] = None,
    email: Optional[str] = None,
    company_id: Optional[str] = None,
    **extra
):
    """
    Set user context for Sentry events

    Args:
        user_id: User ID
        email: User email
        company_id: Company/tenant ID
        **extra: Additional user context
    """
    if not SENTRY_AVAILABLE:
        return

    context = {}
    if user_id:
        context["id"] = user_id
    if email:
        context["email"] = email
    if company_id:
        context["company_id"] = company_id
    if extra:
        context.update(extra)

    if context:
        sentry_sdk.set_user(context)


def set_context(name: str, data: Dict[str, Any]):
    """
    Set custom context for Sentry events

    Args:
        name: Context name (e.g., "ticket", "agent", "pipeline")
        data: Context data dict
    """
    if not SENTRY_AVAILABLE:
        return

    sentry_sdk.set_context(name, data)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
):
    """
    Add breadcrumb to Sentry event trail

    Args:
        message: Breadcrumb message
        category: Category (e.g., "auth", "query", "pipeline")
        level: Level (debug/info/warning/error)
        data: Additional data
    """
    if not SENTRY_AVAILABLE:
        return

    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


def set_tag(key: str, value: str):
    """
    Set tag for filtering in Sentry

    Args:
        key: Tag key
        value: Tag value
    """
    if not SENTRY_AVAILABLE:
        return

    sentry_sdk.set_tag(key, value)


# ============================================================
# Error Capture
# ============================================================

def capture_exception(
    error: Exception,
    level: str = "error",
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Manually capture exception to Sentry

    Args:
        error: Exception to capture
        level: Error level (fatal/error/warning/info/debug)
        tags: Additional tags
        extra: Additional context
    """
    if not SENTRY_AVAILABLE:
        logger.error(f"Error (Sentry disabled): {error}", exc_info=True)
        return

    with sentry_sdk.push_scope() as scope:
        scope.level = level

        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_exception(error)


def capture_message(
    message: str,
    level: str = "info",
    tags: Optional[Dict[str, str]] = None,
    extra: Optional[Dict[str, Any]] = None
):
    """
    Capture message to Sentry

    Args:
        message: Message to capture
        level: Message level (fatal/error/warning/info/debug)
        tags: Additional tags
        extra: Additional context
    """
    if not SENTRY_AVAILABLE:
        logger.log(getattr(logging, level.upper(), logging.INFO), message)
        return

    with sentry_sdk.push_scope() as scope:
        scope.level = level

        if tags:
            for key, value in tags.items():
                scope.set_tag(key, value)

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        sentry_sdk.capture_message(message)


# ============================================================
# Performance Monitoring
# ============================================================

def start_transaction(
    name: str,
    op: str = "function",
    description: Optional[str] = None
):
    """
    Start performance transaction

    Args:
        name: Transaction name
        op: Operation type (e.g., "function", "http", "db")
        description: Optional description

    Returns:
        Transaction object (use as context manager)

    Example:
        with start_transaction("process_ticket", op="pipeline"):
            # Your code here
            pass
    """
    if not SENTRY_AVAILABLE:
        from contextlib import nullcontext
        return nullcontext()

    return sentry_sdk.start_transaction(
        name=name,
        op=op,
        description=description
    )


def start_span(
    op: str,
    description: Optional[str] = None
):
    """
    Start performance span (child of current transaction)

    Args:
        op: Operation type (e.g., "db.query", "http.request", "ai.inference")
        description: Optional description

    Returns:
        Span object (use as context manager)

    Example:
        with start_transaction("process_ticket"):
            with start_span(op="db.query", description="Get ticket"):
                ticket = get_ticket(ticket_id)
    """
    if not SENTRY_AVAILABLE:
        from contextlib import nullcontext
        return nullcontext()

    return sentry_sdk.start_span(
        op=op,
        description=description
    )


# ============================================================
# Decorators
# ============================================================

def monitor_performance(op: str = "function"):
    """
    Decorator to monitor function performance

    Args:
        op: Operation type

    Example:
        @monitor_performance(op="agent.execute")
        async def execute_agent(ticket_id: str):
            # Your code here
            pass
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not SENTRY_AVAILABLE:
                return await func(*args, **kwargs)

            with start_transaction(name=func.__name__, op=op):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not SENTRY_AVAILABLE:
                return func(*args, **kwargs)

            with start_transaction(name=func.__name__, op=op):
                return func(*args, **kwargs)

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def capture_errors(
    level: str = "error",
    reraise: bool = True
):
    """
    Decorator to automatically capture exceptions

    Args:
        level: Error level to report
        reraise: Whether to re-raise the exception

    Example:
        @capture_errors(level="error", reraise=True)
        async def risky_function():
            # Your code here
            raise ValueError("Something went wrong")
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    e,
                    level=level,
                    tags={"function": func.__name__}
                )
                if reraise:
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                capture_exception(
                    e,
                    level=level,
                    tags={"function": func.__name__}
                )
                if reraise:
                    raise

        # Return appropriate wrapper based on function type
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ============================================================
# Utility Functions
# ============================================================

def flush_events(timeout: float = 2.0):
    """
    Flush pending Sentry events (useful before shutdown)

    Args:
        timeout: Timeout in seconds
    """
    if not SENTRY_AVAILABLE:
        return

    sentry_sdk.flush(timeout=timeout)


def is_enabled() -> bool:
    """Check if Sentry is enabled and initialized"""
    if not SENTRY_AVAILABLE:
        return False

    client = sentry_sdk.Hub.current.client
    return client is not None and client.dsn is not None
