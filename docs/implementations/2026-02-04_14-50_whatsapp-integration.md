# WhatsApp Business API Integration

> **Implementado em:** 2026-02-04 14:50
> **Status:** Production-ready

---

## Descricao

Integracao completa com WhatsApp Business Cloud API para receber e enviar mensagens de clientes via WhatsApp. A implementacao segue o mesmo padrao do TelegramAdapter existente, permitindo que mensagens do WhatsApp sejam processadas pelo pipeline de atendimento do sistema.

### Funcionalidades Implementadas

- Webhook verification (GET endpoint para Meta)
- Recebimento de mensagens (texto, imagem, audio, video, documento, localizacao)
- Envio de mensagens de texto
- Envio de templates pre-aprovados
- Envio de mensagens interativas (botoes e listas)
- Envio de midias (imagens, documentos)
- Marcacao de mensagens como lidas
- Download de midias recebidas
- Verificacao de assinatura (X-Hub-Signature-256)
- Redacao de PII em logs

---

## Arquivos Modificados/Criados

### Novos Arquivos

| Arquivo | Descricao |
|---------|-----------|
| `src/models/whatsapp.py` | Modelos Pydantic para payload de webhook e mensagens |
| `src/adapters/whatsapp_adapter.py` | Adapter principal para WhatsApp Cloud API |
| `src/api/whatsapp_routes.py` | Endpoints FastAPI para webhook e operacoes |
| `tests/unit/test_whatsapp_adapter.py` | Testes unitarios do adapter |
| `tests/integration/test_whatsapp_e2e.py` | Testes E2E do fluxo completo |
| `docs/WHATSAPP_SETUP.md` | Guia de configuracao detalhado |

### Arquivos Modificados

| Arquivo | Alteracao |
|---------|-----------|
| `src/config.py` | Adicionadas configuracoes do WhatsApp |
| `src/adapters/__init__.py` | Export do WhatsAppAdapter |
| `src/api/__init__.py` | Export do whatsapp_router |
| `main.py` | Registro do whatsapp_router |

---

## Como Usar

### 1. Configurar Variaveis de Ambiente

```bash
# .env
WHATSAPP_ACCESS_TOKEN=EAAxxxxx...
WHATSAPP_PHONE_NUMBER_ID=123456789
WHATSAPP_VERIFY_TOKEN=seu_token_secreto
WHATSAPP_APP_SECRET=abc123def456...  # Obrigatorio em producao
```

### 2. Configurar Webhook no Meta Business

