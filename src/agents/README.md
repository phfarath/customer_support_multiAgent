# Agents Module - Agentes de IA

> **Localização:** `src/agents/`
> **Propósito:** Implementação dos 4 agentes especializados que processam tickets de suporte

---

## 📖 Visão Geral

Este módulo contém a implementação do **sistema multi-agente** que processa tickets de suporte ao cliente. Cada agente tem uma responsabilidade única e trabalha em **pipeline sequencial**.

### Pipeline de Execução

```
Mensagem do Cliente
    ↓
[1] TriageAgent → Priority, Category, Sentiment
    ↓
[2] RouterAgent → Team Assignment
    ↓
[3] ResolverAgent → Response Generation (com RAG)
    ↓
[4] EscalatorAgent → Escalation Decision
    ↓
Resposta ao Cliente OU Escalação para Humano
```

---

## 📁 Estrutura de Arquivos

```
src/agents/
├── __init__.py              # Package exports
├── base_agent.py            # ⭐ BaseAgent abstrato (interface comum)
├── triage_agent.py          # [1] Classificação de tickets
├── router_agent.py          # [2] Roteamento para equipes
├── resolver_agent.py        # [3] Geração de respostas
└── escalator_agent.py       # [4] Decisão de escalação
```

---

## 🏗️ Arquitetura

### BaseAgent (Classe Abstrata)

Todos os agentes herdam de `BaseAgent` e implementam a interface comum:

```python
from src.agents.base_agent import BaseAgent, AgentResult

class MyAgent(BaseAgent):
    def __init__(self, company_id: str):
        super().__init__(agent_name="MyAgent", company_id=company_id)

    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session=None
    ) -> AgentResult:
        """Implementação específica do agente"""
        pass
```

### Contrato da Interface

**Método obrigatório:** `execute(ticket_id, context, session) -> AgentResult`

**Context recebido:**
```python
context = {
    "ticket": {...},              # Dados do ticket
    "interactions": [...],        # Histórico de mensagens
    "customer_history": [...],    # Histórico do cliente
    "company_config": {...},      # Configurações da empresa
    "previous_agent_results": {}  # Resultados de agentes anteriores
}
```

**AgentResult retornado:**
```python
AgentResult(
    success: bool,           # Se a execução foi bem-sucedida
    data: Dict[str, Any],   # Dados produzidos pelo agente
    next_action: str,       # "continue" ou "stop"
    error: Optional[str]    # Mensagem de erro (se houver)
)
```

### Métodos Herdados de BaseAgent

| Método | Propósito |
|--------|-----------|
| `save_state(ticket_id, state, session)` | Salva estado em `agent_states` collection |
| `log_action(ticket_id, action, details, session)` | Registra ação em `audit_logs` |
| `get_openai_client()` | Retorna cliente OpenAI configurado |
| `call_openai(prompt, system_msg)` | Wrapper para chamadas OpenAI com retry |

---

## 1️⃣ TriageAgent

**Arquivo:** `triage_agent.py`

### Responsabilidade
Analisa e classifica o ticket inicial em prioridade, categoria e sentimento.

### Input
- Ticket com `subject` e `description`
- Primeira mensagem do cliente

### Output
```python
{
    "priority": "low" | "medium" | "high" | "critical",
    "category": "billing" | "technical" | "sales" | "general",
    "sentiment": "positive" | "neutral" | "negative"
}
```

### Lógica de Classificação

#### Prioridade
- **Critical:** Palavras-chave urgentes (urgent, critical, down, broken) + contexto
- **High:** Problema que afeta operação
- **Medium:** Solicitação importante mas não urgente
- **Low:** Dúvidas gerais, informações

#### Categoria
- **Billing:** Pagamento, cobrança, refund, fatura
- **Technical:** Bugs, erros, não funciona, crash
- **Sales:** Compra, produto, preço, plano
- **General:** Outros

#### Sentiment
- **Positive:** Cliente satisfeito, agradecimento
- **Neutral:** Neutro, apenas informação
- **Negative:** Frustração, raiva, insatisfação

### Estratégia de Fallback
Se OpenAI falhar, usa análise baseada em **keywords**:
```python
# Exemplo de fallback
if "refund" in message.lower() or "cobrança" in message.lower():
    category = "billing"
    priority = "high"
```

