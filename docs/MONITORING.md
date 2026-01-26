# Monitoring & Error Tracking Guide

> **Sentry integration para monitoramento de erros e performance em produção**

---

## 📊 Overview

O sistema usa **Sentry** para:
- ✅ Rastreamento automático de erros
- ✅ Monitoramento de performance (APM)
- ✅ Tracking de requests HTTP
- ✅ Contexto de usuário e empresa (multi-tenancy)
- ✅ Breadcrumbs para debug
- ✅ Release tracking (versionamento)
- ✅ Alertas configuráveis

---

## 🚀 Setup

### 1. Criar projeto no Sentry

1. Acesse [sentry.io](https://sentry.io)
2. Crie novo projeto (Python/FastAPI)
3. Copie o **DSN** (Data Source Name)

### 2. Configurar variáveis de ambiente

```bash
# .env
SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/7891011
SENTRY_ENVIRONMENT=production  # ou staging, development
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% = monitorar todas as requests (produção: 0.1 = 10%)
SENTRY_PROFILES_SAMPLE_RATE=1.0  # Profiling rate
```

### 3. Verificar instalação

```bash
# Sentry SDK já está em requirements.txt
pip install sentry-sdk[fastapi]

# Testar configuração
python -c "from src.utils.monitoring import init_sentry; init_sentry()"
```

### 4. Deploy

O Sentry é automaticamente inicializado no startup do FastAPI (main.py).

```python
# main.py
from src.utils.monitoring import init_sentry

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_sentry()  # ✅ Já configurado
    # ...
```

---

## 📝 Usage Examples

### Automatic Error Tracking

**Erros não tratados são capturados automaticamente:**

```python
@router.get("/api/tickets/{ticket_id}")
async def get_ticket(ticket_id: str):
    # Se ocorrer exceção, Sentry captura automaticamente
    ticket = await get_ticket_from_db(ticket_id)
    return ticket
```

**Sentry recebe:**
- Stack trace completo
- Request context (URL, method, headers)
- User context (se configurado)
- Breadcrumbs (logs, queries, etc)

### Manual Error Capture

```python
from src.utils.monitoring import capture_exception, capture_message

try:
    result = risky_operation()
except ValueError as e:
    # Capturar erro com contexto adicional
    capture_exception(
        e,
        level="error",
        tags={"operation": "risky_operation", "module": "pipeline"},
        extra={"input_data": data, "step": current_step}
    )
    # Pode re-raise ou retornar fallback
    raise
```

### Capture Messages (não erros)

```python
from src.utils.monitoring import capture_message

# Capturar evento importante (não erro)
capture_message(
    "High confidence response generated",
    level="info",
    tags={"ticket_id": ticket_id, "confidence": str(confidence)},
    extra={"response_length": len(response)}
)
```

### User Context (Multi-Tenancy)

```python
from src.utils.monitoring import set_user_context

# No middleware ou endpoint
set_user_context(
    user_id="user_abc123",
    email="admin@empresa.com",
    company_id="empresa_001",  # Important for multi-tenancy
    role="admin"
)

# Agora todos os erros incluem contexto do usuário
```

### Custom Context

```python
from src.utils.monitoring import set_context

# Adicionar contexto específico do domínio
set_context("ticket", {
    "ticket_id": "TICKET-123",
    "priority": "high",
    "category": "billing",
    "escalated": True
})

set_context("pipeline", {
    "current_agent": "ResolverAgent",
    "step": 3,
    "total_steps": 4
})
```

### Breadcrumbs (Debug Trail)

```python
from src.utils.monitoring import add_breadcrumb

# Adicionar breadcrumbs para reconstruir fluxo
add_breadcrumb(
    message="Started pipeline execution",
    category="pipeline",
    level="info",
    data={"ticket_id": ticket_id}
)

add_breadcrumb(
    message="Queried RAG knowledge base",
    category="rag",
    level="debug",
    data={"query": user_message, "results_count": len(results)}
)

add_breadcrumb(
    message="OpenAI API call",
    category="ai",
    level="info",
    data={"model": "gpt-3.5-turbo", "tokens": 150}
)

# Se ocorrer erro, Sentry mostra todos os breadcrumbs
```

### Performance Monitoring

**Transaction (request completo):**

```python
from src.utils.monitoring import start_transaction

async def process_ticket(ticket_id: str):
    with start_transaction(name="process_ticket", op="pipeline"):
        # Código monitorado
        ticket = await get_ticket(ticket_id)
        result = await run_agents(ticket)
        return result
```

**Spans (sub-operações):**

```python
from src.utils.monitoring import start_transaction, start_span

async def process_ticket(ticket_id: str):
    with start_transaction(name="process_ticket"):

        with start_span(op="db.query", description="Get ticket from MongoDB"):
            ticket = await tickets_collection.find_one({"ticket_id": ticket_id})

        with start_span(op="ai.inference", description="OpenAI completion"):
            response = await openai.chat.completions.create(...)

        with start_span(op="db.update", description="Save interaction"):
            await interactions_collection.insert_one(interaction)

    # Sentry mostra timeline de todas as operações
```

### Decorators

**Monitor performance automaticamente:**

```python
from src.utils.monitoring import monitor_performance

@monitor_performance(op="agent.execute")
async def execute_triage_agent(ticket_id: str):
    # Função automaticamente monitorada
    # Aparece no Sentry como "execute_triage_agent" transaction
    pass
```

**Capture erros automaticamente:**

```python
from src.utils.monitoring import capture_errors

@capture_errors(level="error", reraise=True)
async def critical_operation():
    # Erros são automaticamente enviados para Sentry
    # E ainda re-raised para tratamento local
    raise ValueError("Something went wrong")
```

---

## 🎯 Integration Examples

### Agent Pipeline Monitoring

```python
# src/utils/pipeline.py
from src.utils.monitoring import (
    start_transaction,
    start_span,
    set_context,
    add_breadcrumb,
    capture_exception
)

async def run_pipeline(ticket_id: str):
    with start_transaction(name="agent_pipeline", op="pipeline"):
        # Set context
        set_context("pipeline", {
            "ticket_id": ticket_id,
            "agents": ["Triage", "Router", "Resolver", "Escalator"]
        })

        try:
            # Step 1: Triage
            add_breadcrumb("Starting Triage Agent", category="pipeline")
            with start_span(op="agent.triage"):
                triage_result = await triage_agent.execute(ticket_id)

            # Step 2: Router
            add_breadcrumb("Starting Router Agent", category="pipeline")
            with start_span(op="agent.router"):
                router_result = await router_agent.execute(ticket_id)

            # Step 3: Resolver (with RAG)
            add_breadcrumb("Starting Resolver Agent", category="pipeline")
            with start_span(op="agent.resolver"):
                with start_span(op="rag.query", description="Query ChromaDB"):
                    rag_results = knowledge_base.query(message)

                with start_span(op="ai.completion", description="OpenAI GPT"):
                    response = await openai_client.create_completion(...)

            # Step 4: Escalator
            add_breadcrumb("Starting Escalator Agent", category="pipeline")
            with start_span(op="agent.escalator"):
                escalator_result = await escalator_agent.execute(ticket_id)

        except Exception as e:
            capture_exception(
                e,
                level="error",
                tags={"ticket_id": ticket_id, "pipeline_stage": "execution"}
            )
            raise
```

### API Endpoint Monitoring

```python
# src/api/ingest_routes.py
from src.utils.monitoring import (
    set_user_context,
    set_context,
    add_breadcrumb,
    capture_message
)

@router.post("/api/ingest-message")
async def ingest_message(request: IngestRequest, api_key: dict = Depends(verify_api_key)):
    # Set user context for multi-tenancy
    set_user_context(
        company_id=api_key["company_id"],
        user_id=request.external_user_id
    )

    # Set custom context
    set_context("message", {
        "channel": request.channel,
        "company_id": api_key["company_id"],
        "message_length": len(request.text)
    })

    # Add breadcrumbs
    add_breadcrumb(
        f"Message received from {request.channel}",
        category="ingestion",
        data={"company_id": api_key["company_id"]}
    )

    # Process message...
    ticket = await find_or_create_ticket(...)

    # Capture important events
    if ticket.get("newly_created"):
        capture_message(
            "New ticket created",
            level="info",
            tags={"company_id": api_key["company_id"], "channel": request.channel}
        )

    return {"status": "success", "ticket_id": ticket["ticket_id"]}
```

---

## 📊 Sentry Dashboard

### Eventos capturados

**Errors:**
- Exceções não tratadas
- Erros capturados manualmente
- HTTP 500 errors

**Performance:**
- Request duration (P50, P75, P95, P99)
- Slow endpoints
- Database query performance
- OpenAI API latency

**Custom Events:**
- Messages importantes (via `capture_message`)
- Business metrics

### Filtros úteis

```
# Ver erros de empresa específica
user.company_id:empresa_001

# Ver erros do pipeline
tags.module:pipeline

# Ver slow requests (> 2s)
transaction.duration:>2000

# Ver erros de OpenAI
tags.operation:ai.completion

# Ver erros por ambiente
environment:production
```

### Alertas recomendados

1. **High Error Rate**
   - Trigger: > 10 errors/min
   - Notification: Slack/Email

2. **Slow Requests**
   - Trigger: P95 > 5s
   - Notification: Email

3. **Failed Escalations**
   - Trigger: Custom event "escalation_failed"
   - Notification: PagerDuty

4. **Low Confidence Responses**
   - Trigger: Custom metric "confidence < 0.5"
   - Notification: Slack

---

## 🔧 Configuration

### Environment Variables

```bash
# Required
SENTRY_DSN=https://...@sentry.io/...

# Optional (with defaults)
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=auto-detected-from-git
SENTRY_TRACES_SAMPLE_RATE=1.0  # 1.0 = 100% (dev), 0.1 = 10% (prod)
SENTRY_PROFILES_SAMPLE_RATE=1.0
```

### Sampling Rates

**Development:**
```bash
SENTRY_TRACES_SAMPLE_RATE=1.0  # Monitor tudo
SENTRY_PROFILES_SAMPLE_RATE=1.0
```

**Production (high traffic):**
```bash
SENTRY_TRACES_SAMPLE_RATE=0.1  # Monitor 10% das requests
SENTRY_PROFILES_SAMPLE_RATE=0.01  # Profile 1%
```

**Custos Sentry:** Baseado em eventos enviados. Sampling reduz custos.

### Filtering

**Não enviar health checks:**

```python
# src/utils/monitoring.py (já configurado)
def _before_send_filter(event, hint):
    # Filtrar health checks
    if event.get("request", {}).get("url", "").endswith("/api/health"):
        return None  # Drop event
    return event
```

**Ignorar exceções específicas:**

```python
# Adicionar em _before_send_filter
if "exc_info" in hint:
    exc_type, exc_value, tb = hint["exc_info"]
    if isinstance(exc_value, IgnoredException):
        return None
```

---

## 📈 Best Practices

### 1. Use Tags for Filtering

```python
set_tag("company_id", "empresa_001")  # Multi-tenancy
set_tag("agent", "ResolverAgent")
set_tag("channel", "telegram")
set_tag("priority", "high")
```

### 2. Add Context Generously

```python
set_context("ticket", {...})
set_context("customer", {...})
set_context("pipeline_state", {...})
```

### 3. Breadcrumbs for Complex Flows

```python
# Cada step importante
add_breadcrumb("Step 1: Validate input")
add_breadcrumb("Step 2: Query database")
add_breadcrumb("Step 3: Call AI")
add_breadcrumb("Step 4: Save result")
```

### 4. Performance Spans

```python
# Granular spans para identificar bottlenecks
with start_span(op="db.query", description="Get customer history"):
    history = await db.find(...)

with start_span(op="ai.embedding", description="Embed query"):
    embedding = await get_embedding(text)
```

### 5. Sample Rate por Environment

- **Development:** 100% (debug tudo)
- **Staging:** 100% (testar antes de prod)
- **Production:** 10-20% (reduzir custos)

### 6. Release Tracking

```python
# Automático via git hash
SENTRY_RELEASE=customer-support@abc123

# Ou manual
SENTRY_RELEASE=v1.2.3
```

**Benefícios:**
- Ver quais releases causaram erros
- Comparar performance entre releases
- Rollback informado

---

## 🐛 Troubleshooting

### Sentry não está capturando erros

**Check 1:** SENTRY_DSN configurado?
```bash
echo $SENTRY_DSN
# Deve retornar: https://...@sentry.io/...
```

**Check 2:** Sentry inicializado?
```python
from src.utils.monitoring import is_enabled
print(is_enabled())  # Deve ser True
```

**Check 3:** Testar manualmente
```python
from src.utils.monitoring import capture_message
capture_message("Test from production", level="info")
```

### Performance tracking não aparece

**Check 1:** Tracing habilitado?
```bash
echo $SENTRY_TRACES_SAMPLE_RATE
# Deve ser > 0 (e.g., 1.0 para 100%)
```

**Check 2:** Transaction criada?
```python
from src.utils.monitoring import start_transaction

with start_transaction(name="test"):
    # Código aqui
    pass
```

### Muitos eventos / custos altos

**Solução 1:** Reduzir sample rate
```bash
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% das requests
```

**Solução 2:** Filtrar health checks (já configurado)

**Solução 3:** Ignorar erros conhecidos
```python
# Em _before_send_filter
if "specific_error" in str(exc_value):
    return None
```

---

## 💰 Custos Estimados

### Sentry Pricing (2026)

**Free Tier:**
- 5K errors/mês
- 10K transactions/mês
- 7 dias retenção

**Team Plan ($26/mês):**
- 50K errors/mês
- 100K transactions/mês
- 90 dias retenção

**Business Plan ($80/mês):**
- 500K errors/mês
- 1M transactions/mês
- 90 dias retenção

### Otimizar custos

1. **Sampling:** SENTRY_TRACES_SAMPLE_RATE=0.1
2. **Filtrar health checks** (já configurado)
3. **Usar Free tier em dev/staging**
4. **Production: Team ou Business plan**

---

## 📚 Resources

- [Sentry Python SDK](https://docs.sentry.io/platforms/python/)
- [FastAPI Integration](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Performance Monitoring](https://docs.sentry.io/product/performance/)
- [Releases](https://docs.sentry.io/product/releases/)

---

**Última atualização:** 2026-01-23
**Versão:** 1.0.0
**Autor:** Agent Claude - Backend/Infra Team
