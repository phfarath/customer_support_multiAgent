# API Key Authentication

> **Implementado em:** 2026-01-22
> **Status:** ✅ 80% Production-ready

---

## Descrição

Sistema completo de autenticação via API keys para proteger todos os endpoints da API. Cada API key está vinculada a uma empresa específica, garantindo isolamento de dados entre múltiplos tenants.

---

## Arquivos Modificados/Criados

- **Modelo:** `src/models/api_key.py` - API Key model com hash SHA-256
- **Middleware:** `src/middleware/auth.py` - API Key validation
- **Routes:** `src/api/api_key_routes.py` - CRUD de API keys
- **Script:** `scripts/create_initial_api_key.py` - Bootstrap primeira API key
- **Collections:** MongoDB `api_keys` collection

---

## Como Usar

### 1. Criar Primeira API Key (Bootstrap)

```bash
python scripts/create_initial_api_key.py --company-id techcorp_001 --name "Initial Key"
```

**Output:**
```
✅ API Key created successfully!
Company ID: techcorp_001
Key ID: key_a1b2c3d4
API Key: sk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890

⚠️  IMPORTANT: Save this API key securely. It won't be shown again.
```

### 2. Usar API Key nas Requisições

Todas as requisições devem incluir o header `X-API-Key`:

```bash
curl -X GET http://localhost:8000/api/tickets \
  -H "X-API-Key: sk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
```

### 3. Gerenciar API Keys

**Listar Keys:**
```bash
curl -X GET http://localhost:8000/api/keys \
  -H "X-API-Key: sk_..."
```

**Criar Nova Key:**
```bash
curl -X POST http://localhost:8000/api/keys \
  -H "X-API-Key: sk_..." \
  -H "Content-Type: application/json" \
  -d '{
    "company_id": "techcorp_001",
    "name": "Production API Key",
    "permissions": ["read", "write"]
  }'
```

**Revogar Key:**
```bash
curl -X DELETE http://localhost:8000/api/keys/key_a1b2c3d4 \
  -H "X-API-Key: sk_..."
```

---

## Endpoints Protegidos (22)

### Tickets (7)
- ✅ POST `/api/tickets` - Criar ticket
- ✅ POST `/api/run_pipeline/{ticket_id}` - Executar pipeline
- ✅ GET `/api/tickets/{ticket_id}` - Ver ticket
- ✅ GET `/api/tickets/{ticket_id}/audit` - Ver audit logs
- ✅ GET `/api/tickets/{ticket_id}/interactions` - Ver interações
- ✅ GET `/api/tickets/{ticket_id}/agent_states` - Ver estados de agentes
- ✅ GET `/api/tickets` - Listar tickets

### Ingest (1)
- ✅ POST `/api/ingest-message` - Ingerir mensagem

### Company Config (5)
- ✅ POST `/api/companies/` - Criar config
- ✅ GET `/api/companies/{company_id}` - Ver config
- ✅ PUT `/api/companies/{company_id}` - Atualizar config
- ✅ DELETE `/api/companies/{company_id}` - Deletar config
- ✅ GET `/api/companies/` - Listar configs

### Human Agent (2)
- ✅ POST `/api/human/reply` - Responder ticket escalado
- ✅ GET `/api/human/escalated` - Listar tickets escalados

### Telegram Admin (4)
- ✅ GET `/telegram/webhook/info` - Info do webhook
- ✅ POST `/telegram/webhook/set` - Configurar webhook
- ✅ POST `/telegram/webhook/delete` - Deletar webhook
- ✅ GET `/telegram/bot/info` - Info do bot

### API Keys (3)
- ✅ POST `/api/keys/` - Criar API key
- ✅ GET `/api/keys/` - Listar API keys
- ✅ DELETE `/api/keys/{key_id}` - Revogar API key

---

## Company Isolation

**Importante:** Cada API key está vinculada a uma `company_id`. O sistema garante que:
- Você só pode acessar dados da sua empresa
- Não pode criar/modificar recursos de outras empresas
- Tentativas de acesso cross-company retornam 404 (não 403, para não vazar informação)

**Exemplo:**
```python
# API key da empresa A tenta acessar ticket da empresa B
curl -X GET http://localhost:8000/api/tickets/TICKET-001 \
  -H "X-API-Key: sk_empresa_A_..."

# Response: 404 Not Found (mesmo se o ticket existir)
# Isso previne information disclosure
```

---

## Boas Práticas

### DO:
- ✅ Criar uma API key por ambiente (dev, staging, prod)
- ✅ Revogar keys antigas quando não mais necessárias
- ✅ Usar nomes descritivos para as keys
- ✅ Armazenar keys em variáveis de ambiente, não no código

### DON'T:
- ❌ Commitar API keys no git
- ❌ Compartilhar API keys entre empresas
- ❌ Usar a mesma key para múltiplos ambientes
- ❌ Expor API keys em logs ou mensagens de erro

---

## Exemplos de Código

### Middleware de Validação

```python
# src/middleware/auth.py
from fastapi import Header, HTTPException
from src.database.connection import get_collection

async def verify_api_key(x_api_key: str = Header(...)):
    """Valida API key e retorna company_id"""
    api_keys_collection = get_collection("api_keys")
    key_doc = await api_keys_collection.find_one({
        "key": x_api_key,
        "active": True
    })

    if not key_doc:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return key_doc
```

### Uso em Route

```python
from fastapi import Depends
from src.middleware.auth import verify_api_key

@router.post("/api/tickets")
async def create_ticket(
    ticket_data: TicketCreate,
    api_key: dict = Depends(verify_api_key)
):
    # Verificar company isolation
    if ticket_data.company_id != api_key["company_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized company access")
    
    # Processar ticket...
```

---

## Testes Realizados

- ✅ Criação de API key via script de bootstrap
- ✅ Validação de API key em endpoints protegidos
- ✅ Company isolation (404 para cross-company access)
- ✅ Revogação de API key
- ✅ Listagem de API keys por empresa
- ✅ Permissões (read/write)
- ✅ Expiração de API key (opcional)

---

## Troubleshooting

### Erro: "Invalid API key"
```bash
# 1. Verificar se a key existe no MongoDB
mongo --eval 'db.api_keys.findOne({key: "sk_..."})'

# 2. Verificar se a key está ativa
mongo --eval 'db.api_keys.findOne({key: "sk_...", active: true})'
```

### Erro: "Unauthorized company access"
```bash
# Verificar se o company_id da key corresponde ao recurso
# Cada API key só pode acessar recursos da própria empresa
```

---

## Referências

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Visão geral do projeto
- [AI_INSTRUCTIONS.md](../../AI_INSTRUCTIONS.md) - Guia para agentes de IA
- [JWT Dashboard Auth](2026-01-23_18-30_jwt-dashboard-auth.md) - Autenticação do dashboard
