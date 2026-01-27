# Multi-Tenancy System Documentation

## Overview

The MultiAgent Customer Support System now supports **multi-tenancy**, allowing multiple companies/organizations to use the same bot instance with their own configurations, policies, and products.

## Architecture

```
Company 1 (empresa1)           Company 2 (empresa2)           Company 3 (empresa3)
        |                              |                              |
        v                              v                              v
        |                              |                              |
    +------------------------------+------------------------------+------------------------------+
                        Multi-Tenancy Support System
    +------------------------------+------------------------------+
```

### Components

1. **Company Config** - Stores company-specific information (policies, products, services)
2. **Pipeline** - Loads company context and passes to agents
3. **Agents** - Use company context to generate responses
4. **Telegram Webhook** - Identifies company from metadata
5. **Company API** - REST endpoints for managing company configs

## Database Schema

### Collections

#### `company_configs`
Stores company configurations for multi-tenancy support.

```json
{
  "company_id": "empresa1",
  "company_name": "Minha Empresa",
  "support_email": "suporte@empresa.com",
  "support_phone": "+55 11 9999-9999",
  "refund_policy": "Reembolsos em até 30 dias após cancelamento",
  "cancellation_policy": "Cancelamento sem multa com 30 dias de antecedência",
  "payment_methods": ["Cartão de Crédito", "PIX", "Boleto"],
  "products": [
    {"name": "Plano Premium", "price": "R$ 99,90/mês"},
    {"name": "Plano Básico", "price": "R$ 49,90/mês"}
  ],
  "business_hours": {
    "Seg-Sex": "09:00-18:00",
    "Sáb-Dom": "09:00-14:00"
  },
  "bot_name": "Suporte Bot",
  "bot_welcome_message": "Olá! Bem-vindo ao suporte da Minha Empresa. Como posso ajudar você hoje?",
  "bot_handoff_message": "Seu ticket #{ticket_id} foi escalado. Um atendente entrará em contato em breve.",
  "handoff_warning_message": "⚠️ Estamos transferindo você para um especialista. Motivo: {reason}. Aguarde um momento.",
  "custom_instructions": "Sempre use linguagem amigável e ofereça descontos de 10% para clientes fiéis."
}
```


### Indexes

```javascript
// company_configs collection
db.company_configs.createIndex({ "company_id": 1 }, { unique: true })
```

## API Endpoints

### Company Configuration API

#### Create Company Config

```http
POST /api/companies/
Content-Type: application/json

{
  "company_id": "empresa1",
  "company_name": "Minha Empresa",
  "support_email": "suporte@empresa.com",
  "support_phone": "+55 11 9999-9999",
  "refund_policy": "Reembolsos em até 30 dias após cancelamento",
  "cancellation_policy": "Cancelamento sem multa com 30 dias de antecedência",
  "payment_methods": ["Cartão de Crédito", "PIX", "Boleto"],
  "products": [
    {"name": "Plano Premium", "price": "R$ 99,90/mês"},
    {"name": "Plano Básico", "price": "R$ 49,90/mês"}
  ],
  "business_hours": {
    "Seg-Sex": "09:00-18:00",
    "Sáb-Dom": "09:00-14:00"
  },
  "bot_name": "Suporte Bot",
  "bot_welcome_message": "Olá! Bem-vindo ao suporte da Minha Empresa. Como posso ajudar você hoje?",
  "custom_instructions": "Sempre use linguagem amigável e ofereça descontos de 10% para clientes fiéis."
}
```

#### Get Company Config

```http
GET /api/companies/{company_id}
```

#### Update Company Config

```http
PUT /api/companies/{company_id}
Content-Type: application/json

{
  "company_name": "Minha Empresa Atualizada",
  "refund_policy": "Nova política de reembolso"
  // ... other fields to update
}
```

#### Delete Company Config

```http
DELETE /api/companies/{company_id}
```

#### List All Companies

```http
GET /api/companies/
```

## Telegram Webhook Integration

### Webhook with Company ID

When sending messages to the webhook, include `company_id` in the metadata:

```bash
curl -X POST "https://your-domain.com/telegram/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-ngrok-url.com/telegram/webhook",
    "metadata": {
      "company_id": "empresa1"
    }
  }'
```

### Metadata Structure

The webhook adapter now extracts `company_id` from metadata:

```json
{
  "external_user_id": "telegram:123456789",
  "text": "Help me with my order",
  "metadata": {
    "update_id": 90633605,
    "message_id": 1,
    "chat_id": 6257466018,
    "chat_type": "private",
    "username": "ph_farath",
    "first_name": "pedro",
    "last_name": "farath",
    "language_code": "en",
    "company_id": "empresa1"  // Added for multi-tenancy
  }
}
```

## Agent Context Enhancement

### Company Context in Agent Prompts

Agents now receive company context including:

- **Company Name**: Displayed in responses
- **Refund Policy**: Used for billing-related inquiries
- **Cancellation Policy**: Used for cancellation requests
- **Payment Methods**: Available payment options
- **Products/Services**: Company offerings
- **Business Hours**: Support availability
- **Custom Instructions**: Company-specific guidelines

### Example Agent Prompt with Company Context

