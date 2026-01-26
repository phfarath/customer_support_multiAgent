# Deployment Guide

> **Guia completo de deployment para produção**  
> Sistema MultiAgent Customer Support  
> Última atualização: 2026-01-23

---

## 📋 Índice

- [Pré-requisitos](#pré-requisitos)
- [Opções de Deployment](#opções-de-deployment)
- [Deployment Local](#deployment-local)
- [Deployment com Docker](#deployment-com-docker)
- [Deployment AWS ECS](#deployment-aws-ecs)
- [Configuração de Variáveis](#configuração-de-variáveis)
- [Banco de Dados](#banco-de-dados)
- [Monitoramento](#monitoramento)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Pré-requisitos

### Infraestrutura

| Componente | Requisito | Notas |
|------------|-----------|-------|
| **Python** | 3.11+ | Recomendado: 3.11.7 |
| **MongoDB** | 6.0+ | Atlas recomendado para produção |
| **ChromaDB** | 0.4.22 | Armazenamento vetorial local |
| **RAM** | 2GB+ | Recomendado: 4GB para produção |
| **CPU** | 2 cores | Recomendado: 4 cores para tráfego alto |
| **Disco** | 10GB+ | ChromaDB pode crescer com KB |

### Serviços Externos

- **OpenAI API** - GPT-3.5-turbo ou GPT-4
- **Telegram Bot** - Token via [@BotFather](https://t.me/botfather)
- **SMTP Server** - Gmail, SendGrid, AWS SES
- **MongoDB Atlas** - Cluster M10+ para produção

### Credenciais Necessárias

```bash
✅ OpenAI API Key
✅ Telegram Bot Token
✅ MongoDB Connection String
✅ SMTP credentials (email para escalations)
✅ JWT Secret Key (mínimo 32 caracteres)
```

---

## 🚀 Opções de Deployment

### 1. Local Development
- ✅ Rápido para desenvolvimento
- ✅ Fácil debugging
- ❌ Não escalável
- ❌ Sem redundância

### 2. Docker Compose
- ✅ Reproduzível
- ✅ Isolamento de dependências
- ✅ Fácil rollback
- ⚠️ Single-host (sem HA)

### 3. AWS ECS (Recomendado Produção)
- ✅ Auto-scaling
- ✅ Load balancing
- ✅ Alta disponibilidade
- ✅ Monitoramento integrado
- ❌ Custo maior

---

## 💻 Deployment Local

### Passo 1: Clone e Setup

```bash
git clone <repository-url>
cd customer_support_multiAgent

# Criar virtual environment
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependências
pip install -r requirements.txt
```

### Passo 2: Configurar Variáveis

```bash
cp .env.example .env
nano .env  # ou vim, code, etc
```

**Variáveis críticas:**

```bash
# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=customer_support_prod

# OpenAI
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo

# Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# SMTP (Escalations)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=support@yourcompany.com
SMTP_PASSWORD=your_app_password
SMTP_FROM=support@yourcompany.com

# JWT Security
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS
CORS_ALLOWED_ORIGINS=https://dashboard.yourcompany.com,https://api.yourcompany.com

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

### Passo 3: Setup Banco de Dados

```bash
# Criar índices MongoDB
python scripts/setup_indexes.py

# Criar primeira API Key
python scripts/create_initial_api_key.py \
  --company-id your_company \
  --name "Production API Key"
# Salve o output: sk_xxxxxxxxx

# Criar usuário dashboard
python scripts/create_dashboard_user.py \
  --email admin@yourcompany.com \
  --password SecurePass123! \
  --company-id your_company \
  --full-name "Admin" \
  --role admin

# Criar empresa no sistema
python create_test_company.py  # Editar antes com seus dados
```

### Passo 4: Ingest Knowledge Base (Opcional)

```bash
# Adicionar documentos ao RAG
python scripts/ingest_knowledge.py \
  --company-id your_company \
  --source ./docs/knowledge_base/product_manual.md
```

### Passo 5: Start Services

**Terminal 1 - API:**
```bash
python main.py
# API disponível em http://localhost:8000
# Docs em http://localhost:8000/docs
```

**Terminal 2 - Telegram Bot:**
```bash
python run_telegram_bot.py
# Listening for messages...
```

**Terminal 3 - Dashboard (Opcional):**
```bash
streamlit run src/dashboard/app.py
# Dashboard em http://localhost:8501
```

### Verificar Health

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok", "mongodb": "connected", ...}
```

---

## 🐳 Deployment com Docker

### Dockerfile

O Agent Claude está criando os Dockerfiles. Após disponíveis:

```bash
# Build image
docker build -t customer-support:latest .

# Run container
docker run -d \
  --name customer-support-api \
  --env-file .env \
  -p 8000:8000 \
  -v $(pwd)/chroma_db:/app/chroma_db \
  customer-support:latest
```

### Docker Compose

```bash
# Start todos os serviços
docker-compose up -d

# Logs
docker-compose logs -f api
docker-compose logs -f telegram-bot

# Stop
docker-compose down
```

**Serviços incluídos:**
- `api` - FastAPI (porta 8000)
- `telegram-bot` - Polling bot
- `dashboard` - Streamlit (porta 8501)
- `chroma` - Volume persistente

---

## ☁️ Deployment AWS ECS

**⚠️ Em desenvolvimento pelo Agent Claude**

Arquivos esperados:
- `scripts/deploy_ecs.py` - Deploy automatizado
- `.github/workflows/deploy.yml` - CI/CD
- ECS Task Definitions
- Load Balancer configs

### Arquitetura Recomendada

```
Internet
    │
    ▼
Application Load Balancer (ALB)
    │
    ├─► Target Group: API (porta 8000)
    │   └─► ECS Service: customer-support-api
    │       ├─► Task 1 (Fargate)
    │       ├─► Task 2 (Fargate)
    │       └─► Task N (auto-scaling)
    │
    └─► Target Group: Dashboard (porta 8501)
        └─► ECS Service: customer-support-dashboard
            └─► Task (Fargate)

Telegram Bot (ECS Service - sem ALB)
└─► Task 1 (Fargate) - Polling mode
```

### Recursos AWS

| Recurso | Configuração | Custo Estimado |
|---------|-------------|----------------|
| **ECS Fargate** | 2 tasks x 0.5 vCPU / 1GB RAM | ~$30/mês |
| **ALB** | 1 load balancer | ~$18/mês |
| **MongoDB Atlas** | M10 cluster | ~$57/mês |
| **CloudWatch Logs** | 10GB retention | ~$5/mês |
| **Total** | | **~$110/mês** |

---

## 🔒 Configuração de Variáveis

### Variáveis Obrigatórias

```bash
# Core
MONGODB_URI=<connection-string>
DATABASE_NAME=<db-name>
OPENAI_API_KEY=<sk-proj-xxx>

# Telegram
TELEGRAM_BOT_TOKEN=<bot-token>

# Security
JWT_SECRET_KEY=<min-32-chars>
```

### Variáveis Opcionais

```bash
# SMTP (sem isso, escalations não enviam email)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=<email>
SMTP_PASSWORD=<password>

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100

# Agent Tuning
ESCALATION_MAX_INTERACTIONS=2
ESCALATION_MIN_CONFIDENCE=0.6
ESCALATION_MIN_SENTIMENT=-0.7
ESCALATION_SLA_HOURS=4

# CORS
CORS_ALLOWED_ORIGINS=https://yourdomain.com
```

### Secrets Management

**Desenvolvimento:**
```bash
# .env file (não commitar!)
```

**Docker:**
```bash
# Docker secrets
docker secret create mongodb_uri -
docker secret create openai_key -
```

**AWS ECS:**
```bash
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name prod/customer-support/mongodb-uri \
  --secret-string "mongodb+srv://..."
```

---

## 🗄️ Banco de Dados

### MongoDB Atlas Setup

1. **Criar Cluster**
   - Tier: M10 (production) ou M0 (dev)
   - Region: Mais próxima dos usuários
   - Backup: Enabled

2. **Network Access**
   ```bash
   # Adicionar IPs permitidos
   # Produção: IP do servidor/ECS
   # Dev: 0.0.0.0/0 (temporário)
   ```

3. **Database User**
   ```bash
   Username: app_user
   Password: <strong-password>
   Role: readWrite no database customer_support_prod
   ```

4. **Connection String**
   ```bash
   mongodb+srv://app_user:<password>@cluster.mongodb.net/?retryWrites=true&w=majority
   ```

### Índices Necessários

Executar **antes do primeiro deploy**:

```bash
python scripts/setup_indexes.py
```

**Índices criados:**
- `tickets`: ticket_id (unique), company_id, status, customer_id
- `interactions`: ticket_id, timestamp
- `customers`: external_user_id + company_id (compound unique)
- `agent_states`: ticket_id, agent_name
- `companies`: company_id (unique)
- `api_keys`: key_hash (unique), company_id

### Backup Strategy

**MongoDB Atlas:**
- Backups automáticos (continuous)
- Retention: 7 dias (M10+)
- Point-in-time recovery disponível

**ChromaDB:**
```bash
# Backup manual do diretório
tar -czf chroma_backup_$(date +%Y%m%d).tar.gz chroma_db/
```

---

## 📊 Monitoramento

### Health Checks

**Endpoint:** `GET /health`

```json
{
  "status": "ok",
  "mongodb": "connected",
  "chromadb": "connected",
  "timestamp": "2026-01-23T21:30:00Z"
}
```

**Configurar Uptime Monitoring:**
- UptimeRobot (free)
- AWS CloudWatch Alarms
- Datadog / New Relic

### Logs

**Local:**
```bash
# Logs em stdout
tail -f logs/app.log
```

**Docker:**
```bash
docker logs -f customer-support-api
```

**AWS ECS:**
```bash
# CloudWatch Logs
aws logs tail /ecs/customer-support-api --follow
```

### Métricas Importantes

| Métrica | Threshold | Ação |
|---------|-----------|------|
| **Response Time** | > 2s | Investigar lentidão |
| **Error Rate** | > 5% | Alerta crítico |
| **MongoDB Connections** | > 100 | Aumentar pool |
| **Memory Usage** | > 85% | Scale up |
| **OpenAI API Errors** | > 10/min | Verificar rate limits |

### Sentry Integration

**⚠️ Em desenvolvimento pelo Agent Claude**

```python
# Após implementação:
import sentry_sdk
sentry_sdk.init(
    dsn="https://xxx@sentry.io/xxx",
    environment="production"
)
```

---

## 🔧 Troubleshooting

### API não inicia

```bash
# Verificar variáveis
python -c "from src.config import settings; print(settings.MONGODB_URI)"

# Testar MongoDB
mongosh "mongodb+srv://..."

# Verificar porta
lsof -i :8000
```

### MongoDB Connection Failed

```bash
# Verificar network access no Atlas
# Adicionar IP atual:
curl ifconfig.me
# Adicionar esse IP no Atlas Network Access
```

### Telegram Bot não responde

```bash
# Verificar webhook
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo

# Deletar webhook (se usar polling)
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook

# Verificar token
curl https://api.telegram.org/bot<TOKEN>/getMe
```

### OpenAI Rate Limit

```python
# Implementar backoff (já incluído em openai_client.py)
# Aumentar tier no OpenAI dashboard
# Considerar usar cache para respostas repetidas
```

### ChromaDB Corrupted

```bash
# Backup atual
mv chroma_db chroma_db.backup

# Re-criar collection
python scripts/ingest_knowledge.py --company-id <id> --source <docs>
```

### Memory Leak

```bash
# Monitorar
docker stats customer-support-api

# Restart (zero-downtime com ECS)
aws ecs update-service --cluster <cluster> --service <service> --force-new-deployment
```

---

## 🔄 Rollback Procedure

### Docker

```bash
# Listar versões
docker images customer-support

# Rollback para versão anterior
docker stop customer-support-api
docker run -d --name customer-support-api customer-support:v1.2.0
```

### AWS ECS

```bash
# Via AWS Console:
# ECS > Service > Deployments > Rollback

# Via CLI:
aws ecs update-service \
  --cluster production \
  --service customer-support-api \
  --task-definition customer-support-api:5  # versão anterior
```

---

## 📞 Support

- **Documentação:** [docs/RUNBOOK.md](./RUNBOOK.md)
- **Arquitetura:** [ARCHITECTURE.md](../ARCHITECTURE.md)
- **Issues:** GitHub Issues

---

## ✅ Checklist de Deploy

### Pré-Deploy
- [ ] Variáveis `.env` configuradas
- [ ] MongoDB indexes criados
- [ ] API Key gerada
- [ ] Dashboard user criado
- [ ] Knowledge base ingerida
- [ ] Health check testado localmente

### Deploy
- [ ] Application deployed
- [ ] Health check retorna 200
- [ ] Telegram bot responde
- [ ] Dashboard acessível
- [ ] Logs sem erros críticos

### Pós-Deploy
- [ ] Monitoramento ativo
- [ ] Backups configurados
- [ ] Alertas configurados
- [ ] Documentação atualizada
- [ ] Equipe notificada

---

**Última revisão:** 2026-01-23  
**Autor:** Agent Copilot  
**Versão:** 1.0
