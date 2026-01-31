# Security Documentation

> **Última atualização:** 2026-01-31
> **Versão:** 1.0

---

## Visão Geral

Este documento descreve as práticas e implementações de segurança do Customer Support MultiAgent.

---

## 1. Autenticação e Autorização

### API Key Authentication
- Todas as APIs REST requerem header `X-API-Key`
- API Keys são hasheadas com SHA-256 antes de armazenamento
- Suporte a permissões granulares por endpoint
- Isolamento por `company_id`

### JWT Dashboard Authentication
- Dashboard Streamlit usa JWT tokens
- Tokens expiram em 24 horas
- Senhas hasheadas com bcrypt
- Refresh token rotation

---

## 2. Input Sanitization

### XSS Prevention
- Todos os inputs são sanitizados com `html.escape()`
- Truncamento de texto para prevenir DoS
- Remoção de null bytes

### SQL/NoSQL Injection
- Uso de queries parametrizadas
- Validação de tipos via Pydantic
- Whitelist de campos permitidos

---

## 3. PII Detection & Redaction (LGPD/GDPR)

### Tipos de PII Detectados

| Tipo | Formato | Exemplo |
|------|---------|---------|
| CPF | 000.000.000-00 | 529.982.247-25 |
| RG | XX.XXX.XXX-X | 12.345.678-9 |
| Cartão de Crédito | 16 dígitos | 4111 1111 1111 1111 |
| Email | user@domain.com | joao@empresa.com |
| Telefone | (XX) XXXXX-XXXX | (11) 99999-8888 |
| CEP | 00000-000 | 01310-100 |
| CNH | 11 dígitos | 12345678901 |
| Passaporte | AA000000 | AB123456 |

### Como Funciona

1. **Detecção**: Regex patterns identificam PII no texto
2. **Validação**: CPF e cartão de crédito são validados (checksums)
3. **Redação**: PII é substituído por placeholders (ex: `[CPF REDACTED]`)
4. **Auditoria**: Tipos de PII detectados são logados

### Uso

```python
from src.utils.sanitization import sanitize_text_with_pii_detection

text = "Meu CPF é 529.982.247-25"
redacted, pii_detected, pii_types = sanitize_text_with_pii_detection(text)

# redacted = "Meu CPF é [CPF REDACTED]"
# pii_detected = True
# pii_types = ["cpf"]
```

### Armazenamento

- Interações armazenam flag `pii_detected: bool`
- Lista de tipos detectados em `pii_types: list`
- Texto original **nunca** é armazenado - apenas versão redatada

---

## 4. Rate Limiting

### Configuração

| Endpoint | Limite | Janela |
|----------|--------|--------|
| /api/ingest-message | 20 req | 1 min |
| /api/tickets | 60 req | 1 min |
| /api/companies | 30 req | 1 min |
| Default | 100 req | 1 min |

### Implementação
- Middleware `slowapi` com Redis backend (opcional)
- Headers de resposta incluem limites restantes
- Status 429 quando limite excedido

---

## 5. CORS Hardening

### Configuração
- Origins permitidos via whitelist em `.env`
- Credenciais permitidas apenas para origins confiáveis
- Headers expostos limitados

```env
CORS_ALLOWED_ORIGINS=https://dashboard.empresa.com,https://admin.empresa.com
```

---

## 6. AI Security

### Prompt Injection Protection
- Sanitização de inputs antes de envio para LLM
- System prompts isolados do user input
- Validação de outputs

### Content Moderation
- Detecção de conteúdo ofensivo
- Filtros para jailbreak attempts
- Rate limiting por usuário

---

## 7. Infrastructure Security

### Secrets Management
- Variáveis sensíveis em `.env` (nunca commitado)
- Suporte a AWS Secrets Manager em produção
- Rotação periódica de credenciais

### Secure Logging
- PII nunca é logado
- Logs de erro não expõem stack traces em produção
- Audit trail completo

### Security Headers
- HSTS, X-Frame-Options, X-Content-Type-Options
- CSP configurado
- Referrer-Policy

---

## 8. Checklist de Segurança

### Antes do Deploy

- [ ] Rotacionar todas as credenciais expostas
- [ ] Configurar CORS whitelist
- [ ] Habilitar rate limiting
- [ ] Verificar logs não contêm PII
- [ ] Testar PII detection em todos os canais

### Monitoramento Contínuo

- [ ] Alertas para tentativas de autenticação falhas
- [ ] Monitoramento de rate limit violations
- [ ] Auditoria de acessos a dados sensíveis
- [ ] Review periódico de logs de segurança

---

## 9. Referências

- [LGPD_COMPLIANCE.md](./LGPD_COMPLIANCE.md) - Compliance com LGPD
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Arquitetura geral
- [AI_INSTRUCTIONS.md](../AI_INSTRUCTIONS.md) - Instruções para AI
- [OWASP Top 10](https://owasp.org/Top10/)

---

## 10. Contato

Para reportar vulnerabilidades de segurança, contate: security@empresa.com