```
You are a friendly customer support bot for the billing team. Your goal is to help customers in a natural, conversational way.

Important guidelines:
- Be empathetic and apologetic and conversational - write like a real person would speak
- Start with a friendly greeting (Olá, Oi, Bom dia, etc.)
- Address the customer's specific issue directly
- Provide helpful next steps or information clearly
- Keep responses concise but comprehensive
- Use natural, everyday Portuguese - avoid overly formal language
- Don't use phrases like "Prezado(a) cliente" - be more personal
- Sign off naturally (Até logo, Um abraço, etc.)
- Present yourself as a helpful support assistant, not a robot

=== CONTEXTO DA EMPRESA ===
Empresa: Minha Empresa

Políticas:
- Política de Reembolso: Reembolsos em até 30 dias após cancelamento
- Política de Cancelamento: Cancelamento sem multa com 30 dias de antecedência

Métodos de Pagamento:
- Cartão de Crédito
- PIX
- Boleto

Produtos/Serviços:
- Plano Premium (R$ 99,90/mês)
- Plano Básico (R$ 49,90/mês)

Horário de Atendimento:
- Seg-Sex: 09:00-18:00
- Sáb-Dom: 09:00-14:00

=== FIM DO CONTEXTO ===

Remember: You're having a conversation with a real person. Be warm, understanding, and helpful.
```

## Setup Guide

### Step 1: Configure a New Company

Run the interactive setup script:

```bash
python scripts/setup_company.py
```

This will prompt you for:
- Company ID (e.g., `empresa1`, `minhaempresa`)
- Company name
- Contact information (email, phone)
- Policies (refund, cancellation)
- Payment methods
- Products/services
- Business hours
- Bot name and welcome message
- Custom instructions

The script will:
1. Create the company configuration via API
2. Display the configuration ID and setup instructions

### Step 2: Configure Telegram Webhook for the Company

After creating the company configuration, set up the webhook with the company ID:

```bash
curl -X POST "http://localhost:8000/api/companies/empresa1/webhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-ngrok-url.com/telegram/webhook",
    "metadata": {
      "company_id": "empresa1"
    }
  }'
```

### Step 3: Test the Bot

Send a message to your Telegram bot. The bot will now:
1. Use the company's welcome message (if configured)
2. Respond using company-specific policies and product information
3. Follow company custom instructions

## File Structure

```
src/
├── models/
│   ├── company_config.py          # Company configuration models
│   └── ...
├── api/
│   ├── company_routes.py          # Company configuration API
│   ├── telegram_routes.py         # Updated to extract company_id
│   └── ...
├── utils/
│   └── pipeline.py              # Updated to load company context
└── agents/
    ├── resolver_agent.py          # Updated to use company context
    └── ...
scripts/
└── setup_company.py             # Interactive company setup script
```

## Benefits

1. **Multi-Tenancy Support**: Multiple companies can use the same bot with their own configurations
2. **Natural Conversations**: Bot responses are more conversational and less robotic
3. **Company-Specific Responses**: Each company can have its own policies, products, and services
4. **Easy Configuration**: Interactive script for setting up new companies
5. **Grounding**: Agents have access to company context for accurate responses
6. **Scalable**: Add new companies without code changes

## Example Use Cases

### Use Case 1: Different Refund Policies

**Company A** (empresa1):
- Refund policy: 30 days
- Products: Premium, Basic

**Company B** (empresa2):
- Refund policy: 7 days
- Products: Enterprise, Custom

When a customer asks about refunds, the bot will respond with the correct policy for their company.

### Use Case 2: Different Products

**Company A**:
- Products: Premium, Basic
- Payment: Credit Card, PIX

**Company B**:
- Products: Enterprise, Custom
- Payment: Bank Transfer, Boleto

The bot will only show available payment methods for the customer's company.

### Use Case 3: Custom Bot Behavior

Each company can set:
- Custom bot name (e.g., "Suporte Tech" vs "Atendimento Cliente")
- Welcome message for new conversations
- Custom instructions for agents (e.g., "Always offer 10% discount to loyal customers")

## Troubleshooting

### Company Not Loading

If the bot is not using company context:

1. Check if `company_id` is in the webhook metadata
2. Verify the company config exists in MongoDB
3. Check server logs for company config loading errors

### Incorrect Responses

If the bot is still responding with generic information:

1. Verify the company config was created successfully
2. Check if the company_id is correctly set in webhook metadata
3. Restart the server to reload company configurations

### Testing

Test with different companies:

```bash
# Setup company 1
python scripts/setup_company.py

# Setup company 2
python scripts/setup_company.py

# Test webhook for company 1
curl -X POST "http://localhost:8000/api/companies/empresa1/webhook" \
  -d '{"url": "https://ngrok-url.com/telegram/webhook", "metadata": {"company_id": "empresa1"}}'

# Test webhook for company 2
curl -X POST "http://localhost:8000/api/companies/empresa2/webhook" \
  -d '{"url": "https://ngrok-url.com/telegram/webhook", "metadata": {"company_id": "empresa2"}}'
```

## Next Steps

- [ ] Add company-specific welcome messages when starting new conversations
- [ ] Implement RAG (Retrieval Augmented Generation) for product documentation
- [ ] Add analytics for multi-tenancy monitoring
- [ ] Create admin dashboard for managing companies
- [ ] Add rate limiting per company
- [ ] Implement company-specific SLA tracking
