# Circuit Breaker Pattern - OpenAI API

> **Resiliência e fallback automático para chamadas à OpenAI API**

---

## 📊 Overview

O **Circuit Breaker** protege o sistema contra falhas em cascata quando a OpenAI API está indisponível ou lenta.

**Problema sem Circuit Breaker:**
```
OpenAI API falha → Todas requests travam por 30s (timeout)
→ 100 requests simultâneas = 3000s desperdiçados
→ Sistema lento/travado
→ Custos de API desperdiçados
```

**Solução com Circuit Breaker:**
```
OpenAI API falha 5x → Circuit ABRE
→ Próximas requests usam fallback imediatamente
→ Sistema continua funcionando (modo degradado)
→ Após 30s: testa se API recuperou
→ Se OK: volta ao normal
```

---

## 🔄 Estados do Circuit Breaker

### 1. CLOSED (Normal)

```
┌─────────────┐
│   CLOSED    │  ← Estado inicial
│ (Normal)    │  Requests passam normalmente
└─────────────┘
      │
      │ 5 falhas consecutivas
      ▼
```

- Todas as requests vão para OpenAI API
- Contador de falhas é rastreado
- Se falhar 5x (threshold) → abre circuit

### 2. OPEN (Falhando)

```
┌─────────────┐
│    OPEN     │  Rejeita requests
│ (Failing)   │  Usa fallback
└─────────────┘
      │
      │ Após 30s (recovery timeout)
      ▼
```

- Requests **não** vão para OpenAI (fail fast)
- Fallback é usado automaticamente
- Economiza tempo e $$$
- Após 30s → tenta recovery (half-open)

### 3. HALF_OPEN (Testando)

```
┌─────────────┐
│ HALF_OPEN   │  Testando recovery
│ (Testing)   │  1 request por vez
└─────────────┘
      │
      ├─ 2 sucessos → CLOSED (recuperado)
      └─ 1 falha → OPEN (ainda falhando)
```

- Permite **algumas** requests de teste
- Se 2 sucessos → volta para CLOSED
- Se 1 falha → volta para OPEN

---

## 🚀 Usage

### Basic Usage

```python
from src.utils.circuit_breaker import get_openai_circuit_breaker

# Get global circuit breaker instance
circuit_breaker = get_openai_circuit_breaker()

# Call OpenAI with circuit breaker protection
result = await circuit_breaker.call(
    func=openai_client.chat.completions.create,
    fallback=rule_based_triage,  # Fallback function
    model="gpt-3.5-turbo",
    messages=[
        {"role": "user", "content": "Classify this ticket"}
    ]
)
```

**O que acontece:**
1. Se circuit está CLOSED → chama OpenAI
2. Se OpenAI falhar → usa `rule_based_triage` fallback
3. Se falhar 5x → circuit ABRE
4. Se circuit está OPEN → usa fallback direto (fail fast)
5. Após 30s → testa recovery

### Decorator Usage

```python
from src.utils.circuit_breaker import with_circuit_breaker

# Define fallback function
async def rule_based_triage(ticket_id: str, context: dict) -> dict:
    """Rule-based fallback when OpenAI is down"""
    # Classify based on keywords
    message = context.get("message", "").lower()

    if "payment" in message or "refund" in message:
        return {
            "priority": "high",
            "category": "billing",
            "sentiment": "neutral"
        }
    elif "not working" in message or "error" in message:
        return {
            "priority": "medium",
            "category": "technical",
            "sentiment": "negative"
        }
    else:
        return {
            "priority": "low",
            "category": "general",
            "sentiment": "neutral"
        }

# Decorate OpenAI call
@with_circuit_breaker(fallback=rule_based_triage)
async def ai_triage(ticket_id: str, context: dict) -> dict:
    """AI-based triage with automatic fallback"""
    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[...]
    )
    return parse_response(response)

# Use it
result = await ai_triage(ticket_id="TICKET-123", context=context)
# Automatically falls back to rule_based_triage if OpenAI fails
```

---

## 🎯 Agent Integration Examples

### Triage Agent

