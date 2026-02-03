# Agent Confidence Transparency

> **Implementado em:** 2026-01-27 23:02
> **Status:** ✅ Production-ready

---

## Descrição

Feature que expõe scores de confiança e reasoning das decisões de AI no dashboard, permitindo operadores e clientes entenderem o porquê das decisões tomadas pelo sistema (triage, routing, resolução, escalação).

---

## Arquivos Modificados/Criados

### Modificados

| Arquivo | Descrição |
|---------|-----------|
| `src/models/interaction.py` | Novo modelo `AIDecisionMetadata`, campo `ai_metadata` em `InteractionBase` |
| `src/models/__init__.py` | Export de `AIDecisionMetadata` |
| `src/agents/triage_agent.py` | Prompt atualizado para reasoning, salvamento de `ai_metadata` |
| `src/agents/router_agent.py` | Reasoning no prompt e persistência em `routing_decisions` |
| `src/agents/resolver_agent.py` | Reasoning para escalação/resolução, salvamento de `ai_metadata` |
| `src/dashboard/components/escalated_inbox.py` | Nova seção "AI Decision Insights" |
| `docs/mongodb_collections.md` | Documentação dos novos campos |

### Criados

| Arquivo | Descrição |
|---------|-----------|
| `tests/unit/test_ai_metadata.py` | 10 unit tests para o modelo AIDecisionMetadata |

---

## Como Usar

### No Dashboard (Tickets Escalados)

1. Acesse o dashboard: `streamlit run src/dashboard/app.py`
2. Navegue para "📥 Tickets Escalados"
3. Selecione um ticket escalado
4. Veja a nova seção "🧠 AI Decision Insights" exibindo:
   - **Confidence Score**: Com indicador de cor (🟢 Alta ≥70%, 🟡 Média 40-69%, 🔴 Baixa <40%)
   - **Tipo de Decisão**: Triage, Routing, Resolution ou Escalation
   - **Reasoning**: Explicação expandível da decisão
   - **Fatores**: Lista de fatores considerados

### Via MongoDB (Consulta Direta)

```javascript
// Buscar interações com AI metadata
db.interactions.find({
  "ai_metadata": { "$exists": true },
  "ai_metadata.decision_type": "escalation"
})
```

---

## Exemplos de Código

### Modelo AIDecisionMetadata

```python
from src.models import AIDecisionMetadata

metadata = AIDecisionMetadata(
    confidence_score=0.45,
    reasoning="Escalation triggered due to: Negative sentiment (-0.8), SLA breach",
    decision_type="escalation",
    factors=["Negative sentiment: -0.80", "SLA breach: 25.5 hours"]
)
```

### Criando Interação com AI Metadata

```python
from src.models import InteractionCreate, InteractionType, AIDecisionMetadata

ai_metadata = AIDecisionMetadata(
    confidence_score=0.85,
    reasoning="Classified as P1 due to cancellation threat",
    decision_type="triage",
    factors=["Priority: P1", "Category: billing", "Sentiment: -0.7"]
)

interaction = InteractionCreate(
    ticket_id="TKT-123",
    type=InteractionType.AGENT_RESPONSE,
    content="Resposta do agente",
    ai_metadata=ai_metadata
)
```

---

## Testes Realizados

### Unit Tests (10 testes - todos passando ✅)

```bash
python3 -m pytest tests/unit/test_ai_metadata.py -v
```

| Classe | Teste | Status |
|--------|-------|--------|
| `TestAIDecisionMetadata` | `test_ai_decision_metadata_creation` | ✅ |
| `TestAIDecisionMetadata` | `test_ai_decision_metadata_defaults` | ✅ |
| `TestAIDecisionMetadata` | `test_ai_decision_metadata_partial` | ✅ |
| `TestInteractionWithAIMetadata` | `test_interaction_with_ai_metadata` | ✅ |
| `TestInteractionWithAIMetadata` | `test_interaction_without_ai_metadata` | ✅ |
| `TestInteractionWithAIMetadata` | `test_interaction_serialization_with_metadata` | ✅ |
| `TestDecisionTypes` | `test_triage_decision` | ✅ |
| `TestDecisionTypes` | `test_routing_decision` | ✅ |
| `TestDecisionTypes` | `test_resolution_decision` | ✅ |
| `TestDecisionTypes` | `test_escalation_decision` | ✅ |

---

## Troubleshooting

### AI Insights não aparece no dashboard

**Causa:** O ticket não possui interações com `ai_metadata` (tickets antigos).

**Solução:** Apenas novos tickets processados após esta implementação terão AI metadata. Para tickets antigos, a mensagem "ℹ️ Nenhuma metadata de AI disponível" será exibida.

### Confidence score sempre baixo

**Causa:** O modelo OpenAI está retornando baixa confiança nas respostas.

**Solução:** Verifique os prompts dos agentes e considere ajustar os thresholds em `settings`.

---

## Referências

- [Feature Spec](../futures/011_v1.0_confidence_transparency.md)
- [MongoDB Collections](../mongodb_collections.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