### Exemplo de Uso
```python
from src.agents.triage_agent import TriageAgent

triage = TriageAgent(company_id="comp_123")
result = await triage.execute(
    ticket_id="TICKET-001",
    context={
        "ticket": {
            "subject": "Problema com cobrança duplicada",
            "description": "Fui cobrado duas vezes este mês!"
        }
    }
)

print(result.data)
# Output: {
#   "priority": "high",
#   "category": "billing",
#   "sentiment": "negative"
# }
```

---

## 2️⃣ RouterAgent

**Arquivo:** `router_agent.py`

### Responsabilidade
Roteia o ticket para a equipe apropriada baseado na categoria e configuração da empresa.

### Input
- Ticket classificado (com `category` do TriageAgent)
- `company_config.teams` (lista de equipes disponíveis)

### Output
```python
{
    "current_team": "billing" | "tech" | "sales" | "general",
    "routing_reason": "Ticket categorized as billing issue"
}
```

### Lógica de Roteamento

1. **Lê equipes da empresa:**
   ```python
   teams = context["company_config"]["teams"]
   # [
   #   {"name": "billing", "description": "Handles payment issues"},
   #   {"name": "tech", "description": "Technical support"},
   #   ...
   # ]
   ```

2. **Mapeia categoria → equipe:**
   - `billing` → equipe "billing"
   - `technical` → equipe "tech"
   - `sales` → equipe "sales"
   - `general` → equipe "general"

3. **Valida equipe existe:**
   Se a equipe não existe na configuração da empresa, usa "general" como fallback.

4. **Salva decisão:**
   Registra em `routing_decisions` collection para auditoria.

### Exemplo de Uso
```python
from src.agents.router_agent import RouterAgent

router = RouterAgent(company_id="comp_123")
result = await router.execute(
    ticket_id="TICKET-001",
    context={
        "ticket": {"category": "billing"},
        "company_config": {
            "teams": [
                {"name": "billing", "description": "Payment team"},
                {"name": "tech", "description": "Tech support"}
            ]
        }
    }
)

print(result.data)
# Output: {
#   "current_team": "billing",
#   "routing_reason": "Ticket categorized as billing issue"
# }
```

---

## 3️⃣ ResolverAgent

**Arquivo:** `resolver_agent.py`

### Responsabilidade
Gera resposta natural para o cliente usando **RAG (Retrieval Augmented Generation)** e políticas da empresa.

### Input
- Ticket completo
- Histórico de interações
- `company_config` (policies, products, custom_instructions)
- RAG knowledge base

### Output
```python
{
    "response": "Texto da resposta para o cliente",
    "confidence": 0.85,  # 0.0 - 1.0
    "knowledge_base_used": true,
    "sources": ["KB_DOC_123", "KB_DOC_456"]
}
```

### Fluxo de Geração

```
1. Busca no Knowledge Base (RAG)
   ↓
2. Monta contexto enriquecido
   ↓
3. Chama OpenAI com prompt estruturado
   ↓
4. Valida resposta
   ↓
5. Retorna resposta + confidence
```

### RAG Integration

```python
# 1. Query ChromaDB
kb_results = await knowledge_base.search(
    query=customer_message,
    company_id=company_id,
    n_results=3
)

# 2. Adiciona ao contexto do prompt
context_with_kb = {
    "customer_message": customer_message,
    "knowledge_base": kb_results,
    "policies": company_config["policies"],
    "products": company_config["products"]
}
```

### Prompt Template

```
Você é um assistente de suporte ao cliente da {company_name}.

INSTRUÇÕES:
- Seja natural e empático, não robótico
- Use as informações do knowledge base fornecido
- Siga as políticas da empresa
- Se não souber a resposta, seja honesto

KNOWLEDGE BASE:
{kb_results}

POLÍTICAS DA EMPRESA:
{policies}

PRODUTOS:
{products}

MENSAGEM DO CLIENTE:
{customer_message}

HISTÓRICO:
{previous_interactions}

Responda de forma clara e útil.
```

### Confidence Score

O agente retorna um score de confiança baseado em:
- KB results found? +0.3
- Clear answer in prompt? +0.4
- Previous context available? +0.2
- OpenAI response quality? +0.1

Se `confidence < 0.6`, pode disparar escalação (via EscalatorAgent).

