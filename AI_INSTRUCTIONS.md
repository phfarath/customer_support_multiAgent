# AI Instructions - Customer Support MultiAgent

> **Guia Prático para Agentes de IA**
> Este documento contém regras, padrões e instruções específicas para modificar código, adicionar features e manter o projeto.

---

## 📖 Leia Primeiro

Antes de fazer qualquer modificação:

1. **Leia:** `ARCHITECTURE.md` (visão geral completa)
2. **Entenda:** O contexto atual e branch ativa
3. **Verifique:** Se já existe implementação similar
4. **Planeje:** Quebre tarefas grandes em passos menores

---

## 🎯 Contexto Atual do Projeto

### Status Atual
- **Branch:** `feat/escalating_to_human` ✅ CONCLUÍDA
- **Última Feature:** JWT Dashboard Authentication implementada ✅
- **Sprint Atual:** **SEMANA 1 - FIX BUGS CRÍTICOS + SECURITY**
- **Estado:** 95% completo - 3 bugs P0 corrigidos ✅ - API auth implementada ✅ - Dashboard JWT implementado ✅

### 🚨 BUGS CRÍTICOS ATIVOS

#### NUNCA faça essas coisas (causam bugs ativos):

1. **NUNCA confie no business hours check**
   - `src/bots/telegram_bot.py:491` sempre retorna True
   - Feature não funciona
   - Fix pendente: implementar parsing correto

#### ✅ BUGS CORRIGIDOS (Jan 22, 2026)

1. **✅ company_config agora está disponível no context**
   - FIXED: `src/utils/pipeline.py` agora injeta company_config
   - Context sempre inclui `company_config` (dict vazio se não encontrado)
   - Todos os agentes têm acesso a produtos, policies e teams

2. **✅ Modelo OpenAI válido configurado**
   - FIXED: `src/config.py` usa `gpt-4o-mini` (modelo válido)
   - Todas as chamadas OpenAI funcionam corretamente

3. **✅ Dependencies completas**
   - FIXED: `requirements.txt` agora inclui todas as dependências
   - chromadb, langchain-*, streamlit, python-telegram-bot instalados

### O Que Está Funcionando
✅ Pipeline completo (4 agentes) com fallbacks
✅ Telegram bot (webhook + polling) 70%
✅ RAG com ChromaDB 100%
✅ Multi-tenancy (company_config + company isolation)
✅ Escalação automática com emails
✅ Dashboard Streamlit 60%
✅ E2E tests (estrutura existe)
✅ **API Key Authentication (20 endpoints protegidos)**

### Sprint Atual: Semana 1 (Dias 1-5)

#### Dias 1-2: CRITICAL BUGS
- [x] Fix Bug #1: company_config no pipeline ✅ DONE
- [x] Fix Bug #3: requirements.txt completo ✅ DONE
- [x] Fix Bug #4: modelo OpenAI correto ✅ DONE
- [ ] Fix Bug #2: business hours check
- [ ] ensure_indexes() no startup
- [ ] Timeouts em HTTP clients

#### Dias 3-5: SECURITY
- [ ] Rotacionar credenciais expostas (manual - instruções fornecidas)
- [x] API key authentication ✅ DONE
- [x] JWT para dashboard ✅ DONE
- [ ] Input sanitization
- [ ] Rate limiting API
- [ ] Fix CORS policy

### Próximas Sprints
- **Semana 2-3:** Deployment (AWS ECS) + Testing
- **Mês 2:** WhatsApp + Email Inbound (V1.1)
- **Mês 2-3:** Dashboard completo (V1.2)

---

## 🔐 Autenticação e Segurança (Implementado)

### API Key Authentication

**Status:** ✅ Implementado (22/01/2026)

Todos os endpoints da API agora requerem autenticação via API keys, exceto:
- `/` (root)
- `/docs` `/redoc` `/openapi.json` (documentação)
- `/api/health` (health check)
- `/telegram/webhook` (público - chamado pelo Telegram)

### Como Usar API Keys

#### 1. Criar Primeira API Key (Bootstrap)

```bash
python scripts/create_initial_api_key.py --company-id techcorp_001 --name "Initial Key"
```

Output:
```
✅ API Key created successfully!
Company ID: techcorp_001
Key ID: key_a1b2c3d4
API Key: sk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890

⚠️  IMPORTANT: Save this API key securely. It won't be shown again.
```

#### 2. Usar API Key nas Requisições

Todas as requisições devem incluir o header `X-API-Key`:

```bash
curl -X GET http://localhost:8000/api/tickets \
  -H "X-API-Key: sk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890"
```

#### 3. Gerenciar API Keys

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

### Company Isolation

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

### Arquivos Relacionados

