# Guia de Configuração - Do Zero ao Bot Funcionando

Este guia vai te levar do zero até ter o bot de atendimento funcionando no Telegram, respondendo mensagens com IA e salvando tudo no MongoDB.

## Índice

1. [Pré-requisitos](#1-pré-requisitos)
2. [Escolha seu Caminho](#2-escolha-seu-caminho)
3. [Configuração com Docker (Recomendado)](#3-configuração-com-docker-recomendado)
4. [Configuração Local (Sem Docker)](#4-configuração-local-sem-docker)
5. [Configurar o Bot do Telegram](#5-configurar-o-bot-do-telegram)
6. [Criar Credenciais de Acesso](#6-criar-credenciais-de-acesso)
7. [Testar o Sistema Completo](#7-testar-o-sistema-completo)
8. [Acessar o Dashboard](#8-acessar-o-dashboard)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Pré-requisitos

### Obrigatórios

| Requisito | Versão Mínima | Como Verificar |
|-----------|---------------|----------------|
| Python | 3.10+ | `python --version` |
| Docker | 24.0+ | `docker --version` |
| Docker Compose | 2.0+ | `docker compose version` |
| Git | 2.0+ | `git --version` |

### Contas Necessárias

- **OpenAI Account** - Para os agentes de IA ([platform.openai.com](https://platform.openai.com))
- **Telegram Account** - Para criar o bot ([telegram.org](https://telegram.org))
- **MongoDB Atlas** (opcional) - Banco na nuvem ([mongodb.com/atlas](https://mongodb.com/atlas))

---

## 2. Escolha seu Caminho

| Caminho | Tempo | Melhor Para |
|---------|-------|-------------|
| 🐳 **Docker (Recomendado)** | ~15 min | Desenvolvimento rápido, menos configuração |
| 💻 **Local** | ~30 min | Mais controle, debugging avançado |

**Recomendação:** Use Docker para começar rapidamente.

---

## 3. Configuração com Docker (Recomendado)

### 3.1 Clone o Repositório

```bash
git clone https://github.com/phfarath/customer_support_multiAgent.git
cd customer_support_multiAgent
```

### 3.2 Configure as Variáveis de Ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env
```

Edite o arquivo `.env` com suas credenciais:

```bash
# Abra no seu editor preferido
nano .env   # ou code .env, vim .env
```

**Variáveis OBRIGATÓRIAS que você precisa configurar:**

```env
# 1. OpenAI - Obtenha em https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-proj-sua-chave-aqui

# 2. Telegram - Veja seção 5 para criar o bot
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# 3. MongoDB - Deixe assim para usar o MongoDB local do Docker
MONGODB_URI=mongodb://admin:changeme@mongodb:27017/customer_support?authSource=admin
DATABASE_NAME=customer_support
```

### 3.3 Inicie os Containers

```bash
# Inicia todos os serviços (API + MongoDB + Dashboard)
docker compose up -d

# Verifique se está rodando
docker compose ps
```

Você deve ver:

```
NAME                    STATUS
customer-support-api    Up (healthy)
customer-support-mongo  Up (healthy)
```

### 3.4 Verifique a Saúde do Sistema

```bash
# Teste o endpoint de saúde
curl http://localhost:8000/api/health
```

Resposta esperada:

```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

### 3.5 Veja os Logs

```bash
# Logs da API
docker compose logs -f api

# Logs do MongoDB
docker compose logs -f mongodb
```

**Pule para a [Seção 5](#5-configurar-o-bot-do-telegram) para configurar o Telegram.**

---

## 4. Configuração Local (Sem Docker)

### 4.1 Clone o Repositório

```bash
git clone https://github.com/phfarath/customer_support_multiAgent.git
cd customer_support_multiAgent
```

### 4.2 Crie o Ambiente Virtual

```bash
# Crie o ambiente virtual
python -m venv venv

# Ative o ambiente
# Linux/Mac:
source venv/bin/activate

# Windows:
.\venv\Scripts\activate
```

### 4.3 Instale as Dependências

```bash
pip install -r requirements.txt
```

### 4.4 Configure o MongoDB

**Opção A: MongoDB Local (Docker)**

```bash
# Inicie apenas o MongoDB
docker run -d \
  --name mongodb \
  -p 27017:27017 \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=changeme \
  mongo:7.0
```

**Opção B: MongoDB Atlas (Nuvem)**

1. Acesse [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Crie uma conta gratuita
3. Crie um cluster (Free Tier M0)
4. Em "Database Access", crie um usuário
5. Em "Network Access", adicione seu IP (ou 0.0.0.0/0 para desenvolvimento)
6. Em "Connect", copie a connection string

### 4.5 Configure as Variáveis de Ambiente

```bash
cp .env.example .env
```

Edite o `.env`:

```env
# Se usar MongoDB local (Docker)
MONGODB_URI=mongodb://admin:changeme@localhost:27017/customer_support?authSource=admin

# Se usar MongoDB Atlas
MONGODB_URI=mongodb+srv://seu_usuario:sua_senha@cluster.mongodb.net/?retryWrites=true&w=majority

# OpenAI (obrigatório)
OPENAI_API_KEY=sk-proj-sua-chave-aqui

# Telegram (veja seção 5)
TELEGRAM_BOT_TOKEN=seu_token_aqui

DATABASE_NAME=customer_support
```

### 4.6 Inicie a API

```bash
# Inicie o servidor
python main.py

# Ou com uvicorn diretamente
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4.7 Verifique a Saúde

```bash
curl http://localhost:8000/api/health
```

---

## 5. Configurar o Bot do Telegram

### 5.1 Crie o Bot no BotFather

1. Abra o Telegram e pesquise por **@BotFather**
2. Envie o comando `/newbot`
3. Escolha um **nome** para o bot (ex: "Suporte Empresa")
4. Escolha um **username** único terminando em "bot" (ex: "empresa_suporte_bot")
5. O BotFather vai retornar um **token** como:
   ```
   123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

### 5.2 Configure o Token no .env

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
```

### 5.3 Reinicie a API (se já estiver rodando)

```bash
# Docker
docker compose restart api

# Local
# Ctrl+C e inicie novamente
python main.py
```

### 5.4 Configure o Webhook

O webhook permite que o Telegram envie mensagens para sua API.

**Para Desenvolvimento (usando ngrok):**

```bash
# Instale o ngrok (https://ngrok.com)
# Exponha sua API
ngrok http 8000
```

O ngrok vai mostrar uma URL como: `https://abc123.ngrok.io`

**Configure o webhook:**

```bash
# Primeiro, crie uma API key (veja seção 6)
# Depois configure o webhook

curl -X POST "http://localhost:8000/telegram/webhook/set?webhook_url=https://abc123.ngrok.io/telegram/webhook" \
  -H "X-API-Key: sua_api_key_aqui"
```

**Para Produção (servidor com domínio):**

```bash
curl -X POST "http://localhost:8000/telegram/webhook/set?webhook_url=https://seu-dominio.com/telegram/webhook" \
  -H "X-API-Key: sua_api_key_aqui"
```

### 5.5 Verifique o Webhook

```bash
curl "http://localhost:8000/telegram/webhook/info" \
  -H "X-API-Key: sua_api_key_aqui"
```

Resposta esperada:

```json
{
  "url": "https://seu-dominio.com/telegram/webhook",
  "has_custom_certificate": false,
  "pending_update_count": 0
}
```

---

## 6. Criar Credenciais de Acesso

### 6.1 Criar sua Primeira Empresa (Company)

O sistema é multi-tenant, então primeiro precisamos criar uma empresa:

```bash
# Acesse o container (Docker)
docker compose exec api bash

# Ou localmente, ative o venv
source venv/bin/activate
```

```bash
# Crie a configuração da empresa
python -c "
import asyncio
from src.database import get_collection, COLLECTION_COMPANY_CONFIGS

async def create_company():
    collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    await collection.insert_one({
        'company_id': 'minha_empresa',
        'company_name': 'Minha Empresa',
        'support_email': 'suporte@minhaempresa.com',
        'bot_name': 'Assistente Virtual',
        'bot_welcome_message': 'Olá! Sou o assistente virtual. Como posso ajudar?',
        'custom_instructions': 'Seja cordial e objetivo nas respostas.',
        'products': [
            {'name': 'Produto A', 'description': 'Descrição do produto A'},
            {'name': 'Produto B', 'description': 'Descrição do produto B'}
        ],
        'teams': [
            {'name': 'billing', 'description': 'Questões financeiras'},
            {'name': 'tech', 'description': 'Suporte técnico'},
            {'name': 'general', 'description': 'Dúvidas gerais'}
        ]
    })
    print('✅ Empresa criada com sucesso!')

asyncio.run(create_company())
"
```

### 6.2 Criar API Key

```bash
python scripts/create_initial_api_key.py \
  --company-id minha_empresa \
  --name "Chave de Desenvolvimento"
```

**Saída:**

```
✅ API Key created successfully!

API Key: sk_abc123def456ghi789jkl012mno345pqr678stu901vwx234yz

⚠️  IMPORTANT: Save this key securely. It will NOT be shown again.

Key Details:
  - Key ID: key_xxxxx
  - Company ID: minha_empresa
  - Name: Chave de Desenvolvimento
  - Created: 2024-01-01T00:00:00Z
```

**IMPORTANTE:** Salve esta chave! Ela não será mostrada novamente.

### 6.3 Criar Usuário do Dashboard

```bash
python scripts/create_dashboard_user.py \
  --email admin@minhaempresa.com \
  --password SenhaSegura123! \
  --company-id minha_empresa \
  --full-name "Administrador" \
  --role admin
```

---

## 7. Testar o Sistema Completo

### 7.1 Teste via API

**Criar um ticket:**

```bash
curl -X POST "http://localhost:8000/api/ingest" \
  -H "X-API-Key: sk_sua_chave_aqui" \
  -H "Content-Type: application/json" \
  -d '{
    "external_user_id": "teste_001",
    "channel": "api",
    "subject": "Problema com cobrança",
    "description": "Fui cobrado duas vezes no cartão",
    "metadata": {"source": "teste"}
  }'
```

**Resposta:**

```json
{
  "ticket_id": "TKT-20240101-ABC123",
  "status": "open",
  "message": "Ticket created successfully"
}
```

**Executar o pipeline de IA:**

```bash
curl -X POST "http://localhost:8000/api/pipeline/TKT-20240101-ABC123" \
  -H "X-API-Key: sk_sua_chave_aqui"
```

**Ver o ticket processado:**

```bash
curl "http://localhost:8000/api/tickets/TKT-20240101-ABC123" \
  -H "X-API-Key: sk_sua_chave_aqui"
```

### 7.2 Teste via Telegram

1. Abra o Telegram
2. Pesquise pelo username do seu bot (ex: @empresa_suporte_bot)
3. Clique em "Start" ou envie `/start`
4. O bot vai pedir seu telefone para registro
5. Envie uma mensagem como: "Tive um problema com minha cobrança"
6. O bot deve responder usando IA!

### 7.3 Verificar no MongoDB

```bash
# Acesse o MongoDB
docker compose exec mongodb mongosh -u admin -p changeme

# Selecione o banco
use customer_support

# Veja os tickets criados
db.tickets.find().pretty()

# Veja as interações
db.interactions.find().pretty()

# Saia
exit
```

---

## 8. Acessar o Dashboard

### 8.1 Inicie o Dashboard

```bash
# Docker - já está rodando se usou docker compose up

# Local
streamlit run src/dashboard/app.py
```

### 8.2 Acesse no Navegador

Abra: [http://localhost:8501](http://localhost:8501)

### 8.3 Faça Login

- **Email:** admin@minhaempresa.com (o que você criou)
- **Senha:** SenhaSegura123! (a que você definiu)

### 8.4 Funcionalidades do Dashboard

- **Tickets Escalados:** Veja tickets que precisam de atenção humana
- **Configuração do Bot:** Ajuste mensagens e comportamento
- **Métricas:** Acompanhe o desempenho do atendimento

---

## 9. Troubleshooting

### Problema: "Connection refused" no MongoDB

```bash
# Verifique se o MongoDB está rodando
docker compose ps

# Se não estiver, reinicie
docker compose up -d mongodb
```

### Problema: "Invalid API Key"

```bash
# Verifique se a chave existe
docker compose exec mongodb mongosh -u admin -p changeme --eval "use customer_support; db.api_keys.find().pretty()"
```

### Problema: Bot não responde no Telegram

1. Verifique se o webhook está configurado:
   ```bash
   curl "http://localhost:8000/telegram/webhook/info" \
     -H "X-API-Key: sk_sua_chave"
   ```

2. Verifique os logs:
   ```bash
   docker compose logs -f api
   ```

3. Verifique se o ngrok está rodando (desenvolvimento)

### Problema: "OpenAI API Error"

1. Verifique se a chave está correta no `.env`
2. Verifique se tem créditos na conta OpenAI
3. Verifique os logs:
   ```bash
   docker compose logs api | grep -i openai
   ```

### Problema: Porta 8000 já em uso

```bash
# Encontre o processo
lsof -i :8000

# Mate o processo ou use outra porta
API_PORT=8001 docker compose up -d
```

### Logs Úteis

```bash
# Todos os logs
docker compose logs -f

# Apenas API
docker compose logs -f api

# Apenas erros
docker compose logs api 2>&1 | grep -i error
```

---

## Próximos Passos

Agora que o sistema está funcionando:

1. 📚 **Configure a Base de Conhecimento** - Adicione documentos para melhorar as respostas
   ```bash
   python scripts/ingest_knowledge.py --company-id minha_empresa --file docs/manual.pdf
   ```

2. 🎨 **Personalize o Bot** - Edite as mensagens no Dashboard

3. 📊 **Configure Métricas** - Integre com Sentry para monitoramento

4. 🚀 **Deploy em Produção** - Veja `docs/DEPLOYMENT.md`

---

## Resumo das Portas

| Serviço | Porta | URL |
|---------|-------|-----|
| API | 8000 | http://localhost:8000 |
| Dashboard | 8501 | http://localhost:8501 |
| MongoDB | 27017 | mongodb://localhost:27017 |
| Swagger Docs | 8000 | http://localhost:8000/docs |

---

## Comandos Úteis

```bash
# Iniciar tudo
docker compose up -d

# Parar tudo
docker compose down

# Ver logs
docker compose logs -f

# Reiniciar API
docker compose restart api

# Entrar no container
docker compose exec api bash

# Limpar tudo (CUIDADO: apaga dados)
docker compose down -v
```

---

**Dúvidas?** Abra uma issue no GitHub ou consulte a documentação em `docs/`.
