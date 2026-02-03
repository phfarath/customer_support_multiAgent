"""
Unit tests for PII detection and redaction
"""
import pytest
from src.utils.pii_detector import (
    detect_pii,
    redact_pii,
    has_pii,
    get_pii_summary,
    validate_cpf,
    validate_credit_card,
    PII_CPF,
    PII_EMAIL,
    PII_PHONE,
    PII_CREDIT_CARD,
    PII_CEP,
    REDACTION_PLACEHOLDERS,
)


class TestValidateCPF:
    """Tests for CPF validation"""

    def test_valid_cpf_formatted(self):
        """Valid CPF with dots and dash"""
        assert validate_cpf("529.982.247-25") is True

    def test_valid_cpf_unformatted(self):
        """Valid CPF without formatting"""
        assert validate_cpf("52998224725") is True

    def test_invalid_cpf_wrong_checksum(self):
        """Invalid CPF with wrong check digits"""
        assert validate_cpf("529.982.247-00") is False

    def test_invalid_cpf_repeated_digits(self):
        """Invalid CPF with all same digits"""
        assert validate_cpf("111.111.111-11") is False
        assert validate_cpf("000.000.000-00") is False

    def test_invalid_cpf_wrong_length(self):
        """Invalid CPF with wrong length"""
        assert validate_cpf("123.456.789") is False
        assert validate_cpf("12345678901234") is False


class TestValidateCreditCard:
    """Tests for credit card validation (Luhn algorithm)"""

    def test_valid_visa(self):
        """Valid Visa card"""
        assert validate_credit_card("4111111111111111") is True

    def test_valid_mastercard(self):
        """Valid Mastercard"""
        assert validate_credit_card("5500000000000004") is True

    def test_valid_amex(self):
        """Valid American Express"""
        assert validate_credit_card("340000000000009") is True

    def test_invalid_card(self):
        """Invalid card number"""
        assert validate_credit_card("4111111111111112") is False

    def test_invalid_card_short(self):
        """Too short card number"""
        assert validate_credit_card("411111111111") is False


class TestDetectPII:
    """Tests for PII detection"""

    def test_detect_cpf_formatted(self):
        """Detect CPF with formatting"""
        text = "Meu CPF é 529.982.247-25"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_CPF
        assert matches[0].original == "529.982.247-25"

    def test_detect_cpf_unformatted(self):
        """Detect CPF without formatting"""
        text = "CPF: 52998224725"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_CPF

    def test_detect_email(self):
        """Detect email address"""
        text = "Contato: joao.silva@empresa.com.br"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_EMAIL
        assert matches[0].original == "joao.silva@empresa.com.br"

    def test_detect_phone_brazilian(self):
        """Detect Brazilian phone number"""
        text = "Telefone: (11) 99999-8888"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_PHONE

    def test_detect_phone_international(self):
        """Detect international phone number"""
        text = "Ligue para +55 11 99999-8888"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_PHONE

    def test_detect_credit_card(self):
        """Detect credit card number"""
        text = "Cartão: 4111 1111 1111 1111"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_CREDIT_CARD

    def test_detect_cep(self):
        """Detect Brazilian postal code (CEP)"""
        text = "CEP: 01310-100"
        matches = detect_pii(text)
        assert len(matches) == 1
        assert matches[0].pii_type == PII_CEP

    def test_detect_multiple_pii(self):
        """Detect multiple PII in same text"""
        text = "CPF: 529.982.247-25, email: teste@email.com, tel: (11) 99999-8888"
        matches = detect_pii(text)
        assert len(matches) == 3
        pii_types = [m.pii_type for m in matches]
        assert PII_CPF in pii_types
        assert PII_EMAIL in pii_types
        assert PII_PHONE in pii_types

    def test_no_pii(self):
        """No PII in text"""
        text = "Olá, gostaria de saber sobre o produto X"
        matches = detect_pii(text)
        assert len(matches) == 0

    def test_invalid_cpf_not_detected(self):
        """Invalid CPF should not be detected when validation enabled"""
        text = "CPF: 111.111.111-11"  # Invalid - all same digits
        matches = detect_pii(text, validate=True)
        assert len(matches) == 0

    def test_invalid_cpf_detected_without_validation(self):
        """Invalid CPF should be detected when validation disabled"""
        text = "CPF: 111.111.111-11"
        matches = detect_pii(text, validate=False)
        assert len(matches) == 1