```python
# src/agents/triage.py
from src.utils.circuit_breaker import get_openai_circuit_breaker

class TriageAgent(BaseAgent):
    async def execute(self, ticket_id: str, context: dict) -> AgentResult:
        circuit_breaker = get_openai_circuit_breaker()

        try:
            # Try AI classification with circuit breaker
            result = await circuit_breaker.call(
                func=self._ai_classify,
                fallback=self._rule_based_classify,
                context=context
            )

            return AgentResult(
                success=True,
                data=result,
                metadata={"method": "ai" if not result.get("fallback") else "rules"}
            )

        except Exception as e:
            logger.error(f"Triage failed: {e}")
            # Last resort: basic classification
            return AgentResult(
                success=True,
                data={
                    "priority": "medium",
                    "category": "general",
                    "sentiment": "neutral"
                },
                metadata={"method": "default"}
            )

    async def _ai_classify(self, context: dict) -> dict:
        """AI-based classification"""
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a triage agent. Classify tickets."
                },
                {
                    "role": "user",
                    "content": context.get("message", "")
                }
            ]
        )
        # Parse and return
        return self._parse_ai_response(response)

    async def _rule_based_classify(self, context: dict) -> dict:
        """Rule-based fallback classification"""
        message = context.get("message", "").lower()

        # Keyword-based classification
        if any(word in message for word in ["urgent", "critical", "emergency"]):
            priority = "critical"
        elif any(word in message for word in ["payment", "refund", "billing"]):
            priority = "high"
            category = "billing"
        elif any(word in message for word in ["error", "not working", "broken"]):
            priority = "medium"
            category = "technical"
        else:
            priority = "low"
            category = "general"

        # Sentiment analysis (simple)
        sentiment = "negative" if any(word in message for word in ["angry", "frustrated"]) else "neutral"

        return {
            "priority": priority,
            "category": category,
            "sentiment": sentiment,
            "fallback": True  # Indicate fallback was used
        }
```

### Resolver Agent

```python
# src/agents/resolver.py
from src.utils.circuit_breaker import with_circuit_breaker

class ResolverAgent(BaseAgent):
    async def execute(self, ticket_id: str, context: dict) -> AgentResult:
        # Use decorator for automatic circuit breaker
        response = await self._generate_response(context)

        return AgentResult(
            success=True,
            data={
                "response": response["text"],
                "confidence": response.get("confidence", 0.5)
            }
        )

    @with_circuit_breaker(fallback=lambda self, ctx: self._template_response(ctx))
    async def _generate_response(self, context: dict) -> dict:
        """Generate response with AI (automatic fallback)"""
        # RAG query
        rag_results = await knowledge_base.query(context.get("message"))

        # OpenAI completion
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": f"Use this knowledge: {rag_results}"
                },
                {
                    "role": "user",
                    "content": context.get("message")
                }
            ]
        )

        return {
            "text": response.choices[0].message.content,
            "confidence": 0.8
        }

    async def _template_response(self, context: dict) -> dict:
        """Template-based fallback response"""
        category = context.get("category", "general")

        templates = {
            "billing": "Recebemos sua solicitação sobre faturamento. Nossa equipe retornará em breve.",
            "technical": "Registramos o problema técnico. Um especialista analisará e entrará em contato.",
            "general": "Obrigado por entrar em contato. Sua mensagem foi registrada."
        }

        return {
            "text": templates.get(category, templates["general"]),
            "confidence": 0.3,  # Low confidence for templates
            "fallback": True
        }
```

---

## ⚙️ Configuration

### Default Configuration

```python
# src/utils/circuit_breaker.py
config = CircuitBreakerConfig(
    name="openai_api",
    failure_threshold=5,      # Open after 5 failures
    failure_timeout=60,       # Reset failures after 60s
    recovery_timeout=30,      # Test recovery after 30s
    success_threshold=2       # Close after 2 successes
)
```

### Custom Configuration

```python
from src.utils.circuit_breaker import OpenAICircuitBreaker, CircuitBreakerConfig

# Create custom circuit breaker
custom_cb = OpenAICircuitBreaker(
    config=CircuitBreakerConfig(
        name="openai_embeddings",
        failure_threshold=10,     # More lenient for embeddings
        failure_timeout=120,
        recovery_timeout=60,
        success_threshold=3
    )
)

# Use custom circuit breaker
result = await custom_cb.call(
    func=openai_client.embeddings.create,
    fallback=cached_embeddings_fallback,
    model="text-embedding-3-small",
    input="text to embed"
)
```

---

## 📊 Monitoring

### Get Circuit State

```python
circuit_breaker = get_openai_circuit_breaker()

# Check current state
state = circuit_breaker.get_state()
print(f"Circuit state: {state.value}")  # closed | open | half_open
```

### Get Metrics

```python
metrics = circuit_breaker.get_metrics()

print(f"Total calls: {metrics.total_calls}")
print(f"Successful: {metrics.successful_calls}")
print(f"Failed: {metrics.failed_calls}")
print(f"Rejected (circuit open): {metrics.rejected_calls}")
print(f"Fallback used: {metrics.fallback_calls}")
print(f"State changes: {metrics.state_changes}")
```

### Sentry Integration

O circuit breaker automaticamente envia eventos para Sentry:

**Eventos capturados:**
- Circuit opened (warning)
- Circuit closed/recovered (info)
- Individual failures (warning)
- Fallback usage (breadcrumb)

**Tags:**
- `component`: circuit_breaker
- `state`: closed/open/half_open
- `failure_count`: N

**Example Sentry query:**
```
component:circuit_breaker state:open
```

### Health Check Integration

```python
# src/api/health_routes.py
from src.utils.circuit_breaker import get_openai_circuit_breaker

async def _check_openai() -> ComponentHealth:
    circuit_breaker = get_openai_circuit_breaker()
    state = circuit_breaker.get_state()

    if state == CircuitState.OPEN:
        return ComponentHealth(
            status="down",
            message=f"Circuit breaker is OPEN (too many failures)"
        )
    elif state == CircuitState.HALF_OPEN:
        return ComponentHealth(
            status="degraded",
            message="Circuit breaker testing recovery"
        )
    else:
        return ComponentHealth(status="up")
```

