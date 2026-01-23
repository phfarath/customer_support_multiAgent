# Tests Module - Suite de Testes E2E

> **Localização:** `tests/`
> **Propósito:** Testes end-to-end para validar funcionalidade completa do sistema

---

## 📖 Visão Geral

Este módulo contém uma **suite de testes E2E (End-to-End)** que valida o comportamento completo do sistema multi-agente, desde a ingestão de mensagens até a resposta final ao cliente.

### Filosofia de Testes

🎯 **E2E First** - Testes focam em cenários reais de uso
🔄 **Full Pipeline** - Cada teste executa o pipeline completo (4 agentes)
🗄️ **Real Database** - Usa MongoDB de teste (não mocks)
📊 **Scenario-Based** - Organizado por cenários de negócio

---

## 📁 Estrutura de Arquivos

```
tests/
├── scenarios/              # Cenários de teste E2E
│   ├── __init__.py
│   ├── test_routing.py     # Testes de roteamento
│   ├── test_sales.py       # Testes de vendas
│   ├── test_rag.py         # Testes de RAG/knowledge base
│   └── test_escalation.py  # Testes de escalação
│
├── seeds/                  # Database seeding
│   ├── seed_companies.py   # Seed de company_configs
│   └── reset_db.py         # Limpeza de DB de teste
│
└── run_suite.py           # Runner de toda a suite
```

---

## 🚀 Como Executar

### Executar Toda a Suite

```bash
# Opção 1: Via pytest (recomendado)
pytest tests/ -v

# Opção 2: Via runner customizado
python tests/run_suite.py

# Com coverage
pytest --cov=src tests/

# Relatório HTML de coverage
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

### Executar Cenário Específico

```bash
# Apenas testes de routing
pytest tests/scenarios/test_routing.py -v

# Apenas testes de RAG
pytest tests/scenarios/test_rag.py -v

# Teste específico
pytest tests/scenarios/test_routing.py::test_route_billing_to_billing_team -v
```

### Executar com Diferentes Níveis de Output

```bash
# Output mínimo
pytest tests/ -q

# Output detalhado
pytest tests/ -vv

# Com print statements
pytest tests/ -s

# Com logs
pytest tests/ -v --log-cli-level=INFO
```

---

## 🧪 Cenários de Teste

### 1. test_routing.py - Roteamento Correto

**Objetivo:** Validar que `RouterAgent` roteia tickets para a equipe correta

**Cenários:**

#### TC01: Billing → Billing Team
```python
@pytest.mark.asyncio
async def test_route_billing_to_billing_team():
    """
    GIVEN um ticket sobre cobrança duplicada
    WHEN o pipeline é executado
    THEN deve rotear para equipe de billing
    """
    # Arrange
    ticket = create_ticket(
        subject="Cobrança duplicada",
        message="Fui cobrado duas vezes este mês!"
    )

    # Act
    result = await run_pipeline(ticket["ticket_id"])

    # Assert
    assert result["routing"]["current_team"] == "billing"
    assert result["triage"]["category"] == "billing"
