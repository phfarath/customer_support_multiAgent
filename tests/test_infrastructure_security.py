"""
Tests for Infrastructure Security - Secrets Manager, Error Handler, Security Headers, Secure Logging

This module tests:
- SecretsManager: Secrets retrieval and masking
- SecureError: Safe error handling without internal detail exposure
- SecurityHeadersMiddleware: HTTP security headers
- SensitiveDataFilter: Log masking for sensitive data
"""

import pytest
import logging
import os
from unittest.mock import patch, MagicMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.responses import Response

# Import security modules
from src.security.secrets_manager import (
    SecretsManager,
    get_secrets_manager,
    reset_secrets_manager,
    mask_secret,
    mask_sensitive_data,
)
from src.security.error_handler import (
    SecureError,
    ERROR_CODES,
    generate_trace_id,
    create_error_response,
    secure_exception_handler,
)
from src.middleware.security_headers import (
    SecurityHeadersMiddleware,
    ContentSecurityPolicyBuilder,
)
from src.utils.secure_logging import (
    SensitiveDataFilter,
    SecureFormatter,
    configure_secure_logging,
    SENSITIVE_PATTERNS,
)


class TestSecretsManager:
    """Tests for SecretsManager module"""

    def setup_method(self):
        """Reset secrets manager before each test"""
        reset_secrets_manager()

    def test_get_secret_from_env(self):
        """Test that secrets can be fetched from environment variables"""
        # Set test env var
        os.environ["TEST_SECRET_KEY"] = "test_secret_value_123"

        secrets = get_secrets_manager(environment="development")
        value = secrets.get_secret("TEST_SECRET_KEY")

        assert value == "test_secret_value_123"

        # Cleanup
        del os.environ["TEST_SECRET_KEY"]

    def test_get_secret_default_value(self):
        """Test that default value is returned when secret not found"""
        secrets = get_secrets_manager(environment="development")
        value = secrets.get_secret("NON_EXISTENT_KEY", default="default_value")

        assert value == "default_value"

    def test_get_secret_required_raises(self):
        """Test that get_secret_required raises when secret not found"""
        secrets = get_secrets_manager(environment="development")

        with pytest.raises(ValueError) as excinfo:
            secrets.get_secret_required("NON_EXISTENT_REQUIRED_KEY")

        assert "Required secret" in str(excinfo.value)

    def test_mask_secret_basic(self):
        """Test that secrets are properly masked"""
        secret = "sk_live_abc123def456ghi789jkl"
        masked = mask_secret(secret)

        assert masked == "sk_l...l"
        assert "abc123" not in masked
        assert len(masked) < len(secret)

    def test_mask_secret_short_value(self):
        """Test that short secrets are completely masked"""
        short_secret = "abc"
        masked = mask_secret(short_secret)

        assert masked == "***"

    def test_mask_sensitive_data_api_key(self):
        """Test masking of API keys in text"""
        text = "Using API key: sk_live_abc123def456ghi789jklmnop"
        masked = mask_sensitive_data(text)

        assert "sk_live_abc123" not in masked
        assert "[API_KEY_MASKED]" in masked

    def test_mask_sensitive_data_mongodb_uri(self):
        """Test masking of MongoDB URIs with credentials"""
        text = "Connecting to mongodb://admin:supersecretpassword@localhost:27017"
        masked = mask_sensitive_data(text)

        assert "supersecretpassword" not in masked
        assert "[MASKED]" in masked

    def test_mask_sensitive_data_jwt(self):
        """Test masking of JWT tokens"""
        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        text = f"Token: {jwt}"
        masked = mask_sensitive_data(text)

        assert jwt not in masked
        assert "[JWT_MASKED]" in masked


