# CORS Hardening (Cross-Origin Security)

> **Implementado em:** 2026-01-23
> **Status:** ✅ 100% Production-ready

---

## Descrição

CORS (Cross-Origin Resource Sharing) hardening para prevenir acessos não autorizados de domínios maliciosos. Apenas domínios na whitelist podem fazer requisições cross-origin.

---

## Arquivos Modificados/Criados

- **Middleware:** `main.py` - CORSMiddleware config
- **Configurações:** `src/config.py` - CORS whitelist
- **Environment:** `.env.example` - CORS_ALLOWED_ORIGINS

---

## O Que Mudou

### Antes (INSEGURO)
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # ❌ QUALQUER domínio pode acessar!
    allow_credentials=True,
    allow_methods=["*"],      # ❌ Todos os métodos
    allow_headers=["*"],      # ❌ Todos os headers
)
```

### Depois (SEGURO)
```python
# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,  # ✅ Whitelist específica
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ Métodos específicos
    allow_headers=[                                # ✅ Headers específicos
        "Content-Type",
        "X-API-Key",
        "Authorization",
        "Accept",
        "Origin",
    ],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],
    max_age=600,  # Cache preflight por 10 min
)
```

---

## Configuração

### src/config.py
```python
from typing import List

# CORS Configuration (Cross-Origin Resource Sharing)
cors_allowed_origins: List[str] = [
    "http://localhost:3000",      # React dev server
    "http://localhost:8501",      # Streamlit dashboard
    "http://127.0.0.1:3000",      # Alternative localhost
    "http://127.0.0.1:8501",      # Alternative localhost
    # Production domains should be added via environment variable
]
```

### .env.example
```bash
# CORS Configuration (Cross-Origin Resource Sharing)
# Comma-separated list of allowed origins
# Development: http://localhost:3000,http://localhost:8501
# Production: https://dashboard.yourdomain.com,https://api.yourdomain.com
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8501,http://127.0.0.1:3000,http://127.0.0.1:8501
```

---

## Como Usar em Produção

### 1. Adicionar domínios de produção ao .env
```bash
CORS_ALLOWED_ORIGINS=https://dashboard.mycompany.com,https://api.mycompany.com,https://app.mycompany.com
```

### 2. Pydantic carrega automaticamente
```python
# src/config.py lê da env var
cors_allowed_origins: List[str] = [...]  # Sobrescrito pelo .env
```

---

## Proteções Implementadas

### 1. Origin Whitelist
- Apenas domínios na lista podem fazer requests cross-origin
- Requests de outros domínios são bloqueados pelo browser

### 2. Métodos Restritos
- Apenas GET, POST, PUT, DELETE, OPTIONS permitidos
- PATCH, TRACE, CONNECT bloqueados

### 3. Headers Restritos
- Apenas headers essenciais permitidos
- Headers customizados maliciosos bloqueados

### 4. Preflight Cache
- Preflight requests (OPTIONS) são cached por 10 min
- Reduz overhead de CORS checks

### 5. Credentials Permitidos
- `allow_credentials=True` permite cookies e auth headers
- Necessário para API keys e JWT tokens

---

## Exemplo de Request Bloqueado

```javascript
// Frontend em https://malicious-site.com tenta acessar API
fetch('https://api.mycompany.com/api/tickets', {
  headers: {
    'X-API-Key': 'sk_stolen_key_123'
  }
})

// Browser bloqueia com erro CORS:
// Access to fetch at 'https://api.mycompany.com/api/tickets'
// from origin 'https://malicious-site.com' has been blocked by CORS policy:
// The 'Access-Control-Allow-Origin' header has a value
// 'https://dashboard.mycompany.com' that is not equal to the supplied origin.
```

---

## Exemplo de Request Permitido

```javascript
// Frontend em https://dashboard.mycompany.com (whitelist)
fetch('https://api.mycompany.com/api/tickets', {
  headers: {
    'X-API-Key': 'sk_...'
  }
})

// Browser permite (domínio na whitelist)
// Response headers:
// Access-Control-Allow-Origin: https://dashboard.mycompany.com
// Access-Control-Allow-Credentials: true
```

---

## Boas Práticas

### DO:
- ✅ Usar HTTPS em produção (never HTTP)
- ✅ Listar apenas domínios que você controla
- ✅ Usar subdomínios específicos (não wildcards)
- ✅ Testar CORS antes de deploy

### DON'T:
- ❌ Usar `allow_origins=["*"]` em produção
- ❌ Adicionar domínios de terceiros à whitelist
- ❌ Usar wildcards (`*.mycompany.com`)
- ❌ Confiar apenas em CORS para segurança (use API keys também)

---

## Exemplos de Código

### Configuração CORS Completa
```python
# main.py
from fastapi.middleware.cors import CORSMiddleware
from src.config import settings

app.add_middleware(
    CORSMiddleware,
    # Whitelist de origens (configurável via .env)
    allow_origins=settings.cors_allowed_origins,
    
    # Permite cookies e auth headers
    allow_credentials=True,
    
    # Métodos permitidos (restrito)
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "DELETE",
        "OPTIONS"
    ],
    
    # Headers permitidos (restrito)
    allow_headers=[
        "Content-Type",
        "X-API-Key",
        "Authorization",
        "Accept",
        "Origin",
    ],
    
    # Headers expostos (para rate limiting)
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining"
    ],
    
    # Cache preflight por 10 min
    max_age=600,
)
```

### Carregar Origins do .env
```python
# src/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # ... outras configurações ...
    
    # CORS Configuration
    cors_allowed_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8501",
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

---

## Troubleshooting

### Erro: "CORS policy blocked"
```bash
# 1. Verificar domínio na whitelist
echo $CORS_ALLOWED_ORIGINS

# 2. Adicionar domínio ao .env
CORS_ALLOWED_ORIGINS=https://dashboard.mycompany.com,https://newdomain.com

# 3. Reiniciar API
python main.py
```

### Erro: "Credentials not allowed"
```python
# Verificar allow_credentials=True no main.py
# Deve estar habilitado para API keys funcionarem
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,  # ← Necessário
    ...
)
```

### Request do localhost não funciona
```bash
# Adicionar ambos localhost e 127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

---

## Security Layering

CORS é **primeira linha de defesa**, mas não suficiente sozinho:

```
┌──────────────────────────────────────────────────┐
│ 1. CORS (Browser-level)            │ ← Bloqueia origem maliciosa
├──────────────────────────────────────────────────┤
│ 2. API Key Auth (App-level)        │ ← Valida autenticação
├──────────────────────────────────────────────────┤
│ 3. Rate Limiting (Infrastructure)  │ ← Previne abuso
├──────────────────────────────────────────────────┤
│ 4. Input Sanitization (Data-level) │ ← Limpa payloads
└──────────────────────────────────────────────────┘
```

Todas as 4 camadas são necessárias para security completo!

---

## Testes Realizados

- ✅ Whitelist de origins
- ✅ Métodos restritos
- ✅ Headers restritos
- ✅ Preflight cache (10min)
- ✅ Credentials permitidos
- ✅ Bloqueio de origins não autorizadas
- ✅ Permissão de origins autorizadas
- ✅ Configuração via .env

---

## Referências

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Visão geral do projeto
- [AI_INSTRUCTIONS.md](../../AI_INSTRUCTIONS.md) - Guia para agentes de IA
- [API Key Authentication](2026-01-23_18-30_api-key-authentication.md) - Autenticação da API
- [Rate Limiting](2026-01-23_18-30_rate-limiting.md) - Prevenção de DoS
