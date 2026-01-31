# PII Detection & Redaction

> **Implementado em:** 2026-01-31 14:30
> **Status:** ✅ Production-ready

---

## Descrição

Implementação de detecção e redação de PII (Personally Identifiable Information) para compliance com LGPD/GDPR. O sistema detecta automaticamente dados sensíveis em mensagens de clientes e os substitui por placeholders antes do armazenamento.

---

## Arquivos Modificados/Criados

### Criados
- `src/utils/pii_detector.py` - Módulo principal de detecção e redação de PII
- `tests/unit/test_pii_detector.py` - Testes unitários para PII detector
- `tests/integration/test_pii_integration.py` - Testes de integração
- `docs/SECURITY.md` - Documentação de segurança
- `docs/LGPD_COMPLIANCE.md` - Documentação de compliance LGPD

### Modificados
- `src/utils/sanitization.py` - Integração do PII detector com sanitização
- `src/models/interaction.py` - Adicionados campos `pii_detected` e `pii_types`
- `src/database/ticket_operations.py` - Suporte para armazenar flags de PII
- `src/api/ingest_routes.py` - Uso de PII detection no fluxo de ingestão

---

## Tipos de PII Detectados

| Tipo | Formato | Placeholder |
|------|---------|-------------|
| CPF | 000.000.000-00 | `[CPF REDACTED]` |
| RG | XX.XXX.XXX-X | `[RG REDACTED]` |
| Cartão de Crédito | 16 dígitos (Luhn) | `[CREDIT CARD REDACTED]` |
| Email | user@domain.com | `[EMAIL REDACTED]` |
| Telefone | (XX) XXXXX-XXXX | `[PHONE REDACTED]` |
| CEP | 00000-000 | `[CEP REDACTED]` |
| CNH | 11 dígitos | `[CNH REDACTED]` |
| Passaporte | AA000000 | `[PASSPORT REDACTED]` |

---

## Como Usar

### Detecção e Redação Básica

```python
from src.utils.pii_detector import redact_pii, detect_pii, has_pii

# Verificar se texto contém PII
if has_pii("Meu CPF é 529.982.247-25"):
    print("Contém PII!")

# Detectar PII sem redatar
matches = detect_pii("CPF: 529.982.247-25, email: teste@email.com")
for match in matches:
    print(f"Tipo: {match.pii_type}, Original: {match.original}")

# Redatar PII
text = "Meu CPF é 529.982.247-25"
redacted, pii_detected, pii_types = redact_pii(text)
# redacted = "Meu CPF é [CPF REDACTED]"
# pii_detected = True
# pii_types = ["cpf"]
```

### Integração com Sanitização

```python
from src.utils.sanitization import sanitize_text_with_pii_detection

# Sanitiza E detecta/redacta PII em uma única chamada
text = "<script>alert('xss')</script> CPF: 529.982.247-25"
redacted, pii_detected, pii_types = sanitize_text_with_pii_detection(text)
# XSS escapado + CPF redatado
```

### Validação de CPF/Cartão

```python
from src.utils.pii_detector import validate_cpf, validate_credit_card

# CPF válido
assert validate_cpf("529.982.247-25") == True
assert validate_cpf("111.111.111-11") == False  # Dígitos repetidos

# Cartão válido (Luhn)
assert validate_credit_card("4111111111111111") == True
```

---

## Fluxo de Processamento

```
Mensagem do Cliente
        │
        ▼
┌───────────────────┐
│ sanitize_text_    │
│ with_pii_detection│
└────────┬──────────┘
         │
         ├─── Sanitização XSS
         │
         ├─── Detecção PII (regex)
         │
         ├─── Validação (CPF/cartão)
         │
         └─── Redação
                │
                ▼
┌───────────────────┐
│ add_interaction() │
│ pii_detected=True │
│ pii_types=[...]   │
└───────────────────┘
```

---

## Modelo de Dados

### Interaction (MongoDB)

```json
{
  "ticket_id": "telegram_123_1706712600",
  "type": "customer_message",
  "content": "Meu CPF é [CPF REDACTED] e email [EMAIL REDACTED]",
  "pii_detected": true,
  "pii_types": ["cpf", "email"],
  "created_at": "2026-01-31T14:30:00Z"
}
```

---

## Testes Realizados

### Testes Unitários (`tests/unit/test_pii_detector.py`)
- ✅ Validação de CPF (válido/inválido)
- ✅ Validação de cartão de crédito (Luhn)
- ✅ Detecção de todos os tipos de PII
- ✅ Redação com preservação de contexto
- ✅ Múltiplos PIIs no mesmo texto
- ✅ Textos sem PII

### Testes de Integração (`tests/integration/test_pii_integration.py`)
- ✅ Integração com sanitização XSS
- ✅ Fluxo completo de ingestão
- ✅ Armazenamento de flags PII

---

## Troubleshooting

### PII não está sendo detectado

1. Verifique se o formato está correto (ex: CPF com 11 dígitos)
2. Para CPF/cartão, verificar se o checksum é válido
3. CNH só é detectado com contexto ("CNH", "carteira", "habilitação")

### Falsos positivos

1. Números que parecem CPF mas não são podem ser detectados
2. Use `validate=True` para validar checksums
3. CEP pode conflitar com outros números de 8 dígitos

### Performance

- Detecção é O(n) onde n = tamanho do texto
- Para textos muito longos, considere truncar antes da detecção

---

## Referências

- [Plano Original](../deprecated_futures/020_v1.1_pii_detection.md)
- [SECURITY.md](../SECURITY.md) - Documentação de segurança
- [LGPD_COMPLIANCE.md](../LGPD_COMPLIANCE.md) - Compliance LGPD/GDPR
- [Microsoft Presidio](https://github.com/microsoft/presidio) - Referência de implementação