- **Modelo:** `src/models/api_key.py`
- **Middleware:** `src/middleware/auth.py`
- **Routes:** `src/api/api_key_routes.py`
- **Script:** `scripts/create_initial_api_key.py`
- **Collections:** MongoDB `api_keys` collection

### Endpoints Protegidos (20)

#### Tickets (7)
- ✅ POST `/api/tickets` - Criar ticket
- ✅ POST `/api/run_pipeline/{ticket_id}` - Executar pipeline
- ✅ GET `/api/tickets/{ticket_id}` - Ver ticket
- ✅ GET `/api/tickets/{ticket_id}/audit` - Ver audit logs
- ✅ GET `/api/tickets/{ticket_id}/interactions` - Ver interações
- ✅ GET `/api/tickets/{ticket_id}/agent_states` - Ver estados de agentes
- ✅ GET `/api/tickets` - Listar tickets

#### Ingest (1)
- ✅ POST `/api/ingest-message` - Ingerir mensagem

#### Company Config (5)
- ✅ POST `/api/companies/` - Criar config
- ✅ GET `/api/companies/{company_id}` - Ver config
- ✅ PUT `/api/companies/{company_id}` - Atualizar config
- ✅ DELETE `/api/companies/{company_id}` - Deletar config
- ✅ GET `/api/companies/` - Listar configs

#### Human Agent (2)
- ✅ POST `/api/human/reply` - Responder ticket escalado
- ✅ GET `/api/human/escalated` - Listar tickets escalados

#### Telegram Admin (4)
- ✅ GET `/telegram/webhook/info` - Info do webhook
- ✅ POST `/telegram/webhook/set` - Configurar webhook
- ✅ POST `/telegram/webhook/delete` - Deletar webhook
- ✅ GET `/telegram/bot/info` - Info do bot

#### API Keys (3)
- ✅ POST `/api/keys/` - Criar API key
- ✅ GET `/api/keys/` - Listar API keys
- ✅ DELETE `/api/keys/{key_id}` - Revogar API key

### Boas Práticas

**DO:**
- ✅ Criar uma API key por ambiente (dev, staging, prod)
- ✅ Revogar keys antigas quando não mais necessárias
- ✅ Usar nomes descritivos para as keys
- ✅ Armazenar keys em variáveis de ambiente, não no código

**DON'T:**
- ❌ Commitar API keys no git
- ❌ Compartilhar API keys entre empresas
- ❌ Usar a mesma key para múltiplos ambientes
- ❌ Expor API keys em logs ou mensagens de erro

---

## 🔐 Dashboard Authentication (JWT)

**Status:** ✅ Implementado (22/01/2026)

O Streamlit Dashboard agora possui sistema completo de autenticação com JWT tokens.

### Como Funciona

**Login Flow:**
1. Usuário acessa `http://localhost:8501`
2. Apresenta tela de login (email + senha)
3. Backend valida credenciais e verifica senha com bcrypt
4. Cria JWT token com dados do usuário (validade: 24h)
5. Armazena token em `st.session_state`
6. Redireciona para dashboard com sidebar mostrando dados do usuário

**Session Management:**
- JWT token verificado em cada reload de página
- Token contém: `user_id`, `company_id`, `email`, `full_name`, `role`
- Expiração automática após 24h
- Logout limpa session e redireciona para login

**Company Isolation (CRÍTICO):**
- Todos os componentes do dashboard filtram por `company_id` do usuário autenticado
- Impossível ver/modificar dados de outras empresas
- Queries MongoDB sempre incluem filtro: `{"company_id": user_data["company_id"]}`

### Como Criar Usuários

#### 1. Criar Primeiro Usuário (Bootstrap)

```bash
python scripts/create_dashboard_user.py \
    --email admin@techcorp.com \
    --password Admin123! \
    --company-id techcorp_001 \
    --full-name "Admin Techcorp" \
    --role admin
```

Output:
```
✅ User created successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User ID:     user_a1b2c3d4e5f6g7h8
Email:       admin@techcorp.com
Full Name:   Admin Techcorp
Company ID:  techcorp_001
Role:        admin
Active:      True
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 Login Information:
   Email:    admin@techcorp.com
   Password: Admin123!

🌐 Dashboard URL:
   http://localhost:8501
```

#### 2. Criar Usuário Operador

```bash
python scripts/create_dashboard_user.py \
    --email operador@techcorp.com \
    --password Operador123! \
    --company-id techcorp_001 \
    --full-name "João Silva"
    # role padrão é "operator"
```

### Roles de Usuário

**Admin:**
- Acesso completo ao dashboard
- Pode modificar configurações do bot
- Pode gerenciar produtos
- Pode responder tickets escalados

**Operator:**
- Pode visualizar tickets escalados
- Pode responder tickets
- Pode visualizar configurações (sem editar)