```

#### TC02: Technical → Tech Team
```python
@pytest.mark.asyncio
async def test_route_technical_to_tech_team():
    """
    GIVEN um ticket sobre bug/erro técnico
    WHEN o pipeline é executado
    THEN deve rotear para equipe tech
    """
    ticket = create_ticket(
        subject="App crashando",
        message="O app fecha sozinho quando clico em configurações"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["routing"]["current_team"] == "tech"
    assert result["triage"]["category"] == "technical"
    assert result["triage"]["priority"] in ["medium", "high"]
```

#### TC03: Sales → Sales Team
```python
@pytest.mark.asyncio
async def test_route_sales_to_sales_team():
    """
    GIVEN um ticket sobre compra de produto
    WHEN o pipeline é executado
    THEN deve rotear para equipe de sales
    """
    ticket = create_ticket(
        subject="Dúvida sobre plano premium",
        message="Gostaria de saber mais sobre o plano premium"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["routing"]["current_team"] == "sales"
    assert result["triage"]["category"] == "sales"
```

#### TC04: General → General Team
```python
@pytest.mark.asyncio
async def test_route_general_to_general_team():
    """
    GIVEN um ticket genérico
    WHEN o pipeline é executado
    THEN deve rotear para equipe general
    """
    ticket = create_ticket(
        subject="Informação geral",
        message="Quais são seus horários de atendimento?"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["routing"]["current_team"] == "general"
    assert result["triage"]["priority"] == "low"
```

**Total:** 4 testes

---

### 2. test_sales.py - Fluxo de Vendas

**Objetivo:** Validar que pipeline trata corretamente queries de vendas

**Cenários:**

#### TC05: Product Information Request
```python
@pytest.mark.asyncio
async def test_product_information_response():
    """
    GIVEN um ticket pedindo info sobre produtos
    WHEN o pipeline é executado
    THEN deve gerar resposta com informações dos produtos
    """
    ticket = create_ticket(
        subject="Produtos disponíveis",
        message="Quais produtos vocês oferecem?"
    )

    result = await run_pipeline(ticket["ticket_id"])

    # Assertions
    assert result["routing"]["current_team"] == "sales"
    assert "response" in result["resolver"]
    assert result["escalator"]["should_escalate"] is False

    # Response deve mencionar produtos
    response = result["resolver"]["response"]
    assert "produto" in response.lower() or "plano" in response.lower()
```

#### TC06: Pricing Question
```python
@pytest.mark.asyncio
async def test_pricing_question():
    """
    GIVEN um ticket sobre preços
    WHEN o pipeline é executado
    THEN deve responder com informações de pricing
    """
    ticket = create_ticket(
        subject="Quanto custa?",
        message="Qual o preço do plano básico?"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["routing"]["current_team"] == "sales"
    assert result["resolver"]["confidence"] > 0.6
    assert "preço" in result["resolver"]["response"].lower() or \
           "r$" in result["resolver"]["response"].lower()
```

#### TC07: Upsell Opportunity
```python
@pytest.mark.asyncio
async def test_upsell_opportunity():
    """
    GIVEN um ticket de cliente interessado em upgrade
    WHEN o pipeline é executado
    THEN deve gerar resposta incentivando upgrade
    """
    ticket = create_ticket(
        subject="Upgrade para premium",
        message="Estou pensando em fazer upgrade para o premium"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["routing"]["current_team"] == "sales"
    assert result["triage"]["sentiment"] in ["positive", "neutral"]
    assert "premium" in result["resolver"]["response"].lower()
```

**Total:** 3 testes

---

### 3. test_rag.py - RAG/Knowledge Base

**Objetivo:** Validar integração com ChromaDB e uso de knowledge base

**Cenários:**

#### TC08: KB Hit - Resposta Baseada em Docs
```python
@pytest.mark.asyncio
async def test_rag_uses_knowledge_base():
    """
    GIVEN um knowledge base com docs sobre refund
    AND um ticket perguntando sobre refund
    WHEN o pipeline é executado
    THEN deve usar knowledge base na resposta
    """
    # Setup: ingerir doc no KB
    kb = KnowledgeBase()
    await kb.add_documents(
        company_id="test_company",
        documents=[{
            "content": "Nossa política de reembolso: 7 dias para cancelamento com reembolso total.",
            "metadata": {"source": "policies.pdf"}
        }]
    )

    # Create ticket
    ticket = create_ticket(
        subject="Como funciona o refund?",
        message="Quero saber sobre a política de reembolso"
    )

    # Execute pipeline
    result = await run_pipeline(ticket["ticket_id"])

    # Assertions
    assert result["resolver"]["knowledge_base_used"] is True
    assert result["resolver"]["confidence"] > 0.7
    assert "7 dias" in result["resolver"]["response"]

    # Cleanup
    await kb.delete_collection("test_company")
```

#### TC09: KB Miss - Fallback Response
```python
@pytest.mark.asyncio
async def test_rag_fallback_when_no_kb_results():
    """
    GIVEN um knowledge base vazio
    AND um ticket com pergunta específica
    WHEN o pipeline é executado
    THEN deve gerar resposta genérica com low confidence
    """
    ticket = create_ticket(
        subject="Pergunta muito específica",
        message="Como faço para integrar com a API do sistema XYZ?"
    )

    result = await run_pipeline(ticket["ticket_id"])

    # Sem KB results, confidence deve ser menor
    assert result["resolver"]["knowledge_base_used"] is False
    assert result["resolver"]["confidence"] < 0.7
```

#### TC10: RAG com Múltiplos Docs
```python
@pytest.mark.asyncio
async def test_rag_with_multiple_documents():
    """
    GIVEN múltiplos docs no knowledge base
    WHEN faz query
    THEN deve retornar top-3 mais relevantes
    """
    kb = KnowledgeBase()

    # Seed multiple docs
    docs = [
        {"content": "Política de refund: 7 dias", "metadata": {"source": "policy1"}},
        {"content": "Processo de refund: envie email", "metadata": {"source": "policy2"}},
        {"content": "Refund parcial após 14 dias", "metadata": {"source": "policy3"}},
        {"content": "Produto A custa R$99", "metadata": {"source": "products"}}  # Não relevante
    ]
    await kb.add_documents("test_company", docs)

    # Search
    results = await kb.search("como pedir refund?", "test_company", n_results=3)

    # Assertions
    assert len(results) == 3
    # Top 3 devem ser sobre refund
    for result in results:
        assert "refund" in result["content"].lower()

    await kb.delete_collection("test_company")
```

**Total:** 3 testes

---

### 4. test_escalation.py - Escalação para Humanos

**Objetivo:** Validar lógica de escalação do `EscalatorAgent`

**Cenários:**

#### TC11: Escalate - Low Confidence
```python
@pytest.mark.asyncio
async def test_escalate_on_low_confidence():
    """
    GIVEN um ticket que gera resposta com baixa confidence (<0.6)
    WHEN o pipeline é executado
    THEN deve escalar para humano
    """
    # Ticket complexo que IA não consegue responder bem
    ticket = create_ticket(
        subject="Problema complexo",
        message="Preciso de ajuda com um caso muito específico que envolve..."
    )

    result = await run_pipeline(ticket["ticket_id"])

    # Se confidence < 0.6, deve escalar
    if result["resolver"]["confidence"] < 0.6:
        assert result["escalator"]["should_escalate"] is True
        assert "confidence" in result["escalator"]["escalation_reason"].lower()
```

#### TC12: Escalate - SLA Breach
```python
@pytest.mark.asyncio
async def test_escalate_on_sla_breach():
    """
    GIVEN um ticket criado há mais de 4 horas
    WHEN o pipeline é executado
    THEN deve escalar por SLA breach
    """
    # Create old ticket (simulate)
    ticket = create_ticket(
        subject="Ticket antigo",
        message="Preciso de ajuda",
        created_at=datetime.now() - timedelta(hours=5)
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["escalator"]["should_escalate"] is True
    assert "sla" in result["escalator"]["escalation_reason"].lower()
```

#### TC13: Escalate - Negative Sentiment
```python
@pytest.mark.asyncio
async def test_escalate_on_very_negative_sentiment():
    """
    GIVEN um ticket com sentimento muito negativo
    WHEN o pipeline é executado
    THEN deve escalar para humano
    """
    ticket = create_ticket(
        subject="MUITO INSATISFEITO",
        message="Estou extremamente frustrado! Isso é inaceitável!"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["triage"]["sentiment"] == "negative"

    # Sentimento muito negativo deve disparar escalação
    if result["escalator"]["should_escalate"]:
        assert "sentiment" in result["escalator"]["escalation_reason"].lower()
```

#### TC14: No Escalation - Normal Flow
```python
@pytest.mark.asyncio
async def test_no_escalation_on_normal_flow():
    """
    GIVEN um ticket normal que IA consegue resolver
    WHEN o pipeline é executado
    THEN NÃO deve escalar
    """
    ticket = create_ticket(
        subject="Dúvida simples",
        message="Qual o horário de atendimento?"
    )

    result = await run_pipeline(ticket["ticket_id"])

    assert result["escalator"]["should_escalate"] is False
    assert result["resolver"]["confidence"] > 0.6
    assert "response" in result["resolver"]
```

#### TC15: Email Sent on Escalation
```python
@pytest.mark.asyncio
async def test_email_sent_when_escalated():
    """
    GIVEN um ticket que deve ser escalado
    WHEN o pipeline é executado
    THEN deve enviar email de notificação
    """
    # Mock email sender
    with patch("src.utils.email_sender.send_escalation_email") as mock_email:
        ticket = create_ticket(
            subject="URGENTE: Problema crítico",
            message="Sistema completamente fora do ar!",
            priority="critical"
        )

        # Force multiple interactions (trigger escalation)
        for i in range(6):
            await save_interaction(ticket["ticket_id"], "customer", f"Mensagem {i}")

        result = await run_pipeline(ticket["ticket_id"])

        # Should escalate
        assert result["escalator"]["should_escalate"] is True

        # Email should be called
        mock_email.assert_called_once()
```

**Total:** 5 testes

---

## 🗃️ Database Seeding

### seed_companies.py

Cria company configs de teste com dados realistas:

```python
# tests/seeds/seed_companies.py

async def seed_test_companies():
    """Seed database com empresas de teste"""
    companies_collection = get_collection(COLLECTION_COMPANY_CONFIGS)

    test_companies = [
        {
            "company_id": "test_company_1",
            "company_name": "Test Company A",
            "bot_name": "Assistant A",
            "welcome_message": "Olá! Como posso ajudar?",
            "teams": [
                {"name": "billing", "description": "Payment issues"},
                {"name": "tech", "description": "Technical support"},
                {"name": "sales", "description": "Sales team"},
                {"name": "general", "description": "General inquiries"}
            ],
            "policies": {
                "refund_policy": "Reembolso em até 7 dias úteis",
                "cancellation_policy": "Cancelamento sem taxa"
            },
            "products": [
                {
                    "name": "Plano Básico",
                    "price": 29.90,
                    "description": "Recursos básicos"
                },
                {
                    "name": "Plano Premium",
                    "price": 99.90,
                    "description": "Todos os recursos + suporte 24/7"
                }
            ],
            "escalation_config": {
                "email_recipients": ["test@test.com"],
                "max_interactions": 5,
                "min_confidence": 0.6,
                "sentiment_threshold": -0.7,
                "sla_hours": 4
            }
        }
    ]

    for company in test_companies:
        await companies_collection.update_one(
            {"company_id": company["company_id"]},
            {"$set": company},
            upsert=True
        )

    print(f"Seeded {len(test_companies)} test companies")
```

### reset_db.py

Limpa database de teste:

```python
# tests/seeds/reset_db.py

async def reset_test_database():
    """Limpa todas as collections de teste"""
    collections_to_clear = [
        COLLECTION_TICKETS,
        COLLECTION_INTERACTIONS,
        COLLECTION_CUSTOMERS,
        COLLECTION_BOT_SESSIONS,
        COLLECTION_AGENT_STATES,
        COLLECTION_ROUTING_DECISIONS,
        COLLECTION_AUDIT_LOGS
    ]

    for collection_name in collections_to_clear:
        collection = get_collection(collection_name)
        await collection.delete_many({"company_id": {"$regex": "^test_"}})

    print("Test database reset complete")
```

---

## 🔧 Test Helpers e Fixtures

### Fixtures Comuns

```python
# tests/conftest.py

import pytest
from src.database.connection import get_mongo_client

@pytest.fixture(scope="session")
async def setup_test_db():
    """Setup database de teste antes de todos os testes"""
    await seed_test_companies()
    yield
    await reset_test_database()

@pytest.fixture
async def clean_db():
    """Limpa DB antes de cada teste"""
    await reset_test_database()
    yield
    # Cleanup após teste

@pytest.fixture
def test_company_id():
    """Retorna company_id de teste"""
    return "test_company_1"

@pytest.fixture
async def knowledge_base():
    """Retorna KnowledgeBase instance"""
    from src.rag.knowledge_base import KnowledgeBase
    kb = KnowledgeBase()
    yield kb
    # Cleanup
    await kb.delete_collection("test_company_1")
```

### Helper Functions

```python
# tests/scenarios/helpers.py

async def create_ticket(subject: str, message: str, **kwargs) -> Dict:
    """Cria ticket de teste"""
    from src.database.operations import find_or_create_ticket

    ticket = await find_or_create_ticket(
        customer_phone="+5511999999999",
        channel="telegram",
        message=message,
        company_id=kwargs.get("company_id", "test_company_1"),
        subject=subject,
        **kwargs
    )
    return ticket

async def run_pipeline(ticket_id: str) -> Dict:
    """Executa pipeline completo e retorna resultados"""
    from src.utils.pipeline import AgentPipeline

    pipeline = AgentPipeline(company_id="test_company_1")
    result = await pipeline.run_pipeline(ticket_id)
    return result

async def assert_ticket_escalated(ticket_id: str):
    """Assert que ticket foi escalado"""
    ticket = await get_ticket(ticket_id)
    assert ticket["escalated"] is True
    assert ticket.get("escalation_reason") is not None
```

---

## 📊 Coverage Report

### Gerar Coverage

```bash
# Executar com coverage
pytest --cov=src tests/

# Gerar HTML report
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html
```

### Target de Coverage

| Módulo | Target | Atual |
|--------|--------|-------|
| `src/agents/` | 85% | ~80% |
| `src/utils/` | 90% | ~85% |
| `src/rag/` | 80% | ~75% |
| `src/database/` | 85% | ~80% |
| **Overall** | **85%** | **~80%** |

---

## 🎯 Test Strategy

### Pirâmide de Testes

```
         /\
        /  \  E2E Tests (Scenarios) - 15 tests
       /────\
      /      \  Integration Tests - TODO
     /────────\
    /          \  Unit Tests - TODO
   /────────────\
```

**Atualmente:** Focado em E2E tests
**Futuro:** Adicionar unit tests para funções isoladas

### O Que Testar

✅ **SIM - Testar:**
- Fluxos completos de uso (E2E)
- Lógica de negócio (roteamento, escalação)
- Integração com serviços externos (OpenAI, MongoDB)
- Edge cases (SLA breach, low confidence, etc)

❌ **NÃO - Testar:**
- Implementação interna de libs (OpenAI, ChromaDB)
- Configurações triviais
- Getters/setters simples

---

## 🔍 Debugging Testes

### Ver Logs Durante Testes

```bash
# Mostrar logs
pytest tests/ -v --log-cli-level=DEBUG

# Com print statements
pytest tests/ -s
```

### Parar no Primeiro Erro

```bash
pytest tests/ -x
```

### Rodar Teste Específico em Loop

```bash
# Útil para debugar flaky tests
pytest tests/scenarios/test_routing.py::test_route_billing -v --count=10
```

### Usar Debugger

```python
# Em qualquer teste, adicionar:
import pdb; pdb.set_trace()

# Ou usar pytest --pdb
pytest tests/ --pdb  # Para no primeiro erro
```

---

## 🚀 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/tests.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mongodb:
        image: mongo:latest
        ports:
          - 27017:27017

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.10

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        env:
          MONGODB_URI: mongodb://localhost:27017
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/ -v --cov=src

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

---

## 📝 Escrevendo Novos Testes

### Template de Teste E2E

```python
import pytest
from tests.scenarios.helpers import create_ticket, run_pipeline

@pytest.mark.asyncio
async def test_new_scenario():
    """
    GIVEN [condições iniciais]
    WHEN [ação]
    THEN [resultado esperado]
    """
    # Arrange
    ticket = await create_ticket(
        subject="...",
        message="..."
    )

    # Act
    result = await run_pipeline(ticket["ticket_id"])

    # Assert
    assert result["triage"]["priority"] == "high"
    assert result["routing"]["current_team"] == "billing"
    assert result["escalator"]["should_escalate"] is False
```

### Naming Conventions

```python
# ✅ BOM
def test_escalate_on_low_confidence()
def test_route_billing_to_billing_team()
def test_rag_uses_knowledge_base()

# ❌ RUIM
def test_1()
def test_escalation()
def test_stuff()
```

---

## 🐛 Troubleshooting

### MongoDB Connection Error

**Problema:** Tests falham com erro de conexão

**Solução:**
```bash
# Verificar MongoDB rodando
mongod --version
brew services start mongodb-community

# Ou usar Docker
docker run -d -p 27017:27017 mongo:latest
```

### OpenAI API Rate Limit

**Problema:** Tests falham por rate limit

**Solução:**
```python
# Usar mocks para testes rápidos
from unittest.mock import patch

@patch("src.utils.openai_client.call_openai")
async def test_with_mock(mock_openai):
    mock_openai.return_value = "Mocked response"
    # Test code
```

### Flaky Tests

**Problema:** Teste passa às vezes e falha outras

**Solução:**
1. Verificar race conditions
2. Adicionar waits apropriados
3. Usar fixtures para garantir estado limpo

---

## 📚 Referências

### Internal Docs
- **ARCHITECTURE.md** - Visão geral do sistema
- **AI_INSTRUCTIONS.md** - Como modificar código
- **src/agents/README.md** - Como agentes funcionam

### External Docs
- Pytest: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/

---

## 🎯 Roadmap de Testes

### Curto Prazo
- [ ] Adicionar unit tests para funções isoladas
- [ ] Aumentar coverage para 85%+
- [ ] Adicionar testes de performance

### Médio Prazo
- [ ] Integration tests para cada adapter (Telegram, WhatsApp)
- [ ] Load tests (múltiplos tickets simultâneos)
- [ ] Testes de segurança (SQL injection, XSS)

### Longo Prazo
- [ ] Testes de regressão visual (Streamlit dashboard)
- [ ] Chaos engineering (MongoDB down, OpenAI timeout)
- [ ] Contract tests (API)

---

**Última atualização:** 2026-01-20
**Versão:** 1.0
**Mantenedor:** Aethera Labs Team
