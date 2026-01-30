"""
Security Headers Middleware - HTTP security headers for protection

This module provides middleware that adds security headers to all responses:
- Content-Security-Policy (CSP)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Strict-Transport-Security (HSTS)
- Referrer-Policy
- Permissions-Policy
- Cache-Control for API responses

Usage:
    from src.middleware.security_headers import SecurityHeadersMiddleware

    app.add_middleware(SecurityHeadersMiddleware)
"""

import os
from typing import Callable, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds security headers to all HTTP responses.

    Headers are configured based on environment (development vs production).
    HSTS is only enabled in production with HTTPS.
    """

    def __init__(
        self,
        app,
        environment: Optional[str] = None,
        csp_directives: Optional[dict] = None,
        hsts_max_age: int = 31536000,  # 1 year
        excluded_paths: Optional[List[str]] = None,
    ):
        """
        Initialize SecurityHeadersMiddleware.

        Args:
            app: ASGI application
            environment: Environment (development, staging, production)
            csp_directives: Optional custom CSP directives
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            excluded_paths: Paths to exclude from security headers
        """
        super().__init__(app)
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.is_production = self.environment == 'production'
        self.hsts_max_age = hsts_max_age
        self.excluded_paths = excluded_paths or []

        # Build CSP directive string
        self.csp = self._build_csp(csp_directives)

    def _build_csp(self, custom_directives: Optional[dict] = None) -> str:
        """
        Build Content-Security-Policy header value.

        Args:
            custom_directives: Optional custom CSP directives to merge

        Returns:
            CSP header value string
        """
        # Default CSP directives (strict but functional for API)
        default_directives = {
            "default-src": "'self'",
            "script-src": "'self'",
            "style-src": "'self' 'unsafe-inline'",  # For Swagger UI
            "img-src": "'self' data: https:",
            "font-src": "'self' data:",
            "connect-src": "'self'",
            "frame-ancestors": "'none'",
            "form-action": "'self'",
            "base-uri": "'self'",
            "object-src": "'none'",
        }

        # Merge with custom directives
        if custom_directives:
            default_directives.update(custom_directives)

        # Build CSP string
        return "; ".join(f"{key} {value}" for key, value in default_directives.items())

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and add security headers to response.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response with security headers
        """
        response = await call_next(request)

        # Skip excluded paths (e.g., health checks)
        if any(request.url.path.startswith(path) for path in self.excluded_paths):
            return response

        # Add security headers
        self._add_security_headers(request, response)

        return response

    def _add_security_headers(self, request: Request, response: Response) -> None:
        """
        Add all security headers to the response.

        Args:
            request: Incoming request
            response: Response to modify
        """
        # Content-Security-Policy
        # Restricts resources the browser can load
        response.headers["Content-Security-Policy"] = self.csp

        # X-Content-Type-Options
        # Prevents MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options
        # Prevents clickjacking by disabling iframe embedding
        response.headers["X-Frame-Options"] = "DENY"

        # X-XSS-Protection
        # Legacy XSS protection (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer-Policy
        # Controls how much referrer info is sent
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy (formerly Feature-Policy)
        # Restricts browser features
        response.headers["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # X-Permitted-Cross-Domain-Policies
        # Restricts Adobe Flash/Acrobat cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        # Cross-Origin-Embedder-Policy
        # Prevents loading cross-origin resources
        response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"

        # Cross-Origin-Opener-Policy
        # Isolates browsing context
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"

        # Cross-Origin-Resource-Policy
        # Prevents cross-origin loading
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"

        # Strict-Transport-Security (HSTS)
        # Forces HTTPS - only in production with HTTPS
        if self.is_production:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # Cache-Control for API responses
        # Prevent caching of sensitive data
        if self._is_api_response(request):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"

    def _is_api_response(self, request: Request) -> bool:
        """Check if this is an API endpoint response."""
        api_prefixes = ["/api/", "/telegram/"]
        return any(request.url.path.startswith(prefix) for prefix in api_prefixes)


class ContentSecurityPolicyBuilder:
    """
    Helper class to build CSP directives.

    Usage:
        csp = ContentSecurityPolicyBuilder()
        csp.add_script_src("'self'", "https://cdn.example.com")
        csp.add_style_src("'self'", "'unsafe-inline'")
        csp_string = csp.build()
    """

    def __init__(self):
        self.directives: dict = {}

    def add_directive(self, name: str, *values: str) -> "ContentSecurityPolicyBuilder":
        """Add a CSP directive."""
        if name not in self.directives:
            self.directives[name] = []
        self.directives[name].extend(values)
        return self

    def add_default_src(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("default-src", *values)

    def add_script_src(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("script-src", *values)

    def add_style_src(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("style-src", *values)

    def add_img_src(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("img-src", *values)

    def add_connect_src(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("connect-src", *values)

    def add_font_src(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("font-src", *values)

    def add_frame_ancestors(self, *values: str) -> "ContentSecurityPolicyBuilder":
        return self.add_directive("frame-ancestors", *values)

    def build(self) -> str:
        """Build the CSP header value."""
        return "; ".join(
            f"{name} {' '.join(values)}"
            for name, values in self.directives.items()
        )


# Pre-configured CSP for common scenarios
CSP_STRICT_API = {
    "default-src": "'none'",
    "frame-ancestors": "'none'",
    "form-action": "'none'",
}

CSP_WITH_SWAGGER = {
    "default-src": "'self'",
    "script-src": "'self' 'unsafe-inline'",  # Swagger needs inline scripts
    "style-src": "'self' 'unsafe-inline'",   # Swagger needs inline styles
    "img-src": "'self' data: https:",
    "font-src": "'self' data:",
    "connect-src": "'self'",
    "frame-ancestors": "'none'",
    "form-action": "'self'",
}


def get_security_headers_middleware(
    environment: Optional[str] = None,
    include_swagger: bool = True,
) -> SecurityHeadersMiddleware:
    """
    Factory function to create SecurityHeadersMiddleware.

    Args:
        environment: Optional environment override
        include_swagger: Whether to allow Swagger UI resources

    Returns:
        Configured SecurityHeadersMiddleware
    """
    csp_directives = CSP_WITH_SWAGGER if include_swagger else CSP_STRICT_API

    return SecurityHeadersMiddleware(
        app=None,  # Will be set when added to app
        environment=environment,
        csp_directives=csp_directives,
        excluded_paths=["/health", "/metrics"],
    )


__all__ = [
    'SecurityHeadersMiddleware',
    'ContentSecurityPolicyBuilder',
    'CSP_STRICT_API',
    'CSP_WITH_SWAGGER',
    'get_security_headers_middleware',
]