### Segurança

**Senhas:**
- Hasheadas com bcrypt (custo: 12 rounds)
- Truncadas automaticamente a 72 bytes (limite do bcrypt)
- Nunca armazenadas em plaintext

**JWT Tokens:**
- Assinados com `settings.jwt_secret_key` (deve ser configurado no `.env`)
- Algoritmo: HS256
- Payload inclui: `user_id`, `company_id`, `email`, `full_name`, `role`, `exp`, `iat`
- Expiração: 24 horas

**Company Isolation:**
```python
# ✅ CORRETO - Todos os componentes filtram por company_id
def render_escalated_inbox(company_id: str):
    tickets = tickets_col.find({
        "status": "escalated",
        "company_id": company_id  # ← CRÍTICO
    })

# ❌ ERRADO - Sem filtro, vaza dados de outras empresas
def render_escalated_inbox():
    tickets = tickets_col.find({"status": "escalated"})
```

### Arquivos Relacionados

**Modelo:**
- `src/models/user.py` - User model com hash/verify de senha

**JWT Handler:**
- `src/utils/jwt_handler.py` - create_jwt_token, verify_jwt_token, refresh_jwt_token

**Dashboard:**
- `src/dashboard/app.py` - Login, autenticação, session management
- `src/dashboard/components/escalated_inbox.py` - Filtro por company_id
- `src/dashboard/components/bot_config.py` - Filtro por company_id
- `src/dashboard/components/products_config.py` - Filtro por company_id

**Script:**
- `scripts/create_dashboard_user.py` - Criação de usuários

**Database:**
- MongoDB `users` collection

### Configuração Necessária

**`.env` file:**
```bash
# JWT Secret (IMPORTANTE: Gerar valor único em produção)
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

**Gerar secret seguro:**
```python
import secrets
print(secrets.token_urlsafe(32))
# Output: "AbCdEfGhIjKlMnOpQrStUvWxYz1234567890AbCdEf"
```

### Boas Práticas

**DO:**
- ✅ Usar senhas fortes (mínimo 8 chars, letras + números + símbolos)
- ✅ Configurar `JWT_SECRET_KEY` única por ambiente
- ✅ Criar usuários separados por operador (não compartilhar credenciais)
- ✅ Desativar usuários que saíram da empresa (`active: False`)

**DON'T:**
- ❌ Usar `JWT_SECRET_KEY` padrão em produção
- ❌ Compartilhar credenciais de login
- ❌ Deletar usuários (desative com `active: False` para manter audit trail)
- ❌ Commitar senhas no git

### Troubleshooting

**Login não funciona:**
```bash
# 1. Verificar se usuário existe no MongoDB
mongo --eval 'db.users.findOne({email: "admin@techcorp.com"})'

# 2. Verificar se senha foi hasheada corretamente
# Password hash deve começar com "$2b$"

# 3. Verificar logs do Streamlit
streamlit run src/dashboard/app.py
```

**JWT expira muito rápido:**
```bash
# Aumentar tempo de expiração em .env
JWT_EXPIRATION_HOURS=48  # 2 dias
```

**KeyError ao fazer login:**
```bash
# Erro: KeyError: 'full_name' ou 'role'
# Fix: Fazer logout e login novamente (token antigo não tem esses campos)
```

---

## 🚀 Guias de Modificação

### 1. Adicionando um Novo Agente

**Quando:** Você quer adicionar um 5º agente ao pipeline (ex: SentimentAnalyzerAgent)

**Passos:**

1. **Criar classe do agente** em `src/agents/`

```python
# src/agents/sentiment_analyzer.py
from src.agents.base import BaseAgent, AgentResult
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class SentimentAnalyzerAgent(BaseAgent):
    """
    Analisa o sentimento detalhado das interações.

    Responsabilidades:
    - Analisa sentimento em escala numérica (-1.0 a 1.0)
    - Detecta emoções específicas (raiva, frustração, felicidade)
    - Identifica urgência emocional
    """

    def __init__(self, company_id: str):
        super().__init__(agent_name="SentimentAnalyzerAgent", company_id=company_id)

    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session=None
    ) -> AgentResult:
        """
        Executa análise de sentimento.

        Args:
            ticket_id: ID do ticket
            context: Contexto com ticket, interações, etc
            session: MongoDB session (para transactions)

        Returns:
            AgentResult com sentiment_score, emotions, urgency
        """
        try:
            # 1. Extract message
            last_interaction = context["interactions"][-1]
            message = last_interaction["message"]

            # 2. Call OpenAI
            result = await self._analyze_with_openai(message)

            # 3. Save state
            await self.save_state(ticket_id, result, session)

            # 4. Audit log
            await self.log_action(ticket_id, "sentiment_analyzed", result, session)

            return AgentResult(
                success=True,
                data=result,
                next_action="continue"
            )

        except Exception as e:
            logger.error(f"SentimentAnalyzer failed: {e}", exc_info=True)
            # Fallback to simple sentiment
            return self._fallback_sentiment()

    async def _analyze_with_openai(self, message: str) -> Dict[str, Any]:
        """Usa OpenAI para análise detalhada"""
        # Implementation here
        pass

    def _fallback_sentiment(self) -> AgentResult:
        """Fallback se OpenAI falhar"""
        return AgentResult(
            success=True,
            data={"sentiment_score": 0.0, "emotions": [], "urgency": "low"},
            next_action="continue"
        )
