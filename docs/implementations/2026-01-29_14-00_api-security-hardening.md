# API Security Hardening

> **Implementado em:** 2026-01-29 14:00
> **Status:** ✅ Production-ready
> **Plano Original:** [docs/deprecated_futures/036_v1.0_api_security_hardening.md](../deprecated_futures/036_v1.0_api_security_hardening.md)

---

## Descricao

Implementacao de hardening de seguranca nas APIs do sistema, incluindo validacao de configuracoes em producao, verificacao de assinatura do webhook do Telegram, rate limiting avancado baseado em fingerprint, e configuracao segura de CORS.

**Vulnerabilidades Corrigidas:**
- CRITICA: JWT secret com valor padrao fraco aceito em producao
- ALTA: Webhook do Telegram aceitava requisicoes sem verificacao de assinatura
- ALTA: Rate limiting baseado apenas em IP (facil contornar com proxies)
- ALTA: CORS permitia localhost em producao

---

## Arquivos Modificados/Criados

### Criados
| Arquivo | Descricao |
|---------|-----------|
| `src/middleware/rate_limiter.py` | Rate limiting baseado em fingerprint (IP + User-Agent + API Key) |
| `src/middleware/cors.py` | Filtro de CORS que remove localhost em producao |

### Modificados
| Arquivo | Mudancas |
|---------|----------|
| `src/config.py` | Adicionado `environment`, `telegram_webhook_secret`, e `model_validator` |
| `src/middleware/__init__.py` | Exporta novos modulos |
| `src/api/telegram_routes.py` | Verificacao de assinatura do webhook |
| `main.py` | Usa novo rate limiter e CORS filter |
| `.env.example` | Novas variaveis `ENVIRONMENT` e `TELEGRAM_WEBHOOK_SECRET` |

---

## Como Usar

### Configuracao de Ambiente

```bash
# .env - Desenvolvimento (padrao)
ENVIRONMENT=development

# .env - Producao (validacoes enforced)
ENVIRONMENT=production
JWT_SECRET_KEY=sua-chave-secreta-com-pelo-menos-32-caracteres-aqui
TELEGRAM_WEBHOOK_SECRET=seu-secret-token-aqui
CORS_ALLOWED_ORIGINS=https://dashboard.seudominio.com,https://api.seudominio.com
```

### Configurar Webhook do Telegram com Secret

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://seu-dominio.com/telegram/webhook",
    "secret_token": "seu-secret-token-aqui"
  }'
```

### Variaveis de Ambiente

| Variavel | Obrigatorio | Descricao |
|----------|-------------|-----------|
| `ENVIRONMENT` | Nao | `development`, `staging`, ou `production` (default: development) |
| `TELEGRAM_WEBHOOK_SECRET` | Em producao | Token secreto para verificacao do webhook |
| `JWT_SECRET_KEY` | Em producao | Chave secreta para JWT (minimo 32 caracteres) |
| `CORS_ALLOWED_ORIGINS` | Em producao | Lista de origens permitidas (sem localhost) |

---

## Detalhes da Implementacao

### 1. Validacao de Producao (`src/config.py`)

O `model_validator` valida configuracoes criticas quando `ENVIRONMENT=production`:

```python
@model_validator(mode='after')
def validate_production_settings(self) -> 'Settings':
    if self.environment == "production":
        # Valida JWT secret
        if self.jwt_secret_key == "CHANGE_THIS_IN_PRODUCTION":
            raise ValueError("JWT_SECRET_KEY must be changed...")
        if len(self.jwt_secret_key) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters...")

        # Valida Telegram webhook secret
        if not self.telegram_webhook_secret:
            raise ValueError("TELEGRAM_WEBHOOK_SECRET is required...")

        # Valida CORS (sem localhost)
        if any("localhost" in o for o in self.cors_allowed_origins):
            raise ValueError("CORS contains localhost origins...")
```

### 2. Rate Limiting por Fingerprint (`src/middleware/rate_limiter.py`)

Gera chave unica combinando:
- IP address
- User-Agent (primeiros 50 chars)
- API Key (primeiros 10 chars)

```python
def get_rate_limit_key(request: Request) -> str:
    ip = get_remote_address(request)
    user_agent = request.headers.get("User-Agent", "")[:50]
    api_key = request.headers.get("X-API-Key", "")[:10]
    fingerprint = f"{ip}:{user_agent}:{api_key}"
    return hashlib.md5(fingerprint.encode()).hexdigest()
```

### 3. Verificacao de Assinatura do Telegram (`src/api/telegram_routes.py`)

Verifica o header `X-Telegram-Bot-Api-Secret-Token`:

```python
async def verify_telegram_signature(request: Request) -> bool:
    if settings.environment != "production" and not settings.telegram_webhook_secret:
        return True  # Skip em dev se nao configurado

    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret_token:
        return False

    return hmac.compare_digest(secret_token, settings.telegram_webhook_secret)
```

### 4. CORS Hardening (`src/middleware/cors.py`)

Filtra automaticamente localhost em producao:

```python
def get_cors_origins() -> List[str]:
    origins = settings.cors_allowed_origins.copy()
    if settings.environment == "production":
        return [o for o in origins if "localhost" not in o and "127.0.0.1" not in o]
    return origins
```

---

## Limites de Rate Limiting

| Operacao | Limite | Descricao |
|----------|--------|-----------|
| default | 60/min | Padrao para endpoints |
| ingest | 15/min | Ingestion de mensagens |
| pipeline | 5/min | Execucao de pipeline (OpenAI) |
| read | 120/min | Operacoes de leitura |
| write | 30/min | Operacoes de escrita |
| admin | 5/min | Operacoes administrativas |
| webhook | 30/min | Webhooks publicos |
| critical | 3/min | Operacoes criticas |

---

## Testes Realizados

1. **JWT Validation**: Aplicacao falha ao iniciar com secret fraco em producao
2. **Telegram Webhook**: Requisicoes sem assinatura retornam 403 em producao
3. **Rate Limiting**: Fingerprints diferentes tem limites separados
4. **CORS**: Localhost bloqueado automaticamente em producao

---

## Troubleshooting

### Aplicacao nao inicia em producao

```bash
# Erro: JWT_SECRET_KEY must be changed from default value
# Solucao: Gerar secret seguro
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### Webhook do Telegram retorna 403

```bash
# 1. Verificar se TELEGRAM_WEBHOOK_SECRET esta configurado
echo $TELEGRAM_WEBHOOK_SECRET

# 2. Verificar se webhook foi configurado com secret_token
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# 3. Reconfigurar webhook com secret
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d '{"url": "https://...", "secret_token": "..."}'
```

### CORS bloqueando requisicoes legitimas

```bash
# Adicionar dominio ao .env
CORS_ALLOWED_ORIGINS=https://dominio1.com,https://dominio2.com

# Reiniciar aplicacao
```

---

## Referencias

- [Telegram Webhook Secret Token](https://core.telegram.org/bots/api#setwebhook)
- [OWASP API Security](https://owasp.org/www-project-api-security/)
- [SlowAPI Rate Limiting](https://slowapi.readthedocs.io/)
- [FastAPI CORS](https://fastapi.tiangolo.com/tutorial/cors/)
- [Plano Original](../deprecated_futures/036_v1.0_api_security_hardening.md)