### Exemplo de Uso
```python
from src.agents.resolver_agent import ResolverAgent

resolver = ResolverAgent(company_id="comp_123")
result = await resolver.execute(
    ticket_id="TICKET-001",
    context={
        "ticket": {"subject": "Como funciona o refund?"},
        "interactions": [
            {"sender": "customer", "message": "Quero cancelar e pedir reembolso"}
        ],
        "company_config": {
            "policies": {
                "refund_policy": "Reembolso em até 7 dias úteis"
            }
        }
    }
)

print(result.data["response"])
# Output: "Entendo que você deseja cancelar e solicitar reembolso.
#          Segundo nossa política, processamos reembolsos em até 7 dias úteis..."
```

---

## 4️⃣ EscalatorAgent

**Arquivo:** `escalator_agent.py`

### Responsabilidade
Decide se o ticket deve ser **escalado para um agente humano** ou se a IA pode continuar atendendo.

### Input
- Ticket completo
- Resultados de agentes anteriores (priority, confidence, etc)
- `company_config.escalation_config`

### Output
```python
{
    "should_escalate": true | false,
    "escalation_reason": "Low confidence response (0.45)",
    "email_sent": true,
    "escalation_summary": "Customer asking for refund, automated response confidence low"
}
```

### Critérios de Escalação

#### Rule-based (Regras Obrigatórias)

1. **Alta Prioridade + Muitas Interações:**
   ```python
   if priority == "critical" and interactions_count > max_interactions:
       escalate = True
   ```

2. **Sentimento Muito Negativo:**
   ```python
   if sentiment_score < -0.7:  # Cliente muito insatisfeito
       escalate = True
   ```

3. **Baixa Confiança na Resposta:**
   ```python
   if resolver_confidence < 0.6:
       escalate = True
   ```

4. **SLA Breach (Violação de Tempo):**
   ```python
   if time_since_creation > sla_hours:
       escalate = True
   ```

#### AI-based (Complementar)

OpenAI analisa o contexto completo e pode sugerir escalação mesmo que regras não ativem:
- Cliente pedindo especificamente para falar com humano
- Situação complexa que requer julgamento humano
- Caso edge que IA não consegue resolver

### Configuração de Escalação

Definida em `company_configs.escalation_config`:

```python
escalation_config = {
    "email_recipients": ["suporte@empresa.com", "manager@empresa.com"],
    "max_interactions": 5,
    "min_confidence": 0.6,
    "sentiment_threshold": -0.7,
    "sla_hours": 4
}
```

### Fluxo de Escalação

```
1. Avalia regras obrigatórias
   ↓
2. Se regra ativar: escalate = True
   ↓
3. Se não, consulta OpenAI
   ↓
4. Se escalar:
   - Atualiza ticket.escalated = True
   - Gera summary com OpenAI
   - Envia email (via email_sender.py)
   - Adiciona interação: "Escalado para humano"
   - Retorna should_escalate = True
   ↓
5. Se não escalar: permite resposta automática
```

### Email de Escalação

Quando escalado, envia email automático com:

**Assunto:** `[ESCALADO] Ticket TICKET-123 - {subject}`

**Corpo:**
```
Ticket TICKET-123 foi escalado para atenção humana.

MOTIVO: Low confidence response (0.45)

RESUMO GERADO POR IA:
Cliente solicitando reembolso por cobrança duplicada.
Tentativas automáticas de resolução não tiveram confiança
suficiente. Requer análise manual.

PRIORIDADE: High
CATEGORIA: Billing
INTERAÇÕES: 3
SENTIMENTO: Negative

Link: http://dashboard.com/tickets/TICKET-123
```

### Exemplo de Uso
```python
from src.agents.escalator_agent import EscalatorAgent

escalator = EscalatorAgent(company_id="comp_123")
result = await escalator.execute(
    ticket_id="TICKET-001",
    context={
        "ticket": {
            "priority": "critical",
            "interactions_count": 6,
            "created_at": datetime.now() - timedelta(hours=5)
        },
        "resolver_result": {
            "confidence": 0.45
        },
        "company_config": {
            "escalation_config": {
                "max_interactions": 5,
                "min_confidence": 0.6,
                "sla_hours": 4,
                "email_recipients": ["support@company.com"]
            }
        }
    }
)

print(result.data)
# Output: {
#   "should_escalate": true,
#   "escalation_reason": "SLA breach (5 hours) and low confidence (0.45)",
#   "email_sent": true,
#   "escalation_summary": "..."
# }
```

---

## 🔄 Ciclo de Vida de um Ticket

### Passo a Passo Completo