class TestSecureError:
    """Tests for SecureError handler module"""

    def test_secure_error_no_stack_trace(self):
        """Test that SecureError responses don't include stack traces"""
        error = SecureError(
            "E001",
            internal_message="Database connection failed: pymongo.errors.ServerSelectionTimeoutError"
        )
        response = error.to_response()

        # Should not contain internal details
        assert "pymongo" not in str(response)
        assert "ServerSelectionTimeoutError" not in str(response)
        assert "Database connection failed" not in str(response)

        # Should contain safe message
        assert response["error"]["code"] == "E001"
        assert "internal server error" in response["error"]["message"].lower()

    def test_secure_error_includes_trace_id(self):
        """Test that SecureError includes a trace ID for correlation"""
        error = SecureError("E001")
        response = error.to_response()

        assert "trace_id" in response["error"]
        assert len(response["error"]["trace_id"]) == 36  # UUID format

    def test_generate_trace_id_unique(self):
        """Test that trace IDs are unique"""
        id1 = generate_trace_id()
        id2 = generate_trace_id()

        assert id1 != id2

    def test_error_codes_exist(self):
        """Test that all error codes have messages"""
        for code in ["E001", "E002", "E003", "E004", "E005", "E006", "E007", "E008", "E009"]:
            assert code in ERROR_CODES
            assert len(ERROR_CODES[code]) > 0

    def test_create_error_response_safe(self):
        """Test that create_error_response doesn't expose internal errors"""
        internal_error = Exception("pymongo.errors.AutoReconnect: connection pool exhausted")

        response = create_error_response(
            code="E002",
            internal_error=internal_error,
            context={"database": "customer_support"}
        )

        # Parse response content
        import json
        content = json.loads(response.body)

        assert "pymongo" not in str(content)
        assert "AutoReconnect" not in str(content)
        assert "connection pool" not in str(content)
        assert content["error"]["code"] == "E002"

    @pytest.mark.asyncio
    async def test_secure_exception_handler_generic_exception(self):
        """Test that unhandled exceptions are properly masked"""
        from starlette.testclient import TestClient
        from fastapi import FastAPI

        app = FastAPI()
        app.add_exception_handler(Exception, secure_exception_handler)

        @app.get("/test")
        async def test_endpoint():
            raise Exception("Internal database error with sensitive info: password=secret123")

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 500
        data = response.json()

        assert "password" not in str(data)
        assert "secret123" not in str(data)
        assert "trace_id" in data["error"]


