# Automated Ticket Tagging

> **Implementado em:** 2026-01-30 10:00
> **Status:** ✅ Production-ready
> **Versão Target:** V1.1

---

## Descrição

Sistema de tagging automatizado que gera tags granulares para tickets durante a fase de triagem, permitindo classificação mais detalhada além das 3 categorias base (billing, tech, general).

**Problema Resolvido:**
- TriageAgent categorizava apenas em 3 buckets (billing/technical/general)
- Não havia tags granulares para reporting e filtering avançado

**Solução:**
- Tags são geradas automaticamente pelo TriageAgent (AI ou rule-based)
- Máximo de 5 tags por ticket
- Suporte a filtro por tags na API e Dashboard

---

## Arquivos Modificados/Criados

### Models
- `src/models/ticket.py` - Adicionado campo `tags` (List[str]) e `category` (TicketCategory enum)
- `src/models/__init__.py` - Exportado TicketCategory

### Agents
- `src/agents/triage_agent.py` - Geração de tags via OpenAI e rule-based fallback
  - Novo método `_validate_tags()` para sanitização
  - Novo método `_generate_tags()` para fallback rule-based
  - Prompt OpenAI atualizado para incluir geração de tags

### API Routes
- `src/api/routes.py` - Filtro por `tags` e `category` no endpoint `GET /tickets`

### Dashboard
- `src/dashboard/components/escalated_inbox.py` - Filtros de categoria e tags, exibição de tags

### Database
- `src/database/connection.py` - Índices MongoDB para `tags` e `category`

### Tests
- `tests/unit/test_tagging.py` - Testes unitários para validação e geração de tags
- `tests/integration/test_tag_filtering.py` - Testes de integração para filtros API
- `conftest.py` - Atualizado FakeCollection para suportar asserções de update

### Documentation
- `docs/mongodb_collections.md` - Documentação dos novos campos

---

## Como Usar

### 1. Tags são geradas automaticamente

Quando um ticket passa pela triagem, tags são geradas automaticamente:

```python
# Via OpenAI (primary)
{
    "priority": "P2",
    "category": "billing",
    "tags": ["refund", "payment_issue", "duplicate_charge"],
    "sentiment": -0.3,
    "confidence": 0.85
}

# Via rule-based fallback
# Tags são inferidas de keywords no texto
```

### 2. Filtrar tickets por tags via API

```bash
# Filtrar por uma tag
curl -X GET "http://localhost:8000/api/tickets?tags=refund" \
  -H "X-API-Key: sk_..."

# Filtrar por múltiplas tags (OR logic)
curl -X GET "http://localhost:8000/api/tickets?tags=refund,payment_issue" \
  -H "X-API-Key: sk_..."

# Combinar com outros filtros
curl -X GET "http://localhost:8000/api/tickets?category=billing&tags=refund&status=open" \
  -H "X-API-Key: sk_..."
```

### 3. Filtrar no Dashboard

O Dashboard Streamlit agora inclui:
- Dropdown para filtrar por categoria
- Multiselect para filtrar por tags
- Exibição de tags em cada ticket

---

## Tags Disponíveis

### Billing Tags
| Tag | Trigger Keywords |
|-----|------------------|
| `refund` | refund, reembolso |
| `payment_issue` | charge, cobrança, payment, pagamento |
| `invoice` | fatura, invoice |
| `duplicate_charge` | duplicate, duplicado |
| `credit_card` | cartão, card |
| `pricing` | preço, price |
| `subscription` | assinatura, subscription |
| `cancellation` | cancel, cancelar |

### Tech Tags
| Tag | Trigger Keywords |
|-----|------------------|
| `login_issue` | login |
| `password_issue` | senha, password |
| `app_crash` | crash |
| `bug` | bug |
| `error_message` | erro, error |
| `slow_performance` | lento, slow |
| `mobile_app` | app |
| `website` | website |
| `installation` | instalação, install |
| `integration` | integração, integration |
| `api_issue` | api |

### General Tags
| Tag | Trigger Keywords |
|-----|------------------|
| `how_to` | como, how to |
| `question` | pergunta, question |
| `feedback` | feedback |
| `feature_request` | sugestão, suggestion, feature |
| `complaint` | reclamação, complaint |
| `account_issue` | conta, account |

---

## Exemplos de Código

### Validação de Tags

```python
def _validate_tags(self, tags: Any) -> list:
    """Validate and normalize tags array"""
    if not isinstance(tags, list):
        return []
    valid_tags = []
    for tag in tags[:5]:  # Max 5 tags
        if isinstance(tag, str):
            sanitized = tag.lower().strip().replace(" ", "_")
            sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
            if sanitized and len(sanitized) <= 50:
                valid_tags.append(sanitized)
    return valid_tags
```

### Filtro MongoDB com Tags

```python
# API Route
if tags:
    tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
    if tag_list:
        filter_dict["tags"] = {"$in": tag_list}  # OR logic
```

---

## Testes Realizados

### Unit Tests (`tests/unit/test_tagging.py`)
- ✅ Tag validation with valid list
- ✅ Tag sanitization (lowercase, alphanumeric)
- ✅ Max 5 tags limit
- ✅ Empty list handling
- ✅ Non-list input handling
- ✅ Empty string removal
- ✅ Billing keywords tag generation
- ✅ Tech keywords tag generation
- ✅ General keywords tag generation
- ✅ Category fallback tag generation
- ✅ Triage fallback generates tags
- ✅ Triage AI generates tags
- ✅ Tags saved to ticket in database

### Integration Tests (`tests/integration/test_tag_filtering.py`)
- ✅ Filter by single tag
- ✅ Filter by multiple tags
- ✅ Filter by category
- ✅ Combined filters (category + tags + status + priority)

---

## Troubleshooting

### Tags não aparecem no ticket

1. Verifique se o TriageAgent executou:
```bash
# Verificar agent_states
db.agent_states.findOne({ticket_id: "T-123", agent_name: "triage"})
```

2. Verifique se o ticket foi atualizado:
```bash
db.tickets.findOne({ticket_id: "T-123"}, {tags: 1, category: 1})
```

### Filtro por tags não retorna resultados

1. Verifique se o índice existe:
```bash
db.tickets.getIndexes()
# Deve incluir: {"tags": 1}
```

2. Verifique o formato das tags (lowercase, sem espaços):
```bash
# Correto
curl "...?tags=refund,payment_issue"

# Incorreto
curl "...?tags=Refund,Payment Issue"
```

### Tags OpenAI não correspondem ao esperado

1. Verifique os logs para ver se OpenAI foi chamado ou se caiu no fallback
2. Ajuste o prompt em `_analyze_ticket()` se necessário

---

## Performance

### MongoDB Indexes
```javascript
// Índice multikey para tags (permite busca eficiente em arrays)
db.tickets.createIndex({"tags": 1})

// Índice composto para filtro por categoria
db.tickets.createIndex({"company_id": 1, "category": 1})
```

### Considerações
- Máximo de 5 tags por ticket para evitar overhead
- Tags são armazenadas em lowercase para consistência
- Índice multikey permite queries `$in` eficientes

---

## Referências

- [Plano original](../deprecated_futures/019_v1.1_automated_tagging.md)
- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Visão geral do projeto
- [mongodb_collections.md](../mongodb_collections.md) - Schema das collections

---

**Última atualização:** 2026-01-30
**Autor:** Claude Code (AI Assistant)
