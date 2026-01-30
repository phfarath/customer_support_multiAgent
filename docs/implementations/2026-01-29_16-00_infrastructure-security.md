# Infrastructure Security

> **Implementado em:** 2026-01-29 16:00
> **Status:** ✅ Production-ready
> **Plano Original:** [docs/deprecated_futures/038_v1.0_infrastructure_security.md](../deprecated_futures/038_v1.0_infrastructure_security.md)

---

## Descrição

Implementacao da camada de seguranca de infraestrutura para protecao de secrets, tratamento seguro de erros, headers de seguranca HTTP, e logging sem exposicao de dados sensiveis.

**Vulnerabilidades Corrigidas:**
- CRITICA: Secrets em texto plano expostos em logs
- CRITICA: Error disclosure - mensagens de erro expondo detalhes internos
- MEDIA: Headers de seguranca ausentes (CSP, XSS, HSTS)
- MEDIA: Logging expondo dados sensiveis (API keys, passwords)

---

## Arquivos Criados

### Modulo de Seguranca

| Arquivo | Descricao | Linhas |
|---------|-----------|--------|
| `src/security/secrets_manager.py` | Gerenciador de secrets com suporte a env vars e AWS | ~280 |
| `src/security/error_handler.py` | Handler seguro de erros com trace ID | ~320 |
| `src/middleware/security_headers.py` | Middleware de headers HTTP de seguranca | ~230 |
| `src/utils/secure_logging.py` | Logging com mascaramento automatico | ~350 |

### Testes

| Arquivo | Descricao | Testes |
|---------|-----------|--------|
| `tests/test_infrastructure_security.py` | Suite completa de testes | 25+ |

---

## Arquivos Modificados

| Arquivo | Modificacao |
|---------|-------------|
| `src/security/__init__.py` | Export novos modulos (secrets, error_handler) |
| `src/middleware/__init__.py` | Export SecurityHeadersMiddleware |
| `src/utils/__init__.py` | Export secure_logging |
| `main.py` | Adiciona middleware e exception handler |
| `src/api/routes.py` | Usa SecureError ao inves de str(e) |
| `src/api/ingest_routes.py` | Usa SecureError ao inves de str(e) |

---

## Como Usar

### 1. Secrets Manager

```python
from src.security import get_secrets_manager, mask_secret

# Obter secrets
secrets = get_secrets_manager()
api_key = secrets.get_secret("OPENAI_API_KEY")

# Secret obrigatorio (lanca excecao se nao encontrado)
db_uri = secrets.get_secret_required("MONGODB_URI")

# Mascarar para logging
logger.info(f"Using key: {mask_secret(api_key)}")
# Output: "Using key: sk_l...i789"
```

### 2. Secure Error Handling

```python
from src.security import SecureError, raise_not_found

# Levantar erro seguro
raise SecureError(
    "E001",
    message="Operation failed",  # Mensagem para usuario
    internal_message="pymongo.errors.ServerSelectionTimeoutError",  # Apenas logs
    context={"ticket_id": "123"}  # Contexto para logs
)

# Helpers convenientes
raise_not_found("Ticket")
raise_validation_error("email", "Invalid format")
raise_internal_error("Database connection failed")
```

### 3. Security Headers

Os headers sao adicionados automaticamente pelo middleware. Incluem:

- `Content-Security-Policy`: Restringe recursos que podem ser carregados
- `X-Frame-Options: DENY`: Previne clickjacking
- `X-XSS-Protection: 1; mode=block`: Protecao XSS (browsers antigos)
- `X-Content-Type-Options: nosniff`: Previne MIME sniffing
- `Strict-Transport-Security`: HSTS (apenas em producao)
- `Referrer-Policy`: Controla envio de referrer
- `Permissions-Policy`: Restringe APIs do browser

### 4. Secure Logging

```python
from src.utils import configure_secure_logging

# Configurar no startup (ja feito em main.py)
configure_secure_logging(
    level=logging.INFO,
    format_type='text',  # ou 'json' para producao
    include_trace_id=True
)

# Agora todos os logs mascaram dados sensiveis automaticamente
logger.info(f"Connecting to {mongodb_uri}")
# Output: "Connecting to mongodb://[USER]:[PASS]@localhost"
```

---

## Codigos de Erro

| Codigo | Descricao | HTTP Status |
|--------|-----------|-------------|
| E001 | Internal server error | 500 |
| E002 | Database connection error | 503 |
| E003 | External service unavailable | 503 |
| E004 | Invalid request format | 400 |
| E005 | Authentication failed | 401 |
| E006 | Authorization denied | 403 |
| E007 | Resource not found | 404 |
| E008 | Rate limit exceeded | 429 |
| E009 | Validation error | 422 |
| E010 | Service temporarily unavailable | 503 |
| E011 | Request timeout | 504 |
| E012 | Configuration error | 500 |

---

## Padroes de Dados Sensiveis Mascarados

O sistema mascara automaticamente:

| Tipo | Exemplo | Mascarado |
|------|---------|-----------|
| API Keys | `sk_live_abc123...` | `[API_KEY_REDACTED]` |
| JWT Tokens | `eyJhbG...` | `[JWT_REDACTED]` |
| MongoDB URI | `mongodb://user:pass@host` | `mongodb://[USER]:[PASS]@host` |
| Passwords | `password=secret123` | `password=[REDACTED]` |
| CPF | `123.456.789-00` | `***.456.***-**` |
| Credit Cards | `4111-1111-1111-1111` | `****-****-****-1111` |
| Phone Numbers | `+55 11 99999-9999` | `+55 (**) *****-9999` |

---

## Testes

```bash
# Executar todos os testes de seguranca
pytest tests/test_infrastructure_security.py -v

# Executar teste especifico
pytest tests/test_infrastructure_security.py::TestSecretsManager -v

# Com coverage
pytest tests/test_infrastructure_security.py --cov=src/security --cov-report=term-missing
```

---

## Troubleshooting

### Erro: "Required secret not found"

```bash
# 1. Verificar se a variavel esta definida
echo $OPENAI_API_KEY

# 2. Adicionar ao .env
echo "OPENAI_API_KEY=sk_..." >> .env

# 3. Em producao, verificar AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id customer-support/secrets
```

### Headers de seguranca nao aparecem

```python
# Verificar se middleware foi adicionado corretamente em main.py
app.add_middleware(
    SecurityHeadersMiddleware,
    environment=settings.environment,
)
```

### Logs ainda mostram dados sensiveis

```python
# Verificar se secure logging foi configurado
from src.utils import configure_secure_logging
configure_secure_logging(level=logging.INFO)

# Verificar se logger tem o filtro
from src.utils.secure_logging import SensitiveDataFilter
logger.addFilter(SensitiveDataFilter())
```

---

## Boas Praticas

**DO:**
- Use `SecureError` para todos os erros que vao para o cliente
- Use `mask_secret()` antes de logar qualquer valor sensivel
- Configure `environment=production` em producao para ativar HSTS
- Use `get_secret_required()` para secrets obrigatorios

**DON'T:**
- Nunca use `str(e)` em respostas HTTP
- Nunca logue secrets sem mascarar
- Nunca desabilite headers de seguranca em producao
- Nunca exponha trace IDs internos ao publico

---

## Referencias

- [OWASP Secure Coding Practices](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
- [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/)
- [Security Headers](https://securityheaders.com/)
- [CSP Reference](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

**Ultima atualizacao:** 2026-01-29
**Versao:** 1.0