```python
# 1. Cliente envia mensagem
message = "Fui cobrado em duplicidade!"

# 2. TriageAgent classifica
triage_result = await triage.execute(ticket_id, context)
# → priority: "high", category: "billing", sentiment: "negative"

# 3. RouterAgent roteia
router_result = await router.execute(ticket_id, context)
# → current_team: "billing"

# 4. ResolverAgent gera resposta
resolver_result = await resolver.execute(ticket_id, context)
# → response: "Vou verificar sua cobrança...", confidence: 0.75

# 5. EscalatorAgent decide
escalator_result = await escalator.execute(ticket_id, context)
# → should_escalate: false (confidence ok)

# 6. Resposta enviada ao cliente
send_response(customer, resolver_result["response"])
```

---

## 🧪 Testando Agentes

### Teste Individual

```python
import pytest
from src.agents.triage_agent import TriageAgent

@pytest.mark.asyncio
async def test_triage_billing_urgent():
    agent = TriageAgent(company_id="test_comp")

    context = {
        "ticket": {
            "subject": "URGENTE: Cobrança duplicada",
            "description": "Fui cobrado duas vezes!"
        }
    }

    result = await agent.execute("TEST-001", context)

    assert result.success
    assert result.data["priority"] == "high"
    assert result.data["category"] == "billing"
    assert result.data["sentiment"] == "negative"
```

### Teste de Pipeline Completo

Ver: `tests/scenarios/` para exemplos completos de testes E2E.

---

## 🛠️ Como Modificar/Estender

### Adicionar Novo Agente

1. **Criar arquivo** `src/agents/my_new_agent.py`
2. **Herdar de BaseAgent**
3. **Implementar `execute()`**
4. **Adicionar ao pipeline** em `src/utils/pipeline.py`
5. **Criar testes** em `tests/scenarios/`

### Modificar Lógica Existente

**Exemplo: Melhorar TriageAgent com mais categorias**

```python
# triage_agent.py

# ANTES
categories = ["billing", "technical", "sales", "general"]

# DEPOIS
categories = [
    "billing",
    "technical",
    "sales",
    "general",
    "account",      # NOVO
    "partnership"   # NOVO
]
```

**Importante:** Ao modificar agentes:
- ✅ Preserve fallback logic
- ✅ Mantenha save_state() e log_action()
- ✅ Use transactions (session parameter)
- ✅ Adicione testes para novos casos

---

## 📚 Dependências

### Módulos Internos
- `src.utils.openai_client` - Cliente OpenAI
- `src.database.operations` - DB operations
- `src.rag.knowledge_base` - RAG system (ResolverAgent)
- `src.utils.email_sender` - Email sending (EscalatorAgent)

### Bibliotecas Externas
- `openai` - OpenAI API
- `motor` - MongoDB async
- `tenacity` - Retry logic

---

## 📊 Métricas e Monitoring

### Audit Logs

Todos os agentes salvam ações em `audit_logs`:

```python
{
    "ticket_id": "TICKET-001",
    "agent_name": "TriageAgent",
    "action": "ticket_classified",
    "details": {
        "priority": "high",
        "category": "billing"
    },
    "timestamp": datetime.now()
}
```

### Agent States

Estados salvos em `agent_states`:

```python
{
    "ticket_id": "TICKET-001",
    "agent_name": "ResolverAgent",
    "state": {
        "response": "...",
        "confidence": 0.85,
        "kb_results_count": 3
    },
    "timestamp": datetime.now()
}
```

Útil para debugging e análise de performance dos agentes.

---

## 🐛 Troubleshooting

### Agente não executa

**Problema:** Pipeline para no meio

**Soluções:**
1. Check logs: `logger.error` em cada agente
2. Verify MongoDB connection
3. Check OpenAI API key
4. Validate context structure

### OpenAI timeout

**Problema:** Agente demora muito ou timeout

**Soluções:**
1. Reduce prompt size
2. Increase timeout em `openai_client.py`
3. Use fallback logic

### Escalação não envia email

**Problema:** `should_escalate=True` mas email não chega

**Soluções:**
1. Check SMTP config em `.env`
2. Verify `escalation_config.email_recipients`
3. Check logs em `email_sender.py`

---

## 📖 Referências

- **ARCHITECTURE.md** - Visão geral do projeto
- **AI_INSTRUCTIONS.md** - Guias de modificação
- **src/utils/pipeline.py** - Orquestração dos agentes
- **tests/scenarios/** - Exemplos de testes E2E

---

**Última atualização:** 2026-01-20
**Versão:** 1.0
**Mantenedor:** Aethera Labs Team