```

2. **Adicionar ao pipeline** em `src/utils/pipeline.py`

```python
# src/utils/pipeline.py
from src.agents.sentiment_analyzer import SentimentAnalyzerAgent

class AgentPipeline:
    async def run_pipeline(self, ticket_id: str) -> Dict[str, Any]:
        # ... existing code ...

        # Execute agents sequentially
        triage_result = await triage_agent.execute(ticket_id, context, session)

        # NOVO: Add sentiment analyzer after triage
        sentiment_agent = SentimentAnalyzerAgent(self.company_id)
        sentiment_result = await sentiment_agent.execute(ticket_id, context, session)

        router_result = await router_agent.execute(ticket_id, context, session)
        # ... rest of pipeline
```

3. **Criar testes** em `tests/scenarios/`

```python
# tests/scenarios/test_sentiment.py
import pytest
from src.agents.sentiment_analyzer import SentimentAnalyzerAgent

@pytest.mark.asyncio
async def test_sentiment_analyzer_positive():
    """Test sentiment analyzer with positive message"""
    agent = SentimentAnalyzerAgent(company_id="test_company")
    context = {
        "interactions": [
            {"message": "Thank you so much! Very helpful!", "sender": "customer"}
        ]
    }
    result = await agent.execute("TEST-001", context)
    assert result.success
    assert result.data["sentiment_score"] > 0.5
```

4. **Atualizar documentação**
   - Adicionar seção no `ARCHITECTURE.md` sobre o novo agente
   - Atualizar diagramas de pipeline

---

### 2. Adicionando um Novo Canal (ex: WhatsApp)

**Quando:** Você quer adicionar suporte a WhatsApp além de Telegram

**Passos:**

1. **Criar adapter** em `src/adapters/`

```python
# src/adapters/whatsapp_adapter.py
from typing import Dict, Any
import httpx
import logging

logger = logging.getLogger(__name__)

