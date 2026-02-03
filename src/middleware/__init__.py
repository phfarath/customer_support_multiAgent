"""
Middleware for authentication, authorization, security headers, and request handling
"""
from .auth import verify_api_key, PUBLIC_PATHS
from .rate_limiter import get_rate_limit_key, get_rate_limit_key_ip_only, RATE_LIMITS, get_rate_limit
from .cors import get_cors_origins, is_origin_allowed
from .security_headers import (
    SecurityHeadersMiddleware,
    ContentSecurityPolicyBuilder,
    CSP_STRICT_API,
    CSP_WITH_SWAGGER,
    get_security_headers_middleware,
)

__all__ = [
    # Authentication
    "verify_api_key",
    "PUBLIC_PATHS",
    # Rate Limiting
    "get_rate_limit_key",
    "get_rate_limit_key_ip_only",
    "RATE_LIMITS",
    "get_rate_limit",
    # CORS
    "get_cors_origins",
    "is_origin_allowed",
    # Security Headers
    "SecurityHeadersMiddleware",
    "ContentSecurityPolicyBuilder",
    "CSP_STRICT_API",
    "CSP_WITH_SWAGGER",
    "get_security_headers_middleware",
]