class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware"""

    def setup_method(self):
        """Create test app with security headers middleware"""
        self.app = FastAPI()
        self.app.add_middleware(SecurityHeadersMiddleware, environment="development")

        @self.app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        self.client = TestClient(self.app)

    def test_security_headers_csp(self):
        """Test that Content-Security-Policy header is present"""
        response = self.client.get("/test")

        assert "Content-Security-Policy" in response.headers
        csp = response.headers["Content-Security-Policy"]
        assert "default-src" in csp
        assert "frame-ancestors" in csp

    def test_security_headers_xss(self):
        """Test that X-XSS-Protection header is present"""
        response = self.client.get("/test")

        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"

    def test_security_headers_frame_options(self):
        """Test that X-Frame-Options header is present"""
        response = self.client.get("/test")

        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_security_headers_content_type_options(self):
        """Test that X-Content-Type-Options header is present"""
        response = self.client.get("/test")

        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_security_headers_referrer_policy(self):
        """Test that Referrer-Policy header is present"""
        response = self.client.get("/test")

        assert "Referrer-Policy" in response.headers

    def test_security_headers_permissions_policy(self):
        """Test that Permissions-Policy header is present"""
        response = self.client.get("/test")

        assert "Permissions-Policy" in response.headers
        assert "camera=()" in response.headers["Permissions-Policy"]

    def test_no_hsts_in_development(self):
        """Test that HSTS is not added in development"""
        response = self.client.get("/test")

        # HSTS should only be in production
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_in_production(self):
        """Test that HSTS is added in production"""
        prod_app = FastAPI()
        prod_app.add_middleware(SecurityHeadersMiddleware, environment="production")

        @prod_app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}

        client = TestClient(prod_app)
        response = client.get("/test")

        assert "Strict-Transport-Security" in response.headers
        assert "max-age=" in response.headers["Strict-Transport-Security"]


class TestSecureLogging:
    """Tests for SecureLogging module"""

    def test_sensitive_data_filter_masks_api_keys(self):
        """Test that SensitiveDataFilter masks API keys in logs"""
        filter = SensitiveDataFilter()

        # Create a log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Using API key: sk_live_abc123def456ghi789jklmnop",
            args=(),
            exc_info=None
        )

        filter.filter(record)

        assert "sk_live_abc123" not in record.msg
        assert "REDACTED" in record.msg or "API_KEY" in record.msg

    def test_sensitive_data_filter_masks_mongodb_uri(self):
        """Test that SensitiveDataFilter masks MongoDB URIs"""
        filter = SensitiveDataFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Connecting to mongodb://admin:supersecret@localhost:27017/db",
            args=(),
            exc_info=None
        )

        filter.filter(record)

        assert "supersecret" not in record.msg
        assert "PASS" in record.msg or "USER" in record.msg

    def test_sensitive_data_filter_masks_passwords(self):
        """Test that SensitiveDataFilter masks passwords"""
        filter = SensitiveDataFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='Login with password="secretpassword123"',
            args=(),
            exc_info=None
        )

        filter.filter(record)

        assert "secretpassword123" not in record.msg

    def test_sensitive_data_filter_masks_jwt(self):
        """Test that SensitiveDataFilter masks JWT tokens"""
        filter = SensitiveDataFilter()

        jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=f"Token: {jwt}",
            args=(),
            exc_info=None
        )

        filter.filter(record)

        assert jwt not in record.msg
        assert "JWT" in record.msg or "REDACTED" in record.msg

    def test_sensitive_data_filter_masks_cpf(self):
        """Test that SensitiveDataFilter masks Brazilian CPF"""
        filter = SensitiveDataFilter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Customer CPF: 123.456.789-00",
            args=(),
            exc_info=None
        )

        filter.filter(record)

        assert "123.456.789-00" not in record.msg

    def test_sensitive_patterns_exist(self):
        """Test that sensitive patterns are defined"""
        assert len(SENSITIVE_PATTERNS) > 0

        # Check that patterns cover common sensitive data
        pattern_names = str(SENSITIVE_PATTERNS)
        # The patterns themselves should exist
        assert len(SENSITIVE_PATTERNS) >= 10  # At least 10 patterns


class TestContentSecurityPolicyBuilder:
    """Tests for CSP Builder"""

    def test_csp_builder_basic(self):
        """Test basic CSP building"""
        csp = ContentSecurityPolicyBuilder()
        csp.add_default_src("'self'")
        csp.add_script_src("'self'", "'unsafe-inline'")

        result = csp.build()

        assert "default-src 'self'" in result
        assert "script-src 'self' 'unsafe-inline'" in result

    def test_csp_builder_frame_ancestors(self):
        """Test CSP frame-ancestors directive"""
        csp = ContentSecurityPolicyBuilder()
        csp.add_frame_ancestors("'none'")

        result = csp.build()

        assert "frame-ancestors 'none'" in result


# Integration test
class TestSecurityIntegration:
    """Integration tests for security modules"""

    def test_full_security_stack(self):
        """Test all security layers working together"""
        from fastapi import FastAPI
        from starlette.testclient import TestClient

        app = FastAPI()

        # Add security middleware
        app.add_middleware(SecurityHeadersMiddleware, environment="development")
        app.add_exception_handler(Exception, secure_exception_handler)

        @app.get("/secure-endpoint")
        async def secure_endpoint():
            return {"status": "secure"}

        @app.get("/error-endpoint")
        async def error_endpoint():
            raise Exception("Internal error with secret: sk_live_test123")

        client = TestClient(app)

        # Test secure endpoint has all headers
        response = client.get("/secure-endpoint")
        assert response.status_code == 200
        assert "Content-Security-Policy" in response.headers
        assert "X-Frame-Options" in response.headers

        # Test error endpoint doesn't leak secrets
        response = client.get("/error-endpoint")
        assert response.status_code == 500
        data = response.json()
        assert "sk_live_test123" not in str(data)
        assert "trace_id" in data["error"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