1. Acesse [Meta for Developers](https://developers.facebook.com/)
2. Configure o webhook URL: `https://seu-dominio.com/whatsapp/webhook`
3. Use o mesmo `WHATSAPP_VERIFY_TOKEN` configurado no `.env`
4. Selecione os eventos: `messages`, `message_status`

### 3. Testar Integracao

```bash
# Testar webhook localmente
curl -X POST http://localhost:8000/whatsapp/webhook \
  -H 'Content-Type: application/json' \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "WABA_ID",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {"display_phone_number": "15551234567", "phone_number_id": "123456789"},
          "contacts": [{"profile": {"name": "Test"}, "wa_id": "5511999999999"}],
          "messages": [{
            "from": "5511999999999",
            "id": "wamid.test",
            "timestamp": "1704067200",
            "text": {"body": "Ola!"},
            "type": "text"
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

### 4. Enviar Mensagem via API

```bash
curl -X POST 'http://localhost:8000/whatsapp/send?to=5511999999999&text=Ola!' \
  -H 'X-API-Key: sua_api_key'
```

---

## Exemplos de Codigo

### Usando o WhatsAppAdapter Diretamente

```python
from src.adapters import WhatsAppAdapter

adapter = WhatsAppAdapter()

# Enviar mensagem de texto
await adapter.send_message(
    to="5511999999999",
    text="Ola! Como posso ajudar?"
)

# Enviar mensagem com botoes
await adapter.send_interactive_buttons(
    to="5511999999999",
    body_text="Escolha uma opcao:",
    buttons=[
        {"id": "suporte", "title": "Suporte"},
        {"id": "vendas", "title": "Vendas"},
    ]
)

# Enviar template
await adapter.send_template(
    to="5511999999999",
    template_name="hello_world",
    language_code="pt_BR"
)
```

### Processando Webhooks

```python
from src.adapters import WhatsAppAdapter

adapter = WhatsAppAdapter()

# Verificar assinatura
is_valid = adapter.verify_signature(
    payload=request_body_bytes,
    signature=request.headers["X-Hub-Signature-256"]
)

# Parsear mensagens
messages = adapter.parse_webhook_payload(webhook_json)
for msg in messages:
    print(f"De: {msg.sender_name} ({msg.wa_id})")
    print(f"Texto: {msg.text}")
```

---

## Testes Realizados

### Testes Unitarios

```bash
pytest tests/unit/test_whatsapp_adapter.py -v
```

| Teste | Status |
|-------|--------|
| Verificacao de webhook (sucesso) | Pass |
| Verificacao de webhook (token errado) | Pass |
| Verificacao de assinatura HMAC | Pass |
| Parse de mensagem de texto | Pass |
| Parse de mensagem de imagem | Pass |
| Parse de mensagem de localizacao | Pass |
| Parse de resposta interativa | Pass |
| Parse de status update | Pass |
| Envio de mensagem de texto | Pass |
| Envio de template | Pass |
| Envio de botoes interativos | Pass |
| Mark as read | Pass |
| Download de midia | Pass |

### Testes de Integracao

```bash
pytest tests/integration/test_whatsapp_e2e.py -v
```

| Teste | Status |
|-------|--------|
| Fluxo completo de verificacao | Pass |
| Processamento de mensagem de texto | Pass |
| Processamento de status update | Pass |
| Verificacao de assinatura em producao | Pass |
| Multiplas mensagens em um webhook | Pass |
| Tratamento de erros | Pass |

---

## Troubleshooting

### Webhook Verification Failed

**Problema**: Meta nao consegue verificar o webhook.

**Solucoes**:
1. Verifique se `WHATSAPP_VERIFY_TOKEN` esta correto
2. Confirme que o servidor esta acessivel publicamente (HTTPS)
3. Verifique logs em `logs/whatsapp_webhook.jsonl`

### Invalid Signature (403)

**Problema**: Assinatura do webhook invalida.

**Solucoes**:
1. Verifique se `WHATSAPP_APP_SECRET` esta correto
2. Copie novamente de Settings > Basic no Meta Developers
3. Em desenvolvimento, pode deixar `WHATSAPP_APP_SECRET` vazio para pular verificacao

### Mensagem Nao Enviada

**Problema**: Erro ao enviar mensagem.

**Solucoes**:
1. Verifique se o token nao expirou (use token permanente)
2. Em desenvolvimento, adicione o numero como "Test Number"
3. Verifique formato: numero sem + (ex: `5511999999999`)

### Logs de Debug

```bash
# Verificar logs de webhook
tail -f logs/whatsapp_webhook.jsonl

# Habilitar debug
LOG_LEVEL=DEBUG python main.py
```

---

## Fluxo de Mensagens

```
Cliente WhatsApp
      |
      v
[Meta Cloud API] --> POST /whatsapp/webhook
      |
      v
[WhatsApp Routes] --> verify_signature()
      |
      v
[WhatsApp Adapter] --> parse_webhook_payload()
      |
      v
[Ingest Routes] --> ingest_message()
      |
      v
[Pipeline] --> triage -> route -> resolve
      |
      v
[WhatsApp Adapter] --> send_message()
      |
      v
[Meta Cloud API] --> Cliente WhatsApp
```

---

## Configuracoes de Producao

| Variavel | Valor | Obrigatorio |
|----------|-------|-------------|
| `WHATSAPP_ACCESS_TOKEN` | Token permanente (System User) | Sim |
| `WHATSAPP_PHONE_NUMBER_ID` | ID do numero verificado | Sim |
| `WHATSAPP_VERIFY_TOKEN` | Token customizado | Sim |
| `WHATSAPP_APP_SECRET` | Secret da app | Sim |
| `ENVIRONMENT` | `production` | Sim |

---

## Referencias

- [WhatsApp Cloud API Documentation](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Webhook Setup Guide](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates)
- [docs/WHATSAPP_SETUP.md](../WHATSAPP_SETUP.md) - Guia completo de configuracao
- [src/adapters/telegram_adapter.py](../../src/adapters/telegram_adapter.py) - Implementacao de referencia
