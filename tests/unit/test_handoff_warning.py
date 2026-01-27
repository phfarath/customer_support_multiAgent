"""
Unit tests for Handoff Warning Message generation
"""
import pytest
import sys
from typing import Optional

# Avoid import chain issues by importing directly
sys.path.insert(0, '/Users/phfarath/Library/Mobile Documents/com~apple~CloudDocs/Pessoal-PF/Codes/customer_support_multiAgent')

from src.models.company_config import CompanyConfig


def _generate_warning_message(
    reasons: list[str], 
    company_config: CompanyConfig | None = None
) -> str:
    """
    Generate warning message before escalation explaining why.
    (Duplicated here for isolated testing)
    """
    # Build default message
    default_message = (
        "⚠️ Para melhor atendê-lo, sua solicitação será transferida "
        "para um de nossos especialistas."
    )
    
    if reasons:
        if len(reasons) == 1:
            reason_summary = reasons[0]
        else:
            reason_summary = f"{reasons[0]} e {reasons[1]}"
        default_message += f" Motivo: {reason_summary}."
    
    default_message += " Aguarde um momento, por favor."
    
    # Check for custom template
    if company_config and company_config.handoff_warning_message:
        try:
            return company_config.handoff_warning_message.format(
                reason=reasons[0] if reasons else "necessidade de especialista",
                reasons=", ".join(reasons) if reasons else "necessidade de especialista"
            )
        except Exception:
            return company_config.handoff_warning_message
    
    return default_message


class TestGenerateWarningMessage:
    """Tests for _generate_warning_message helper function"""
    
    def test_warning_with_default_template_single_reason(self):
        """Test warning with default template and single reason"""
        reasons = ["cliente frustrado"]
        message = _generate_warning_message(reasons, None)
        
        assert "⚠️" in message
        assert "cliente frustrado" in message
        assert "Motivo:" in message
        assert "Aguarde" in message
        assert "transferida" in message
    
    def test_warning_with_default_template_multiple_reasons(self):
        """Test warning with default template and multiple reasons"""
        reasons = ["cliente frustrado", "problema técnico complexo", "outro motivo"]
        message = _generate_warning_message(reasons, None)
        
        assert "⚠️" in message
        assert "cliente frustrado" in message
        assert "problema técnico complexo" in message
        # Should only show first two reasons
        assert "outro motivo" not in message
        assert "Aguarde" in message
    
    def test_warning_with_no_reasons(self):
        """Test warning with no specific reasons"""
        message = _generate_warning_message([], None)
        
        assert "⚠️" in message
        assert "transferida" in message
        assert "Aguarde" in message
        # Should not contain "Motivo:" when no reasons
        assert "Motivo:" not in message
    
    def test_warning_with_custom_template_reason_placeholder(self):
        """Test warning with custom template using {reason} placeholder"""
        config = CompanyConfig(
            company_id="test",
            company_name="Test Co",
            handoff_warning_message="Olá! Motivo da transferência: {reason}. Aguarde."
        )
        
        reasons = ["solicitação especial"]
        message = _generate_warning_message(reasons, config)
        
        assert "Olá!" in message
        assert "solicitação especial" in message
        assert "Aguarde" in message
    
    def test_warning_with_custom_template_reasons_placeholder(self):
        """Test warning with custom template using {reasons} placeholder"""
        config = CompanyConfig(
            company_id="test",
            company_name="Test Co",
            handoff_warning_message="Transferindo por: {reasons}"
        )
        
        reasons = ["motivo1", "motivo2"]
        message = _generate_warning_message(reasons, config)
        
        assert "motivo1" in message
        assert "motivo2" in message
    
    def test_warning_with_custom_template_no_placeholder(self):
        """Test warning with custom template without placeholders"""
        config = CompanyConfig(
            company_id="test",
            company_name="Test Co",
            handoff_warning_message="Você está sendo transferido. Aguarde por favor."
        )
        
        reasons = ["qualquer motivo"]
        message = _generate_warning_message(reasons, config)
        
        assert message == "Você está sendo transferido. Aguarde por favor."
    
    def test_warning_with_custom_template_empty_reasons(self):
        """Test warning with custom template when no reasons provided"""
        config = CompanyConfig(
            company_id="test",
            company_name="Test Co",
            handoff_warning_message="Motivo: {reason}"
        )
        
        message = _generate_warning_message([], config)
        
        # Should use default fallback text
        assert "necessidade de especialista" in message
    
    def test_warning_with_none_config(self):
        """Test warning with None company config"""
        reasons = ["teste"]
        message = _generate_warning_message(reasons, None)
        
        # Should use default template
        assert "⚠️" in message
        assert "teste" in message
    
    def test_warning_with_config_but_no_warning_message(self):
        """Test warning with company config that has no handoff_warning_message"""
        config = CompanyConfig(
            company_id="test",
            company_name="Test Co",
            # handoff_warning_message not set
        )
        
        reasons = ["teste"]
        message = _generate_warning_message(reasons, config)
        
        # Should use default template
        assert "⚠️" in message
        assert "teste" in message


class TestWarningMessageIntegration:
    """Integration-style tests for warning message behavior"""
    
    def test_warning_message_structure(self):
        """Test that warning message has proper structure"""
        reasons = ["problema complexo"]
        message = _generate_warning_message(reasons, None)
        
        # Should start with warning emoji
        assert message.startswith("⚠️")
        
        # Should contain key phrases
        assert "especialistas" in message.lower()
        assert "aguarde" in message.lower()
    
    def test_warning_message_length_reasonable(self):
        """Test that warning message is not too long"""
        reasons = ["razão 1", "razão 2", "razão 3", "razão 4", "razão 5"]
        message = _generate_warning_message(reasons, None)
        
        # Message should be concise (under 300 chars)
        assert len(message) < 300
