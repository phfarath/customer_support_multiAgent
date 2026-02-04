# WhatsApp Business API Setup Guide

Este guia explica como configurar a integração com WhatsApp Business API para o sistema Customer Support MultiAgent.

---

## Sumario

1. [Pre-requisitos](#pre-requisitos)
2. [Criacao da App no Meta Business](#criacao-da-app-no-meta-business)
3. [Configuracao do WhatsApp Business](#configuracao-do-whatsapp-business)
4. [Configuracao do Webhook](#configuracao-do-webhook)
5. [Variaveis de Ambiente](#variaveis-de-ambiente)
6. [Testando a Integracao](#testando-a-integracao)
7. [Producao](#producao)
8. [Troubleshooting](#troubleshooting)

---

## Pre-requisitos

Antes de comecar, voce precisara de:

- [ ] Uma conta no [Meta for Developers](https://developers.facebook.com/)
- [ ] Um [Meta Business Account](https://business.facebook.com/) verificado
- [ ] Um numero de telefone para o WhatsApp Business (nao pode estar vinculado a uma conta WhatsApp pessoal)
- [ ] Um servidor com HTTPS para receber webhooks (ou ngrok para desenvolvimento)

---

## Criacao da App no Meta Business

### 1. Criar uma Nova App

1. Acesse [Meta for Developers](https://developers.facebook.com/)
2. Va em **My Apps** > **Create App**
3. Selecione **Business** como tipo de app
4. Preencha os dados:
   - **App Name**: Customer Support Bot (ou nome de sua preferencia)
   - **App Contact Email**: seu email
   - **Business Account**: selecione sua conta business
5. Clique em **Create App**

### 2. Adicionar WhatsApp Product

1. No dashboard da app, clique em **Add Product**
2. Encontre **WhatsApp** e clique em **Set Up**
3. Siga o fluxo de configuracao inicial

### 3. Obter Credenciais

Na secao **WhatsApp** > **API Setup**, voce encontrara:

- **Phone Number ID**: ID do numero de telefone
- **WhatsApp Business Account ID**: ID da conta business
- **Temporary Access Token**: Token temporario (24h)

> **Nota**: Para producao, voce precisara gerar um **Permanent Access Token**. Veja [Gerando Token Permanente](#gerando-token-permanente).

---

## Configuracao do WhatsApp Business

### 1. Adicionar Numero de Telefone

1. Va em **WhatsApp** > **API Setup**
2. Clique em **Add Phone Number**
3. Siga o processo de verificacao do numero
4. O numero deve receber um codigo SMS ou ligacao para verificacao

### 2. Configurar Perfil Business

```bash
# Via API (opcional - pode fazer pelo dashboard)
curl -X POST \
  'https://graph.facebook.com/v18.0/{phone-number-id}/whatsapp_business_profile' \
  -H 'Authorization: Bearer {access-token}' \
  -H 'Content-Type: application/json' \
  -d '{
    "messaging_product": "whatsapp",
    "about": "Suporte ao Cliente",
    "description": "Atendimento automatizado 24/7",
    "vertical": "TECH"
  }'
```

---

## Configuracao do Webhook

### 1. Expor seu Servidor (Desenvolvimento)

Para desenvolvimento local, use ngrok:

```bash
# Instalar ngrok (se necessario)
brew install ngrok  # macOS
# ou
snap install ngrok  # Linux

# Iniciar tunnel
ngrok http 8000
```

Copie a URL HTTPS gerada (ex: `https://abc123.ngrok.io`)

### 2. Configurar Webhook no Meta

1. Va em **WhatsApp** > **Configuration**
2. Na secao **Webhook**, clique em **Edit**
3. Configure:
   - **Callback URL**: `https://seu-dominio.com/whatsapp/webhook`
   - **Verify Token**: Um token secreto que voce escolhe (ex: `meu_token_secreto_123`)
4. Clique em **Verify and Save**

### 3. Subscribir aos Eventos

Apos verificar o webhook, selecione os eventos para receber:

- [x] `messages` - Mensagens recebidas
- [x] `message_status` - Status de entrega (sent, delivered, read)

### 4. Obter App Secret

1. Va em **Settings** > **Basic**
2. Copie o **App Secret** (clique em Show)
3. Este secret sera usado para verificar assinaturas de webhook

---

## Variaveis de Ambiente

Adicione as seguintes variaveis ao seu arquivo `.env`:

```bash
# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=EAAxxxxx...  # Access token do Meta
WHATSAPP_PHONE_NUMBER_ID=123456789  # Phone Number ID
WHATSAPP_VERIFY_TOKEN=meu_token_secreto_123  # Token que voce escolheu para webhook
WHATSAPP_APP_SECRET=abc123def456...  # App Secret (para verificar assinaturas)
```

### Descricao das Variaveis

| Variavel | Descricao | Obrigatorio |
|----------|-----------|-------------|
| `WHATSAPP_ACCESS_TOKEN` | Token de acesso para a API do WhatsApp | Sim |
| `WHATSAPP_PHONE_NUMBER_ID` | ID do numero de telefone business | Sim |
| `WHATSAPP_VERIFY_TOKEN` | Token customizado para verificacao do webhook | Sim |
| `WHATSAPP_APP_SECRET` | Secret da app para verificar assinaturas | Sim (producao) |

---

## Testando a Integracao

### 1. Verificar Configuracao

```bash
# Testar se as credenciais estao corretas
curl -X GET \
  'https://graph.facebook.com/v18.0/{phone-number-id}/whatsapp_business_profile?fields=about,description' \
  -H 'Authorization: Bearer {access-token}'
```

### 2. Enviar Mensagem de Teste

```bash
# Enviar mensagem (apenas para numeros de teste durante desenvolvimento)
curl -X POST \
  'https://graph.facebook.com/v18.0/{phone-number-id}/messages' \
  -H 'Authorization: Bearer {access-token}' \
  -H 'Content-Type: application/json' \
  -d '{
    "messaging_product": "whatsapp",
    "to": "5511999999999",
    "type": "text",
    "text": {"body": "Hello from API!"}
  }'
```

### 3. Testar Webhook Localmente

```bash
# Simular um webhook do WhatsApp
curl -X POST http://localhost:8000/whatsapp/webhook \
  -H 'Content-Type: application/json' \
  -d '{
    "object": "whatsapp_business_account",
    "entry": [{
      "id": "WABA_ID",
      "changes": [{
        "value": {
          "messaging_product": "whatsapp",
          "metadata": {
            "display_phone_number": "15551234567",
            "phone_number_id": "123456789"
          },
          "contacts": [{"profile": {"name": "Test"}, "wa_id": "5511999999999"}],
          "messages": [{
            "from": "5511999999999",
            "id": "wamid.test",
            "timestamp": "1704067200",
            "text": {"body": "Ola, preciso de ajuda!"},
            "type": "text"
          }]
        },
        "field": "messages"
      }]
    }]
  }'
```

### 4. Executar Testes Automatizados

```bash
# Testes unitarios
pytest tests/unit/test_whatsapp_adapter.py -v

# Testes de integracao
pytest tests/integration/test_whatsapp_e2e.py -v
```

---

## Producao

### Gerando Token Permanente

Tokens temporarios expiram em 24 horas. Para producao:

1. Va em **Business Settings** > **System Users**
2. Crie um **System User** com role Admin
3. Gere um token com as permissoes:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
4. Use este token permanente no `WHATSAPP_ACCESS_TOKEN`

### Verificacao do Business

Para enviar mensagens para qualquer usuario (nao apenas numeros de teste):

1. Complete a **Business Verification** em Business Settings
2. Solicite acesso ao **WhatsApp Business API** production tier
3. Aguarde aprovacao (pode levar alguns dias)

### Checklist de Producao

- [ ] Token permanente gerado (System User)
- [ ] Business verificado
- [ ] App em modo Live (nao Development)
- [ ] `WHATSAPP_APP_SECRET` configurado
- [ ] HTTPS configurado no servidor
- [ ] Rate limiting configurado
- [ ] Logs de webhook configurados

### Limites de Mensagens

| Tier | Mensagens/dia | Requisitos |
|------|---------------|------------|
| Development | 1,000 | Apenas numeros de teste |
| Tier 1 | 1,000 | Business verificado |
| Tier 2 | 10,000 | Qualidade de mensagens |
| Tier 3 | 100,000 | Alto volume sustentado |
| Tier 4 | Ilimitado | Enterprise |

---

## Troubleshooting

### Erro: Webhook Verification Failed

**Causa**: O `verify_token` nao coincide.

**Solucao**:
1. Verifique se `WHATSAPP_VERIFY_TOKEN` esta correto no `.env`
2. Reinicie o servidor
3. Tente verificar o webhook novamente

### Erro: Invalid Signature

**Causa**: O `app_secret` esta incorreto.

**Solucao**:
1. Va em Settings > Basic no Meta Developers
2. Copie o App Secret novamente
3. Atualize `WHATSAPP_APP_SECRET` no `.env`

### Erro: Message Failed to Send

**Causa**: Token invalido ou numero nao autorizado.

**Solucao**:
1. Verifique se o token nao expirou
2. Em desenvolvimento, adicione o numero como "Test Number"
3. Verifique o formato do numero (codigo do pais sem +)

### Erro: Rate Limited

**Causa**: Muitas requisicoes a API.

**Solucao**:
1. Implemente exponential backoff
2. Verifique seu tier de mensagens
3. Considere batch de mensagens

### Mensagens Nao Chegam

**Causa**: Webhook nao esta funcionando.

**Solucao**:
1. Verifique se o servidor esta acessivel externamente
2. Confira os logs em `logs/whatsapp_webhook.jsonl`
3. Teste com curl localmente
4. Verifique se os eventos corretos estao subscritos

### Debug Mode

Para habilitar logs detalhados:

```bash
# No .env
LOG_LEVEL=DEBUG
```

Logs de webhook sao salvos em: `logs/whatsapp_webhook.jsonl`

---

## Endpoints Disponiveis

| Metodo | Endpoint | Descricao | Auth |
|--------|----------|-----------|------|
| GET | `/whatsapp/webhook` | Verificacao do webhook | Nenhuma |
| POST | `/whatsapp/webhook` | Receber mensagens | Signature |
| POST | `/whatsapp/send` | Enviar mensagem | API Key |
| POST | `/whatsapp/send/template` | Enviar template | API Key |
| GET | `/whatsapp/business-profile` | Obter perfil | API Key |
| POST | `/whatsapp/mark-read` | Marcar como lido | API Key |
| GET | `/whatsapp/media/{id}` | Obter URL de midia | API Key |

---

## Referencias

- [WhatsApp Cloud API Documentation](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Webhook Setup Guide](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/set-up-webhooks)
- [Message Templates](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates)
- [Media Messages](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages#media-messages)
- [Rate Limits](https://developers.facebook.com/docs/whatsapp/cloud-api/overview#throughput)

---

**Ultima atualizacao**: 2026-02-04