class TestRedactPII:
    """Tests for PII redaction"""

    def test_redact_cpf(self):
        """Redact CPF from text"""
        text = "Meu CPF é 529.982.247-25"
        redacted, detected, types = redact_pii(text)
        assert detected is True
        assert PII_CPF in types
        assert "529.982.247-25" not in redacted
        assert REDACTION_PLACEHOLDERS[PII_CPF] in redacted

    def test_redact_email(self):
        """Redact email from text"""
        text = "Email: usuario@dominio.com"
        redacted, detected, types = redact_pii(text)
        assert detected is True
        assert PII_EMAIL in types
        assert "usuario@dominio.com" not in redacted
        assert REDACTION_PLACEHOLDERS[PII_EMAIL] in redacted

    def test_redact_multiple_pii(self):
        """Redact multiple PII from text"""
        text = "CPF 529.982.247-25 e email teste@email.com"
        redacted, detected, types = redact_pii(text)
        assert detected is True
        assert len(types) == 2
        assert "529.982.247-25" not in redacted
        assert "teste@email.com" not in redacted
        assert REDACTION_PLACEHOLDERS[PII_CPF] in redacted
        assert REDACTION_PLACEHOLDERS[PII_EMAIL] in redacted

    def test_redact_preserves_context(self):
        """Redaction preserves surrounding text"""
        text = "Olá, meu CPF é 529.982.247-25, obrigado!"
        redacted, _, _ = redact_pii(text)
        assert redacted.startswith("Olá, meu CPF é")
        assert redacted.endswith(", obrigado!")

    def test_no_pii_unchanged(self):
        """Text without PII remains unchanged"""
        text = "Mensagem normal sem dados sensíveis"
        redacted, detected, types = redact_pii(text)
        assert detected is False
        assert types == []
        assert redacted == text

    def test_empty_text(self):
        """Empty text handling"""
        redacted, detected, types = redact_pii("")
        assert detected is False
        assert types == []
        assert redacted == ""

    def test_none_text(self):
        """None text handling"""
        redacted, detected, types = redact_pii(None)
        assert detected is False
        assert types == []
        assert redacted is None


class TestHasPII:
    """Tests for has_pii function"""

    def test_has_pii_true(self):
        """Returns True when PII present"""
        assert has_pii("CPF: 529.982.247-25") is True

    def test_has_pii_false(self):
        """Returns False when no PII"""
        assert has_pii("Hello world") is False


class TestGetPIISummary:
    """Tests for PII summary function"""

    def test_summary_single_type(self):
        """Summary with single PII type"""
        text = "CPF: 529.982.247-25"
        summary = get_pii_summary(text)
        assert summary == {PII_CPF: 1}

    def test_summary_multiple_same_type(self):
        """Summary with multiple instances of same type"""
        text = "Emails: a@b.com e c@d.com"
        summary = get_pii_summary(text)
        assert summary == {PII_EMAIL: 2}

    def test_summary_multiple_types(self):
        """Summary with multiple PII types"""
        text = "CPF 529.982.247-25, email teste@x.com"
        summary = get_pii_summary(text)
        assert PII_CPF in summary
        assert PII_EMAIL in summary

    def test_summary_empty(self):
        """Summary for text without PII"""
        summary = get_pii_summary("No PII here")
        assert summary == {}


class TestIntegration:
    """Integration tests for PII detection in realistic scenarios"""

    def test_customer_support_message(self):
        """Typical customer support message with PII"""
        text = """
        Olá, preciso de ajuda com minha conta.
        Meu CPF é 529.982.247-25 e meu email é cliente@email.com.
        Podem me ligar no (11) 99999-1234?
        """
        redacted, detected, types = redact_pii(text)
        
        assert detected is True
        assert len(types) == 3
        assert "529.982.247-25" not in redacted
        assert "cliente@email.com" not in redacted
        assert "(11) 99999-1234" not in redacted

    def test_credit_card_payment_message(self):
        """Payment message with credit card"""
        text = "Quero pagar com cartão 4111 1111 1111 1111"
        redacted, detected, types = redact_pii(text)
        
        assert detected is True
        assert PII_CREDIT_CARD in types
        assert "4111 1111 1111 1111" not in redacted

    def test_address_with_cep(self):
        """Address with CEP"""
        text = "Entrega na Av. Paulista, 1000 - CEP 01310-100"
        redacted, detected, types = redact_pii(text)
        
        assert detected is True
        assert PII_CEP in types
        assert "01310-100" not in redacted
        assert "Av. Paulista, 1000" in redacted  # Address text preserved
