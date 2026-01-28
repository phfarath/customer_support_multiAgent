# Documentação das Collections do MongoDB

Este documento descreve a estrutura de dados (schema) de cada collection utilizada no banco de dados do sistema de Suporte ao Cliente Multi-Agente.

## Índice

1. [tickets](#tickets)
2. [interactions](#interactions)
3. [customers](#customers)
4. [bot_sessions](#bot_sessions)
5. [company_configs](#company_configs)
6. [agent_states](#agent_states)
7. [routing_decisions](#routing_decisions)
8. [audit_logs](#audit_logs)

---

## 1. tickets <a name="tickets"></a>

Armazena os chamados de suporte (tickets). É a entidade central do sistema.

**Nome da Collection:** `tickets`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `ticket_id` | String | Sim | ID único legível do ticket (ex: `telegram_12345_1700000000`) |
| `customer_id` | String | Sim | ID do cliente associado |
| `company_id` | String | Não | ID da empresa (multi-tenancy) |
| `external_user_id` | String | Não | ID do usuário no canal externo (ex: chat_id do Telegram) |
| `channel` | String | Sim | Canal de origem (`email`, `chat`, `phone`, `telegram`, `whatsapp`) |
| `subject` | String | Sim | Assunto do ticket |
| `description` | String | Sim | Descrição detalhada ou mensagem inicial |
| `priority` | String | Sim | Prioridade (`P1`, `P2`, `P3`) |
| `status` | String | Sim | Status atual (`open`, `in_progress`, `escalated`, `resolved`) |
| `current_phase` | String | Sim | Fase do pipeline (`triage`, `routing`, `resolution`, `escalation`) |
| `interactions_count` | Int | Sim | Contador de interações |
| `lock_version` | Int | Sim | Controle de concorrência otimista |
| `created_at` | DateTime | Sim | Data de criação |
| `updated_at` | DateTime | Sim | Data da última atualização |

---

## 2. interactions <a name="interactions"></a>

Histórico de mensagens e ações dentro de um ticket.

**Nome da Collection:** `interactions`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `ticket_id` | String | Sim | ID do ticket relacionado |
| `type` | String | Sim | Tipo (`customer_message`, `agent_response`, `system_update`) |
| `content` | String | Sim | Conteúdo textual da interação |
| `channel` | String | Não | Canal por onde ocorreu (`telegram`, etc) |
| `sentiment_score` | Float | Sim | Score de sentimento (0.0 a 1.0) |
| `ai_metadata` | Object | Não | Metadata de decisão AI para transparência (ver sub-campos) |
| `ai_metadata.confidence_score` | Float | Não | Score de confiança da decisão (0.0 a 1.0) |
| `ai_metadata.reasoning` | String | Não | Explicação textual da decisão tomada |
| `ai_metadata.decision_type` | String | Não | Tipo: `triage`, `routing`, `resolution`, `escalation` |
| `ai_metadata.factors` | Array[String] | Não | Lista de fatores considerados na decisão |
| `created_at` | DateTime | Sim | Data e hora da interação |

---

## 3. customers <a name="customers"></a>

Cadastro de clientes identificados, vinculando telefone e dados pessoais.

**Nome da Collection:** `customers`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `customer_id` | String | Sim | ID único do cliente (ex: `CUST-5511999999999`) |
| `phone_number` | String | Sim | Telefone (formato internacional) |
| `company_id` | String | Sim | ID da empresa à qual o cliente pertence |
| `name` | String | Não | Nome do cliente |
| `email` | String | Não | Email do cliente |
| `telegram_chat_id` | Int | Não | ID do chat no Telegram |
| `metadata` | Object | Não | Dados adicionais flexíveis |
| `created_at` | DateTime | Sim | Data de cadastro |
| `updated_at` | DateTime | Sim | Data de atualização |

---

## 4. bot_sessions <a name="bot_sessions"></a>

Gerencia o estado da sessão do usuário no Bot (Telegram/WhatsApp), persistindo contexto entre mensagens.

**Nome da Collection:** `bot_sessions`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `chat_id` | Int | Sim | ID do chat (Telegram) |
| `state` | String | Sim | Estado atual (`new`, `awaiting_phone`, `registered`, etc) |
| `username` | String | Não | Username no Telegram |
| `first_name` | String | Não | Primeiro nome |
| `last_name` | String | Não | Último nome |
| `customer_id` | String | Não | ID do cliente (se identificado) |
| `company_id` | String | Não | ID da empresa vinculada |
| `phone_number` | String | Não | Telefone registrado |
| `message_count` | Int | Sim | Contador para rate limiting |
| `rate_limit_until` | DateTime | Não | Data/hora até quando está bloqueado (se aplicável) |
| `created_at` | DateTime | Sim | Data de criação da sessão |
| `updated_at` | DateTime | Sim | Data da última atualização |
| `last_message_at` | DateTime | Não | Timestamp da última mensagem recebida |

---

## 5. company_configs <a name="company_configs"></a>

Configurações específicas de cada empresa (Multi-tenancy), como, mensagens do bot, horários e políticas.

**Nome da Collection:** `company_configs`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `company_id` | String | Sim | ID único da empresa |
| `company_name` | String | Sim | Nome da empresa |
| `support_email` | String | Não | Email de suporte |
| `business_hours` | Object | Não | Configuração de horários (ex: `{"mon-fri": "09:00-18:00"}`) |
| `bot_name` | String | Não | Nome personalizado do bot |
| `bot_welcome_message` | String | Não | Mensagem de boas-vindas do bot |
| `bot_outside_hours_message` | String | Não | Mensagem para fora do horário comercial |
| `custom_instructions` | String | Não | Instruções personalizadas para os agentes IA |
| `products` | Array | Não | Lista de produtos/serviços |
| `teams` | Array[Object] | Não | Definição dos times/departamentos e suas responsabilidades |
| `knowledge_base` | Object | Não | Configuração da base de conhecimento (RAG) |
| `integrations` | Object | Não | Credenciais de integrações (Telegram, WhatsApp) |
| `escalation_contact` | String | Não | ID de contato (chat_id) para escalonamento humano |
| `created_at` | DateTime | Sim | Data de criação |
| `updated_at` | DateTime | Sim | Data de atualização |

---

## 6. agent_states <a name="agent_states"></a>

Armazena o estado momentâneo de cada agente durante o processamento de um ticket (memória de curto prazo).

**Nome da Collection:** `agent_states`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `ticket_id` | String | Sim | ID do ticket e processamento |
| `agent_name` | String | Sim | Nome do agente (`triage`, `router`, etc) |
| `phase` | String | Sim | Fase atual |
| `state` | Object | Sim | Dicionário com dados arbitrários do estado do agente |
| `lock_version` | Int | Sim | Controle de concorrência |
| `updated_at` | DateTime | Sim | Data de atualização |

---

## 7. routing_decisions <a name="routing_decisions"></a>

Registra as decisões tomadas pelo agente roteador (Router Agent).

**Nome da Collection:** `routing_decisions`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `ticket_id` | String | Sim | ID do ticket |
| `agent_name` | String | Sim | Nome do agente (geralmente `router`) |
| `target_team` | String | Sim | Time/Departamento de destino |
| `confidence` | Float | Sim | Nível de confiança da decisão |
| `reasons` | Array[String]| Sim | Lista de justificativas para a decisão |
| `reasoning` | String | Não | Explicação textual da decisão de roteamento |
| `created_at` | DateTime | Sim | Data da decisão |

---

## 8. audit_logs <a name="audit_logs"></a>

Log de auditoria para rastreabilidade de todas as ações importantes do sistema.

**Nome da Collection:** `audit_logs`

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `_id` | ObjectId | Sim | ID interno do MongoDB |
| `ticket_id` | String | Sim | ID do ticket |
| `agent_name` | String | Sim | Agente ou usuário que realizou a ação |
| `operation` | String | Sim | Tipo de operação (ex: `UPDATE_STATUS`, `ESCALATE`) |
| `before` | Object | Não | Estado antes da mudança |
| `after` | Object | Não | Estado depois da mudança |
| `timestamp` | DateTime | Sim | Data e hora exata da ação |
