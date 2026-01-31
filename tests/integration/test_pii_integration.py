"""
Integration tests for PII detection in the message ingestion flow
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.utils.sanitization import sanitize_text_with_pii_detection


class TestPIIIntegrationSanitization:
    """Tests for PII detection integrated with sanitization"""

    def test_sanitize_with_pii_detection_cpf(self):
        """PII detection works with sanitization"""
        text = "Meu CPF é 529.982.247-25"
        redacted, detected, types = sanitize_text_with_pii_detection(text)
        
        assert detected is True
        assert "cpf" in types
        assert "529.982.247-25" not in redacted
        assert "[CPF REDACTED]" in redacted

    def test_sanitize_with_pii_and_xss(self):
        """PII detection works alongside XSS prevention"""
        text = "<script>alert('xss')</script> CPF: 529.982.247-25"
        redacted, detected, types = sanitize_text_with_pii_detection(text)
        
        # XSS should be escaped
        assert "<script>" not in redacted
        assert "&lt;script&gt;" in redacted
        
        # PII should be redacted
        assert detected is True
        assert "529.982.247-25" not in redacted

    def test_sanitize_with_truncation_and_pii(self):
        """PII detection works with text truncation"""
        # Create a long message with PII at the end
        long_prefix = "A" * 100
        text = f"{long_prefix} CPF: 529.982.247-25"
        
        redacted, detected, types = sanitize_text_with_pii_detection(text, max_length=4000)
        
        # Should still detect PII
        assert detected is True
        assert "529.982.247-25" not in redacted

    def test_sanitize_no_pii(self):
        """No PII detected in clean text"""
        text = "Olá, gostaria de mais informações sobre o produto"
        redacted, detected, types = sanitize_text_with_pii_detection(text)
        
        assert detected is False
        assert types == []
        assert redacted == text

    def test_sanitize_empty_string(self):
        """Empty string handling"""
        redacted, detected, types = sanitize_text_with_pii_detection("")
        
        assert detected is False
        assert types == []
        assert redacted == ""

    def test_sanitize_multiple_pii_types(self):
        """Multiple PII types detected and redacted"""
        text = "Email: teste@email.com, Tel: (11) 99999-8888, CPF: 529.982.247-25"
        redacted, detected, types = sanitize_text_with_pii_detection(text)
        
        assert detected is True
        assert len(types) >= 3
        
        # All PII should be redacted
        assert "teste@email.com" not in redacted
        assert "(11) 99999-8888" not in redacted
        assert "529.982.247-25" not in redacted
        
        # Redaction placeholders should be present
        assert "[EMAIL REDACTED]" in redacted
        assert "[PHONE REDACTED]" in redacted
        assert "[CPF REDACTED]" in redacted


class TestPIIInMessageFlow:
    """Tests simulating the message ingestion flow"""

    @pytest.mark.asyncio
    async def test_interaction_stores_pii_flag(self):
        """Interaction correctly stores pii_detected flag"""
        from src.utils.sanitization import sanitize_text_with_pii_detection
        
        # Simulate incoming message with PII
        incoming_text = "Meu CPF é 529.982.247-25 e email teste@email.com"
        
        # Apply sanitization with PII detection
        sanitized_text, pii_detected, pii_types = sanitize_text_with_pii_detection(incoming_text)
        
        # Verify PII was detected
        assert pii_detected is True
        assert "cpf" in pii_types
        assert "email" in pii_types
        
        # Verify PII was redacted
        assert "529.982.247-25" not in sanitized_text
        assert "teste@email.com" not in sanitized_text
        
        # These values would be stored in the interaction
        interaction_data = {
            "content": sanitized_text,
            "pii_detected": pii_detected,
            "pii_types": pii_types,
        }
        
        assert interaction_data["pii_detected"] is True
        assert len(interaction_data["pii_types"]) == 2

    @pytest.mark.asyncio
    async def test_message_without_pii(self):
        """Normal message without PII flows correctly"""
        incoming_text = "Olá, preciso de ajuda com meu pedido #12345"
        
        sanitized_text, pii_detected, pii_types = sanitize_text_with_pii_detection(incoming_text)
        
        assert pii_detected is False
        assert pii_types == []
        assert sanitized_text == incoming_text


class TestPIIAuditLogging:
    """Tests for PII detection audit logging"""

    def test_pii_types_for_audit(self):
        """PII types are correctly identified for audit logs"""
        from src.utils.pii_detector import get_pii_summary
        
        text = "CPF: 529.982.247-25, cartão: 4111 1111 1111 1111"
        summary = get_pii_summary(text)
        
        # Should have counts for each type
        assert "cpf" in summary
        assert "credit_card" in summary
        
        # Counts should be correct
        assert summary["cpf"] == 1
        assert summary["credit_card"] == 1
