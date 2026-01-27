# Context Persistence

> **Implementado em:** 2026-01-27 19:00
> **Status:** ✅ Production-ready
> **Feature Spec:** [docs/futures/009_v1.0_context_persistence.md](../futures/009_v1.0_context_persistence.md)

---

## Descrição

Implementação de persistência de contexto de conversação que permite ao sistema lembrar do histórico de interações de cada cliente entre diferentes tickets. Quando um cliente abre um novo ticket, o sistema automaticamente recupera resumos de tickets anteriores relevantes e injeta esse contexto no prompt do AI, possibilitando respostas mais personalizadas.

**Funcionalidades:**
- Geração automática de resumos de conversação ao resolver tickets
- Indexação de resumos no ChromaDB com filtro por `customer_id`
- Recuperação de contexto histórico relevante para novos tickets
- Injeção de contexto no prompt do ResolverAgent

---

## Arquivos Modificados/Criados

### Modificados

| Arquivo | Alteração |
|---------|-----------|
| `src/models/customer.py` | Adicionados campos `preferences` (Dict) e `history_summary` (str) |
| `src/rag/knowledge_base.py` | Adicionados métodos `add_ticket_summary()` e `search_customer_context()` |
| `src/agents/resolver_agent.py` | Adicionada lógica de sumarização, indexação e recuperação de contexto |

### Criados

| Arquivo | Descrição |
|---------|-----------|
| `tests/unit/test_context_persistence.py` | Suite de testes unitários para a feature |

---

## Como Usar

### Fluxo Automático

A feature funciona automaticamente. Quando um ticket é resolvido (não escalado), o sistema:

1. Gera um resumo da conversação usando OpenAI
2. Indexa o resumo no ChromaDB com metadados do cliente
3. Na próxima interação do cliente, recupera o contexto relevante

### Acessando Preferências do Cliente

```python
from src.models import Customer

# Customer agora tem campos de contexto
customer = Customer(
    customer_id="C-123",
    phone_number="+5511999999999",
    company_id="comp_001",
    preferences={"language": "pt-BR", "communication_style": "formal"},
    history_summary="Cliente frequente, geralmente pergunta sobre faturamento."
)
```

---

## Exemplos de Código

### Buscar Contexto do Cliente

```python
from src.rag.knowledge_base import knowledge_base

# Buscar resumos de tickets anteriores relevantes
summaries = await knowledge_base.search_customer_context(
    query="problema com cobrança",
    customer_id="C-123",
    company_id="comp_001",
    k=3  # Top 3 resultados
)

# Retorna: ["Resumo do ticket T-001...", "Resumo do ticket T-002..."]
```

### Indexar Resumo de Ticket

```python
from src.rag.knowledge_base import knowledge_base

success = await knowledge_base.add_ticket_summary(
    summary="Cliente solicitou reembolso. Resolvido com crédito na conta.",
    ticket_id="T-456",
    customer_id="C-123",
    company_id="comp_001"
)
```

---

## Testes Realizados

### Testes Unitários (7 testes)

```bash
python3 -m pytest tests/unit/test_context_persistence.py -v
```

| Teste | Resultado |
|-------|-----------|
| `test_add_ticket_summary_success` | ✅ PASSED |
| `test_add_ticket_summary_failure` | ✅ PASSED |
| `test_search_customer_context_returns_summaries` | ✅ PASSED |
| `test_search_customer_context_empty_results` | ✅ PASSED |
| `test_generate_conversation_summary_success` | ✅ PASSED |
| `test_generate_conversation_summary_failure` | ✅ PASSED |
| `test_index_ticket_summary_calls_knowledge_base` | ✅ PASSED |

---

## Troubleshooting

### Resumos não estão sendo indexados

**Causa:** O ticket foi escalado em vez de resolvido.

**Solução:** Resumos só são gerados quando `needs_escalation=False`. Verifique o resultado do EscalatorAgent.

### Contexto do cliente não aparece nas respostas

**Causa:** Pode não haver histórico anterior ou o `customer_id` está incorreto.

**Verificação:**
```python
# Verificar se há resumos indexados
results = await knowledge_base.search_customer_context(
    query="qualquer coisa",
    customer_id="C-123",
    company_id="comp_001"
)
print(f"Resumos encontrados: {len(results)}")
```

### Erro de ChromaDB

**Causa:** O diretório `chroma_db` pode estar corrompido.

**Solução:** Apagar o diretório e deixar o sistema recriar:
```bash
rm -rf chroma_db/
```

---

## Referências

- [Feature Spec: Context Persistence](../futures/009_v1.0_context_persistence.md)
- [Knowledge Base RAG](../../src/rag/knowledge_base.py)
- [Resolver Agent](../../src/agents/resolver_agent.py)
- [Customer Model](../../src/models/customer.py)

---

## Impacto em Custos

> ⚠️ **Atenção:** Esta feature adiciona uma chamada extra ao OpenAI para cada ticket resolvido (geração de resumo). Considere isso no planejamento de custos.

| Operação | Custo Estimado |
|----------|----------------|
| Geração de resumo | ~200 tokens por ticket |
| Recuperação de contexto | Sem custo (ChromaDB local) |

---

**Implementado por:** Gemini 3 Pro High (Antigravity)
**Versão:** 1.0
