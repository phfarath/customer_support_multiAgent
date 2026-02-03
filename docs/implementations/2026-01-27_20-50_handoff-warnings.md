# Proactive Handoff Warnings

> **Implementado em:** 2026-01-27 20:50
> **Status:** ✅ Production-ready

---

## Descrição

Feature que adiciona comunicação transparente antes do handoff para humano. Quando um ticket é escalado, o cliente recebe uma mensagem **warning** explicando os motivos da escalação, seguida da mensagem de **handoff** padrão.

**Benefícios:**
- Cliente sabe **por que** está sendo transferido
- Melhora a transparência do atendimento
- Mensagem customizável por empresa via `handoff_warning_message`

---

## Arquivos Modificados/Criados

### Modificados
- `src/models/company_config.py` - Campo `handoff_warning_message` adicionado
- `src/api/ingest_routes.py` - Função `_generate_warning_message()` e fluxo de escalação
- `docs/MULTI_TENANCY.md` - Documentação do novo campo

### Criados
- `tests/unit/test_handoff_warning.py` - 11 testes unitários

---

## Como Usar

### 1. Configuração Padrão (Automática)

Sem configuração adicional, o sistema usa o template padrão:

```
⚠️ Para melhor atendê-lo, sua solicitação será transferida para um de nossos especialistas. Motivo: {motivos}. Aguarde um momento, por favor.
```

### 2. Template Customizado

Configure via API de empresas:

```bash
curl -X PUT "http://localhost:8000/api/companies/empresa1" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: sua_api_key" \
  -d '{
    "handoff_warning_message": "🔄 {reason} - Conectando você com um especialista!"
  }'
```

**Placeholders disponíveis:**
- `{reason}` - Primeiro motivo da escalação
- `{reasons}` - Todos os motivos separados por vírgula

---

## Exemplos de Código

### Função de geração de warning

```python
def _generate_warning_message(
    reasons: list[str], 
    company_config: CompanyConfig | None = None
) -> str:
    default_message = (
        "⚠️ Para melhor atendê-lo, sua solicitação será transferida "
        "para um de nossos especialistas."
    )
    
    if reasons:
        reason_summary = reasons[0] if len(reasons) == 1 else f"{reasons[0]} e {reasons[1]}"
        default_message += f" Motivo: {reason_summary}."
    
    default_message += " Aguarde um momento, por favor."
    
    if company_config and company_config.handoff_warning_message:
        try:
            return company_config.handoff_warning_message.format(
                reason=reasons[0] if reasons else "necessidade de especialista",
                reasons=", ".join(reasons) if reasons else "necessidade de especialista"
            )
        except Exception:
            return company_config.handoff_warning_message
    
    return default_message
```

### Exemplo de mensagem combinada

```
⚠️ Para melhor atendê-lo, sua solicitação será transferida para um de nossos especialistas. Motivo: cliente frustrado e problema técnico complexo. Aguarde um momento, por favor.

Seu ticket #TKT-2026-0127-001 foi escalado. Um atendente entrará em contato em breve.
```

---

## Testes Realizados

| Teste | Status |
|-------|--------|
| Warning com template padrão (1 motivo) | ✅ |
| Warning com template padrão (múltiplos motivos) | ✅ |
| Warning sem motivos específicos | ✅ |
| Warning com template custom `{reason}` | ✅ |
| Warning com template custom `{reasons}` | ✅ |
| Warning com template custom sem placeholders | ✅ |
| Warning com template custom e lista vazia de motivos | ✅ |
| Warning com config nula | ✅ |
| Warning com config sem `handoff_warning_message` | ✅ |
| Verificação de estrutura da mensagem | ✅ |
| Verificação de tamanho razoável | ✅ |

**Comando para rodar testes:**
```bash
pytest tests/unit/test_handoff_warning.py -v
```

---

## Troubleshooting

### Warning não aparece

1. Verifique se o ticket foi realmente escalado (`escalated: true` na resposta)
2. Confirme que o ticket **não estava** previamente escalado (warning só é enviado na primeira escalação)

### Template customizado não funciona

1. Verifique se o campo `handoff_warning_message` foi salvo corretamente na company config
2. Confirme que os placeholders estão corretos (`{reason}` ou `{reasons}`)

### Caractere ⚠️ não aparece

Verifique se o encoding do Telegram/canal suporta emojis Unicode.

---

## Referências

- [MULTI_TENANCY.md](../MULTI_TENANCY.md) - Documentação de multi-tenancy com campo `handoff_warning_message`
- [Feature original](../deprecated_futures/010_v1.0_handoff_warnings.md) - Especificação inicial da feature