---

## 🐛 Troubleshooting

### Circuit keeps opening

**Causa:** OpenAI API está falhando frequentemente

**Debug:**
```python
# Ver métricas
metrics = circuit_breaker.get_metrics()
print(f"Failed calls: {metrics.failed_calls}")
print(f"Last failure: {metrics.last_failure_time}")

# Ver estado
print(f"State: {circuit_breaker.get_state()}")
print(f"Failures: {circuit_breaker.failure_count}/{circuit_breaker.config.failure_threshold}")
```

**Soluções:**
1. **API key inválida:** Verificar `OPENAI_API_KEY` em `.env`
2. **Rate limit:** OpenAI tem rate limits (TPM, RPM)
3. **Network issues:** Verificar conectividade
4. **Timeout muito curto:** Aumentar timeout (padrão: 30s)

### Fallback não funciona

**Causa:** Fallback function não está implementada ou falha

**Verificar:**
```python
# Testar fallback isoladamente
result = await rule_based_triage(ticket_id, context)
print(result)  # Deve funcionar sem erros
```

**Solução:**
- Implementar fallback robusto (sem dependências externas)
- Fallback deve ter mesma assinatura que função principal
- Fallback deve SEMPRE retornar valor (não pode falhar)

### Reset manual

```python
# Reset circuit breaker manualmente
circuit_breaker = get_openai_circuit_breaker()
circuit_breaker.reset()
print("Circuit breaker reset to CLOSED state")
```

---

## 📈 Best Practices

### 1. Sempre fornecer fallback

```python
# ❌ Ruim - sem fallback
await circuit_breaker.call(func=openai_call)

# ✅ Bom - com fallback
await circuit_breaker.call(
    func=openai_call,
    fallback=rule_based_logic
)
```

### 2. Fallback deve ser rápido e confiável

```python
# ✅ Bom fallback - apenas lógica local
async def rule_based_fallback(context):
    # Keyword matching (rápido, sempre funciona)
    if "refund" in context["message"]:
        return {"category": "billing"}
    return {"category": "general"}

# ❌ Ruim fallback - depende de serviço externo
async def bad_fallback(context):
    # Chama outra API (pode falhar também!)
    return await another_api.call()
```

### 3. Monitor estado do circuit

```python
# Adicionar ao health check
@router.get("/api/health/detailed")
async def health_check():
    circuit_breaker = get_openai_circuit_breaker()
    state = circuit_breaker.get_state()

    return {
        "openai_circuit_breaker": {
            "state": state.value,
            "metrics": circuit_breaker.get_metrics()
        }
    }
```

### 4. Ajustar thresholds por ambiente

```python
# Development - mais leniente
if environment == "development":
    config = CircuitBreakerConfig(
        failure_threshold=10,  # Permite mais falhas
        recovery_timeout=60
    )
# Production - mais rigoroso
else:
    config = CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30
    )
```

### 5. Log quando usar fallback

```python
@with_circuit_breaker(fallback=rule_based_logic)
async def ai_function(context):
    result = await openai_call()
    logger.info("Using AI response")
    return result

async def rule_based_logic(context):
    result = calculate_locally()
    logger.warning("Using fallback (AI unavailable)")
    # Notificar ops team
    return result
```

---

## 💡 Advanced Usage

### Multiple Circuit Breakers

```python
# Different circuit breakers for different OpenAI services
completion_cb = OpenAICircuitBreaker(
    config=CircuitBreakerConfig(name="openai_completion")
)

embedding_cb = OpenAICircuitBreaker(
    config=CircuitBreakerConfig(name="openai_embedding")
)

# Use specific circuit breakers
completion = await completion_cb.call(
    func=openai_client.chat.completions.create,
    fallback=rule_based_response,
    ...
)

embedding = await embedding_cb.call(
    func=openai_client.embeddings.create,
    fallback=cached_embedding,
    ...
)
```

### Custom Failure Detection

```python
# Extend circuit breaker for custom logic
class CustomCircuitBreaker(OpenAICircuitBreaker):
    def _on_failure(self, error: Exception):
        # Ignore rate limit errors (don't count as failure)
        if "rate_limit" in str(error).lower():
            logger.warning("Rate limit hit, not counting as failure")
            return

        # Count other errors normally
        super()._on_failure(error)
```

---

## 📚 References

- [Circuit Breaker Pattern (Martin Fowler)](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Release It! - Design for Failure](https://pragprog.com/titles/mnee2/release-it-second-edition/)
- [OpenAI Rate Limits](https://platform.openai.com/docs/guides/rate-limits)

---

**Última atualização:** 2026-01-23
**Versão:** 1.0.0
**Autor:** Agent Claude - Backend/Infra Team