class WhatsAppAdapter:
    """
    Adapter para WhatsApp Business API.

    Responsabilidades:
    - Enviar mensagens via WhatsApp API
    - Formatar mensagens para WhatsApp
    - Lidar com media (imagens, documentos)
    """

    def __init__(self, api_token: str, phone_number_id: str):
        self.api_token = api_token
        self.phone_number_id = phone_number_id
        self.base_url = "https://graph.facebook.com/v18.0"

    async def send_message(
        self,
        to: str,
        message: str,
        company_id: str
    ) -> bool:
        """
        Envia mensagem via WhatsApp.

        Args:
            to: Número do destinatário (com código país)
            message: Texto da mensagem
            company_id: ID da empresa

        Returns:
            True se enviado com sucesso
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/{self.phone_number_id}/messages",
                    headers={
                        "Authorization": f"Bearer {self.api_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "messaging_product": "whatsapp",
                        "to": to,
                        "type": "text",
                        "text": {"body": message}
                    }
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"WhatsApp send failed: {e}", exc_info=True)
            return False

    def format_message(self, text: str, company_config: Dict[str, Any]) -> str:
        """Formata mensagem para WhatsApp (max 4096 chars)"""
        if len(text) > 4096:
            text = text[:4093] + "..."
        return text
```

2. **Criar routes** em `src/api/`

```python
# src/api/whatsapp_routes.py
from fastapi import APIRouter, HTTPException, Request
from src.adapters.whatsapp_adapter import WhatsAppAdapter
from src.database.operations import find_or_create_ticket, save_interaction
from src.utils.pipeline import AgentPipeline
import logging

router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Webhook para receber mensagens do WhatsApp.

    WhatsApp envia:
    {
        "object": "whatsapp_business_account",
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "5511999999999",
                        "text": {"body": "Olá!"},
                        "timestamp": "1234567890"
                    }]
                }
            }]
        }]
    }
    """
    try:
        data = await request.json()

        # Extract message
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "ok"}

        message_data = value["messages"][0]
        from_number = message_data["from"]
        text = message_data["text"]["body"]

        # Find company by phone_number_id (add to company_configs)
        phone_number_id = value["metadata"]["phone_number_id"]
        company_id = await get_company_by_whatsapp_number(phone_number_id)

        # Create/update ticket
        ticket = await find_or_create_ticket(
            customer_phone=from_number,
            channel="whatsapp",
            message=text,
            company_id=company_id
        )

        # Save interaction
        await save_interaction(
            ticket_id=ticket["ticket_id"],
            sender="customer",
            message=text,
            channel="whatsapp",
            company_id=company_id
        )

        # Run pipeline
        pipeline = AgentPipeline(company_id=company_id)
        result = await pipeline.run_pipeline(ticket["ticket_id"])

        # Send response via WhatsApp
        if result.get("response") and not ticket.get("escalated"):
            adapter = WhatsAppAdapter(
                api_token=os.getenv("WHATSAPP_API_TOKEN"),
                phone_number_id=phone_number_id
            )
            await adapter.send_message(from_number, result["response"], company_id)

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/webhook")
async def whatsapp_webhook_verify(request: Request):
    """Verifica webhook (WhatsApp envia GET para verificar)"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")
```

3. **Registrar router** em `main.py`

```python
# main.py
from src.api import whatsapp_routes

app.include_router(whatsapp_routes.router)
```

4. **Atualizar modelos** em `src/models/ticket.py`

```python
# src/models/ticket.py
class ChannelType(str, Enum):
    telegram = "telegram"
    email = "email"
    whatsapp = "whatsapp"  # NOVO
```

5. **Adicionar env vars** em `.env.example`

```bash
# WhatsApp Business API
WHATSAPP_API_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_VERIFY_TOKEN=your_verify_token
```

6. **Criar testes**

```python
# tests/scenarios/test_whatsapp.py
import pytest
from src.adapters.whatsapp_adapter import WhatsAppAdapter

@pytest.mark.asyncio
async def test_whatsapp_send_message():
    """Test sending message via WhatsApp"""
    adapter = WhatsAppAdapter(
        api_token="test_token",
        phone_number_id="test_id"
    )
    # Mock httpx call
    # Assert message sent
```

---

### 3. Modificando Lógica de um Agente Existente

**Quando:** Você quer melhorar o ResolverAgent para usar mais contexto

**Regras Importantes:**

1. **Preserve o fallback:** Sempre mantenha lógica fallback se OpenAI falhar
2. **Mantenha a interface:** Não mude a assinatura de `execute()`
3. **Salve o estado:** Sempre chame `save_state()` e `log_action()`
4. **Use transactions:** Sempre passe `session` para operações DB

**Exemplo:**

```python
# src/agents/resolver.py

# ANTES
async def execute(self, ticket_id, context, session=None):
    message = context["last_message"]
    response = await self._generate_response(message)
    return AgentResult(success=True, data={"response": response})

# DEPOIS (melhorado)
async def execute(self, ticket_id, context, session=None):
    # Build richer context
    message = context["last_message"]
    customer_history = context.get("customer_history", [])
    company_policies = context.get("company_config", {}).get("policies", {})

    # Use RAG
    kb_results = await self.knowledge_base.search(message, company_id=self.company_id)

    # Generate response with more context
    response = await self._generate_response(
        message=message,
        history=customer_history,
        policies=company_policies,
        knowledge=kb_results
    )

    # Save state (IMPORTANTE!)
    await self.save_state(
        ticket_id,
        {"response": response, "kb_used": len(kb_results) > 0},
        session
    )

    # Audit log (IMPORTANTE!)
    await self.log_action(
        ticket_id,
        "response_generated",
        {"response_length": len(response), "kb_results": len(kb_results)},
        session
    )

    return AgentResult(success=True, data={"response": response})
```

---

### 4. Adicionando Nova Feature ao Dashboard

**Quando:** Você quer adicionar uma página de métricas ao Streamlit

**Passos:**

1. **Criar nova página** em `src/dashboard/`

```python
# src/dashboard/pages/metrics.py
import streamlit as st
from src.database.operations import get_collection, COLLECTION_TICKETS
from datetime import datetime, timedelta

async def show_metrics_page(company_id: str):
    """Página de métricas e analytics"""

    st.title("📊 Métricas e Analytics")

    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        date_from = st.date_input("De", datetime.now() - timedelta(days=7))
    with col2:
        date_to = st.date_input("Até", datetime.now())

    # Buscar dados
    tickets_collection = get_collection(COLLECTION_TICKETS)
    tickets = await tickets_collection.find({
        "company_id": company_id,
        "created_at": {
            "$gte": datetime.combine(date_from, datetime.min.time()),
            "$lte": datetime.combine(date_to, datetime.max.time())
        }
    }).to_list(length=None)

    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Tickets", len(tickets))
    with col2:
        escalated = [t for t in tickets if t.get("escalated")]
        st.metric("Escalados", len(escalated),
                  delta=f"{len(escalated)/len(tickets)*100:.1f}%")
    with col3:
        resolved = [t for t in tickets if t.get("status") == "resolved"]
        st.metric("Resolvidos", len(resolved))
    with col4:
        avg_interactions = sum(t.get("interactions_count", 0) for t in tickets) / len(tickets) if tickets else 0
        st.metric("Avg Interações", f"{avg_interactions:.1f}")

    # Gráficos
    st.subheader("Tickets por Categoria")
    category_counts = {}
    for ticket in tickets:
        cat = ticket.get("category", "unknown")
        category_counts[cat] = category_counts.get(cat, 0) + 1
    st.bar_chart(category_counts)
```

2. **Integrar no app principal** em `src/dashboard/app.py`

```python
# src/dashboard/app.py
import streamlit as st
from src.dashboard.pages import metrics

# Sidebar navigation
page = st.sidebar.radio("Navegação", ["Inbox", "Métricas", "Configurações"])

if page == "Métricas":
    await metrics.show_metrics_page(st.session_state.company_id)
```

---

## 🔒 Padrões Obrigatórios

### Security Patterns (CRÍTICO)

```python
# ✅ BOM - Input sanitization
from html import escape

def sanitize_user_input(text: str, max_length: int = 4000) -> str:
    """Sanitiza input de usuário"""
    # Truncate
    text = text[:max_length]
    # Escape HTML
    text = escape(text)
    # Remove null bytes
    text = text.replace('\x00', '')
    return text

# Uso
customer_message = sanitize_user_input(raw_input)

# ❌ RUIM - Input direto no DB
await save_interaction(message=raw_input)  # XSS vulnerability!
```

```python
# ✅ BOM - API key validation
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(...)):
    """Valida API key"""
    api_keys_collection = get_collection("api_keys")
    key_doc = await api_keys_collection.find_one({"key": x_api_key, "active": True})

    if not key_doc:
        raise HTTPException(status_code=403, detail="Invalid API key")

    return key_doc

# Uso em route
@router.post("/api/ingest-message")
async def ingest(request: IngestRequest, api_key: dict = Depends(verify_api_key)):
    # Verificar company isolation
    if request.company_id != api_key["company_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized company access")

# ❌ RUIM - Sem autenticação
@router.post("/api/ingest-message")
async def ingest(request: IngestRequest):
    # Qualquer um pode acessar!
```

```python
# ✅ BOM - Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/ingest-message")
@limiter.limit("100/minute")
async def ingest(request: Request):
    pass

# ❌ RUIM - Sem rate limit
@app.post("/api/ingest-message")
async def ingest(request: Request):
    # Pode ser abusado (DoS)
```

```python
# ✅ BOM - Secrets não hardcoded
from src.config import settings

openai_key = settings.OPENAI_API_KEY
mongo_uri = settings.MONGODB_URI

# ❌ RUIM - Hardcoded secrets
openai_key = "sk-proj-abc123..."  # NUNCA faça isso!
```

### Python Code Style

```python
# ✅ BOM
async def find_or_create_ticket(
    customer_phone: str,
    channel: str,
    message: str,
    company_id: str
) -> Dict[str, Any]:
    """
    Encontra ticket existente ou cria novo.

    Args:
        customer_phone: Telefone do cliente (formato: +5511999999999)
        channel: Canal de origem (telegram, whatsapp, email)
        message: Mensagem inicial
        company_id: ID da empresa

    Returns:
        Dict com dados do ticket criado/encontrado

    Raises:
        ValueError: Se company_id for inválido
    """
    # Implementation
    pass

# ❌ RUIM (sem type hints, sem docstring)
def find_ticket(phone, msg):
    pass
```

### Async/Await

```python
# ✅ BOM - Async para I/O
async def get_ticket(ticket_id: str) -> Dict[str, Any]:
    tickets = get_collection(COLLECTION_TICKETS)
    ticket = await tickets.find_one({"ticket_id": ticket_id})
    return ticket

# ❌ RUIM - Sync para operação I/O
def get_ticket(ticket_id: str) -> Dict[str, Any]:
    tickets = get_collection(COLLECTION_TICKETS)
    ticket = tickets.find_one({"ticket_id": ticket_id})  # Blocking!
    return ticket
```

### Error Handling

```python
# ✅ BOM - Try-catch + logging + fallback
async def call_openai(prompt: str) -> str:
    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI call failed: {e}", exc_info=True)
        # Fallback to rule-based
        return self._fallback_response()

# ❌ RUIM - Sem error handling
async def call_openai(prompt: str) -> str:
    response = await openai_client.chat.completions.create(...)
    return response.choices[0].message.content
```

### MongoDB Operations

```python
# ✅ BOM - Com transaction e optimistic locking
async def update_ticket_status(ticket_id: str, status: str, session=None):
    tickets = get_collection(COLLECTION_TICKETS)

    # Get current version
    ticket = await tickets.find_one({"ticket_id": ticket_id}, session=session)
    current_version = ticket.get("lock_version", 0)

    # Update with version check
    result = await tickets.update_one(
        {
            "ticket_id": ticket_id,
            "lock_version": current_version
        },
        {
            "$set": {"status": status, "updated_at": datetime.now()},
            "$inc": {"lock_version": 1}
        },
        session=session
    )

    if result.modified_count == 0:
        raise ConcurrencyError("Ticket was modified by another process")

# ❌ RUIM - Sem locking, sem transaction
async def update_ticket_status(ticket_id: str, status: str):
    tickets = get_collection(COLLECTION_TICKETS)
    await tickets.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": status}}
    )
```

### Logging

```python
# ✅ BOM - Structured logging
logger.info(
    "Ticket created",
    extra={
        "ticket_id": ticket_id,
        "company_id": company_id,
        "channel": channel
    }
)

logger.error(
    "Agent execution failed",
    exc_info=True,
    extra={"agent": "ResolverAgent", "ticket_id": ticket_id}
)

# ❌ RUIM - String interpolation, sem contexto
logger.info(f"Created ticket {ticket_id}")
logger.error("Error in agent")
```

---

## 🧪 Testing Requirements

### Quando Adicionar Testes

**SEMPRE adicione testes quando:**
- Criar novo agente
- Adicionar novo canal
- Modificar lógica crítica (escalation, routing, etc)
- Adicionar nova rota API

### Estrutura de Teste

```python
# tests/scenarios/test_new_feature.py
import pytest
from src.database.operations import setup_test_db, cleanup_test_db

@pytest.fixture(scope="module")
async def setup_database():
    """Setup test database"""
    await setup_test_db()
    yield
    await cleanup_test_db()

@pytest.mark.asyncio
async def test_feature_happy_path(setup_database):
    """Test feature with valid input"""
    # Arrange
    input_data = {...}

    # Act
    result = await function_to_test(input_data)

    # Assert
    assert result["success"] is True
    assert result["data"]["field"] == expected_value

@pytest.mark.asyncio
async def test_feature_error_handling(setup_database):
    """Test feature with invalid input"""
    # Arrange
    invalid_data = {...}

    # Act & Assert
    with pytest.raises(ValueError):
        await function_to_test(invalid_data)

@pytest.mark.asyncio
async def test_feature_edge_case(setup_database):
    """Test feature with edge case"""
    # Test empty input, null values, etc
    pass
```

### Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Teste específico
pytest tests/scenarios/test_routing.py::test_route_to_billing -v

# Com coverage
pytest --cov=src tests/

# Apenas testes rápidos (skip slow)
pytest -m "not slow" tests/
```

---

## 📝 Commit Conventions

### Formato

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- `feat`: Nova feature
- `fix`: Bug fix
- `docs`: Documentação
- `refactor`: Refatoração (sem mudança de comportamento)
- `test`: Adicionar/modificar testes
- `chore`: Manutenção (deps, configs)
- `perf`: Performance improvement

### Exemplos

```bash
# Feature
git commit -m "feat(agents): add SentimentAnalyzerAgent to pipeline"

# Bug fix
git commit -m "fix(resolver): handle empty knowledge base results"

# Documentation
git commit -m "docs(architecture): update agent pipeline diagram"

# Refactor
git commit -m "refactor(database): extract connection logic to separate module"

# Test
git commit -m "test(escalation): add tests for SLA breach scenario"

# Multiple changes
git commit -m "feat(channels): add WhatsApp support

- Create WhatsAppAdapter
- Add webhook routes
- Update ChannelType enum
- Add tests for WhatsApp flow"
```

---

## 🔍 Code Navigation Tips for AI

### Encontrar Onde Modificar

| Tarefa | Arquivo Principal | Arquivos Relacionados |
|--------|------------------|---------------------|
| Mudar lógica de agente | `src/agents/{agent}.py` | `src/utils/pipeline.py` |
| Adicionar endpoint API | `src/api/{resource}_routes.py` | `main.py` (registrar router) |
| Mudar schema MongoDB | `src/models/{model}.py` | `src/database/operations.py` |
| Adicionar canal | `src/adapters/{channel}_adapter.py` | `src/api/{channel}_routes.py`, `src/models/ticket.py` |
| Mudar RAG logic | `src/rag/knowledge_base.py` | `src/agents/resolver.py` |
| Adicionar config empresa | `src/models/company_config.py` | `src/utils/pipeline.py` (context building) |
| Mudar UI dashboard | `src/dashboard/app.py` | `src/dashboard/pages/*.py` |

### Debugging Flow

1. **Mensagem não chegou?**
   - Check: `src/api/ingest_routes.py`
   - Check: `src/bots/telegram_bot.py` (se Telegram)

2. **Agente não executou?**
   - Check: `src/utils/pipeline.py` (pipeline execution)
   - Check logs: agente específico em `src/agents/`

3. **Resposta não enviou?**
   - Check: `src/adapters/{channel}_adapter.py`
   - Check: Ticket escalated? (escalados não enviam resposta automática)

4. **RAG não retornou resultados?**
   - Check: `src/rag/knowledge_base.py`
   - Check: ChromaDB tem documentos? `ls chroma_db/`

---

## ⚠️ Common Pitfalls (Evite!)

### 1. Esquecer Transaction

```python
# ❌ RUIM
async def update_ticket_and_save_interaction(ticket_id, message):
    await update_ticket(ticket_id, {"status": "in_progress"})
    await save_interaction(ticket_id, message)
    # Se save_interaction falhar, ticket fica inconsistente!

# ✅ BOM
@with_transaction
async def update_ticket_and_save_interaction(ticket_id, message, session=None):
    await update_ticket(ticket_id, {"status": "in_progress"}, session=session)
    await save_interaction(ticket_id, message, session=session)
    # Se qualquer operação falhar, rollback automático
```

### 2. Hardcoded Values (Use Company Config!)

```python
# ❌ RUIM
refund_policy = "Reembolso em até 7 dias"

# ✅ BOM
company_config = await get_company_config(company_id)
refund_policy = company_config["policies"]["refund_policy"]
```

### 3. Não Validar com Pydantic

```python
# ❌ RUIM
def create_ticket(data: dict):
    ticket_id = data["ticket_id"]  # E se não existir?
    # ...

# ✅ BOM
from src.models.ticket import TicketCreate

def create_ticket(data: TicketCreate):  # Pydantic valida automaticamente
    ticket_id = data.ticket_id
    # ...
```

### 4. Bloquear Event Loop

```python
# ❌ RUIM
import time
time.sleep(5)  # Bloqueia o event loop!

# ✅ BOM
import asyncio
await asyncio.sleep(5)  # Non-blocking
```

### 5. Não Logar Erros

```python
# ❌ RUIM
try:
    result = await risky_operation()
except:
    pass  # Erro silencioso, impossível debugar

# ✅ BOM
try:
    result = await risky_operation()
except Exception as e:
    logger.error(f"Risky operation failed: {e}", exc_info=True)
    raise  # Re-raise ou retornar fallback
```

---

## 📚 Recursos Adicionais

### Documentos para Consultar

- `ARCHITECTURE.md` - Visão geral do projeto
- `docs/MULTI_TENANCY.md` - Como multi-tenancy funciona
- `docs/TELEGRAM_SETUP.md` - Setup Telegram bot
- `docs/mongodb_collections.md` - Schema detalhado

### External Docs

- FastAPI: https://fastapi.tiangolo.com/
- Motor (MongoDB async): https://motor.readthedocs.io/
- OpenAI API: https://platform.openai.com/docs/
- ChromaDB: https://docs.trychroma.com/
- Streamlit: https://docs.streamlit.io/

---

## 🎯 Checklist Antes de Commit

- [ ] Código segue style guide (type hints, docstrings)
- [ ] Async/await usado para I/O
- [ ] Error handling implementado
- [ ] Logging adicionado
- [ ] Testes criados/atualizados
- [ ] Testes passando (`pytest tests/ -v`)
- [ ] Documentação atualizada (ARCHITECTURE.md se necessário)
- [ ] Commit message seguindo convenção
- [ ] Sem secrets no código (.env usado corretamente)

---

## 🆘 Quando em Dúvida

1. **Não tem certeza se deve criar um agente novo?**
   - Se a responsabilidade é muito diferente dos 4 agentes atuais: SIM
   - Se é apenas melhoria de um agente: NÃO, modifique o existente

2. **Não sabe onde colocar uma função helper?**
   - Se é específica de um agente: dentro do arquivo do agente
   - Se é usada por múltiplos agentes: `src/utils/`
   - Se é operação DB: `src/database/operations.py`

3. **Não sabe se deve usar transaction?**
   - Múltiplas operações DB que precisam ser atômicas: SIM
   - Single read operation: NÃO
   - Pipeline execution: SIM (já está implementado)

4. **Não sabe qual modelo OpenAI usar?**
   - Default: `gpt-4o-mini` (rápido e barato)
   - Tarefas complexas: `gpt-4-turbo`
   - Embeddings: `text-embedding-3-small`

---

**Última atualização:** 2026-01-20
**Versão:** 1.0
**Mantenedor:** Aethera Labs Team
