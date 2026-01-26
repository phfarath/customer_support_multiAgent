# Operational Runbook

> **Guia operacional para manutenção e troubleshooting**  
> Sistema MultiAgent Customer Support  
> Última atualização: 2026-01-23

---

## 📋 Índice

- [Visão Geral](#visão-geral)
- [Operações Diárias](#operações-diárias)
- [Monitoramento](#monitoramento)
- [Alertas e Respostas](#alertas-e-respostas)
- [Procedimentos Comuns](#procedimentos-comuns)
- [Troubleshooting](#troubleshooting)
- [Manutenção](#manutenção)
- [Contatos de Emergência](#contatos-de-emergência)

---

## 🎯 Visão Geral

### Componentes do Sistema

| Componente | Função | Criticidade | Uptime Target |
|------------|--------|-------------|---------------|
| **FastAPI** | API REST principal | 🔴 CRÍTICO | 99.9% |
| **Telegram Bot** | Interface com clientes | 🔴 CRÍTICO | 99.5% |
| **Dashboard** | Interface humanos | 🟡 MÉDIO | 99.0% |
| **MongoDB** | Banco de dados | 🔴 CRÍTICO | 99.95% |
| **ChromaDB** | Knowledge base | 🟢 BAIXO | 95.0% |
| **OpenAI API** | LLM inference | 🔴 CRÍTICO | 99.0% |

### URLs Importantes

```bash
# Produção
API: https://api.yourcompany.com
Dashboard: https://dashboard.yourcompany.com
Health: https://api.yourcompany.com/health

# Staging
API: https://api-staging.yourcompany.com
Dashboard: https://dashboard-staging.yourcompany.com

# Desenvolvimento
API: http://localhost:8000
Dashboard: http://localhost:8501
```

### Credenciais

**Localização dos secrets:**
- AWS: Secrets Manager → `prod/customer-support/*`
- Vault local: Ver `1Password` vault "Customer Support Prod"

---

## 📅 Operações Diárias

### Morning Checks (9:00 AM)

```bash
# 1. Verificar health
curl https://api.yourcompany.com/health

# 2. Verificar logs últimas 24h
# AWS CloudWatch ou:
docker logs customer-support-api --since 24h | grep ERROR

# 3. Verificar métricas
# Dashboard de monitoramento (Grafana/CloudWatch)

# 4. Verificar escalations pendentes
# Dashboard Streamlit → Tickets Escalados
```

**Checklist:**
- [ ] API health = OK
- [ ] MongoDB connected
- [ ] Sem erros críticos nos logs
- [ ] Tickets escalados < 10 pendentes
- [ ] Taxa de erro < 1%

### End of Day Review (6:00 PM)

```bash
# 1. Revisar métricas do dia
# - Total de mensagens processadas
# - Taxa de resolução automática
# - Tickets escalados (meta: < 20%)
# - Tempo médio de resposta

# 2. Verificar backups
# MongoDB Atlas: Backups automáticos OK?

# 3. Planejar manutenção
# Atualizações pendentes?
```

---

## 📊 Monitoramento

### Dashboards

**CloudWatch (AWS):**
- ECS Service Metrics (CPU, Memory, Tasks)
- ALB Metrics (Request count, Response time, 5xx errors)
- Custom Metrics (via CloudWatch Logs Insights)

**Application Metrics:**
```bash
# Queries úteis (CloudWatch Logs Insights)

# 1. Error rate últimas 4 horas
fields @timestamp, @message
| filter @message like /ERROR/
| stats count() by bin(5m)

# 2. Endpoint mais lentos
fields @timestamp, duration, endpoint
| filter endpoint != "/health"
| stats avg(duration), max(duration) by endpoint
| sort avg(duration) desc

# 3. OpenAI API failures
fields @timestamp, @message
| filter @message like /OpenAI.*error/
| stats count() by bin(15m)
```

### Key Metrics

| Métrica | Normal | Warning | Critical |
|---------|--------|---------|----------|
| **API Response Time** | < 500ms | 500-1000ms | > 1000ms |
| **Error Rate** | < 0.1% | 0.1-1% | > 1% |
| **CPU Usage** | < 50% | 50-80% | > 80% |
| **Memory Usage** | < 70% | 70-85% | > 85% |
| **MongoDB Connections** | < 50 | 50-90 | > 90 |
| **Ticket Resolution Rate** | > 80% | 60-80% | < 60% |
| **Escalation Rate** | < 20% | 20-30% | > 30% |

### Health Check Endpoint

```bash
# GET /health
curl https://api.yourcompany.com/health

# Response esperado:
{
  "status": "ok",
  "mongodb": "connected",
  "chromadb": "connected",
  "openai": "available",
  "timestamp": "2026-01-23T21:30:00Z",
  "version": "0.1.0"
}

# Status codes:
# 200 - Tudo OK
# 503 - Serviço degradado (MongoDB down, OpenAI unavailable)
```

---

## 🚨 Alertas e Respostas

### Alert: API Down (5xx errors > 50%)

**Severidade:** 🔴 P1 - CRÍTICO

**Ações imediatas:**

```bash
# 1. Verificar health
curl https://api.yourcompany.com/health

# 2. Verificar logs
docker logs customer-support-api --tail 100
# ou AWS:
aws logs tail /ecs/customer-support-api --follow --since 10m

# 3. Verificar MongoDB
mongosh "mongodb+srv://..." --eval "db.adminCommand('ping')"

# 4. Restart service (se necessário)
# Docker:
docker restart customer-support-api
# AWS ECS:
aws ecs update-service --cluster prod --service api --force-new-deployment

# 5. Escalar manualmente se persistir
# ECS: Aumentar desired count de 2 para 4
```

**Escalation:** Se não resolver em 15 min, ligar para Tech Lead

---

### Alert: High Response Time (> 2s sustained)

**Severidade:** 🟡 P2 - ALTO

**Diagnóstico:**

```bash
# 1. Verificar CPU/Memory
docker stats customer-support-api
# ou CloudWatch Metrics

# 2. Verificar slow queries MongoDB
# Atlas: Performance Advisor → Slow Queries

# 3. Verificar OpenAI latency
grep "OpenAI.*duration" logs/app.log | tail -20

# 4. Verificar número de conexões
# MongoDB Atlas: Metrics → Connections
```

**Ações:**

```bash
# Se CPU > 80%: Scale up
aws ecs update-service --cluster prod --service api --desired-count 4

# Se Memory > 85%: Aumentar task memory
# Editar Task Definition: 1024MB → 2048MB

# Se OpenAI lento: Implementar caching (futuro)
# Se MongoDB lento: Verificar índices (scripts/setup_indexes.py)
```

---

### Alert: Escalation Rate > 30%

**Severidade:** 🟡 P2 - ALTO

**Investigação:**

```bash
# 1. Ver tickets escalados recentemente
# Dashboard Streamlit → Filtrar por "Escalated"

# 2. Verificar padrões
# - Todos da mesma empresa?
# - Mesmo tipo de problema?
# - Confidence score baixo em todos?

# 3. Revisar logs do Escalator Agent
grep "EscalatorAgent" logs/app.log | tail -50
```

**Ações:**

```python
# Ajustar thresholds no .env:
ESCALATION_MIN_CONFIDENCE=0.5  # era 0.6 (mais permissivo)
ESCALATION_MAX_INTERACTIONS=3  # era 2 (dar mais chances)

# Restart após mudança:
docker restart customer-support-api
```

**Longo prazo:**
- Melhorar knowledge base (mais documentos)
- Treinar agentes com feedback de humanos
- Revisar company policies

---

### Alert: MongoDB Connection Pool Exhausted

**Severidade:** 🔴 P1 - CRÍTICO

```bash
# 1. Verificar conexões ativas
# MongoDB Atlas: Metrics → Connections

# 2. Restart aplicação (libera pool)
docker restart customer-support-api

# 3. Aumentar maxPoolSize
# Em src/database/connection.py:
# motor.motor_asyncio.AsyncIOMotorClient(
#     uri, maxPoolSize=50  # aumentar de 100 para 200
# )

# 4. Scale MongoDB (se necessário)
# Atlas: Scale cluster para tier superior (M20, M30)
```

---

### Alert: Telegram Bot Not Responding

**Severidade:** 🔴 P1 - CRÍTICO

```bash
# 1. Verificar se bot está rodando
ps aux | grep telegram
docker ps | grep telegram

# 2. Verificar token válido
curl https://api.telegram.org/bot<TOKEN>/getMe

# 3. Verificar webhook (não deve existir em polling mode)
curl https://api.telegram.org/bot<TOKEN>/getWebhookInfo
# Se webhook ativo:
curl https://api.telegram.org/bot<TOKEN>/deleteWebhook

# 4. Restart bot
docker restart telegram-bot
# ou
python run_telegram_bot.py

# 5. Testar manualmente
# Enviar mensagem para o bot no Telegram
```

---

## 🔧 Procedimentos Comuns

### Adicionar Nova Empresa

```bash
# 1. Editar create_test_company.py com dados da empresa
nano create_test_company.py

# 2. Executar script
python create_test_company.py

# 3. Criar API key para empresa
python scripts/create_initial_api_key.py \
  --company-id new_company_id \
  --name "Production Key"

# 4. Criar usuário dashboard
python scripts/create_dashboard_user.py \
  --email admin@newcompany.com \
  --password SecurePass123! \
  --company-id new_company_id \
  --full-name "Admin" \
  --role admin

# 5. Ingest knowledge base
python scripts/ingest_knowledge.py \
  --company-id new_company_id \
  --source ./docs/knowledge_base/company_docs.md

# 6. Configurar Telegram bot (se necessário)
# Dashboard → Company Config → Integrations
```

---

### Atualizar Knowledge Base

```bash
# 1. Preparar documentos
# Formato: Markdown, TXT, ou JSON
# Localização: docs/knowledge_base/<company>/

# 2. Ingest
python scripts/ingest_knowledge.py \
  --company-id <id> \
  --source ./path/to/document.md

# 3. Verificar
# Dashboard Streamlit → Company Config → Knowledge Base
# Ou via API:
curl -H "X-API-Key: sk_xxx" \
  "http://localhost:8000/api/companies/<company_id>"

# 4. Testar
# Enviar pergunta ao bot que deve ser respondida pelo novo documento
```

---

### Revogar API Key Comprometida

```bash
# 1. Listar keys
curl -H "X-API-Key: sk_xxx" http://localhost:8000/api/keys

# 2. Identificar key_id comprometida
# (aparece nos logs ou reportada)

# 3. Revogar
curl -X DELETE \
  -H "X-API-Key: sk_xxx" \
  http://localhost:8000/api/keys/<key_id>

# 4. Criar nova key
curl -X POST \
  -H "X-API-Key: sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{"company_id":"xxx","name":"New Key","permissions":["read","write"]}' \
  http://localhost:8000/api/keys

# 5. Notificar cliente com nova key
```

---

### Reset Password Dashboard User

```bash
# 1. Localizar usuário
python -c "
from pymongo import MongoClient
from src.config import settings
client = MongoClient(settings.MONGODB_URI)
db = client[settings.DATABASE_NAME]
user = db.dashboard_users.find_one({'email': 'user@company.com'})
print(user)
"

# 2. Criar novo hash
python scripts/create_dashboard_user.py \
  --email user@company.com \
  --password NewSecurePass123! \
  --company-id <company_id> \
  --full-name "User Name" \
  --role operator

# (Script vai atualizar se usuário já existe)
```

---

### Deploy Nova Versão

```bash
# 1. Backup atual
docker tag customer-support:latest customer-support:backup-$(date +%Y%m%d)

# 2. Pull nova versão
git pull origin main
docker-compose pull  # ou build

# 3. Restart com zero-downtime (se usar compose)
docker-compose up -d --no-deps --build api

# 4. Verificar logs
docker-compose logs -f api

# 5. Smoke test
curl https://api.yourcompany.com/health
# Enviar mensagem teste no Telegram

# 6. Rollback se necessário (ver DEPLOYMENT.md)
```

---

### Limpar Logs Antigos

```bash
# MongoDB (audit_logs, interactions antigas)
python scripts/cleanup_old_data.py --days 90

# Docker logs
docker logs customer-support-api > /tmp/backup.log
docker container prune -f

# CloudWatch (via console ou CLI)
aws logs delete-log-stream \
  --log-group-name /ecs/customer-support-api \
  --log-stream-name <old-stream>
```

---

## 🐛 Troubleshooting

### Problema: Tickets não sendo processados

**Sintomas:** Mensagens chegam mas nenhum agente responde

**Diagnóstico:**
```bash
# 1. Verificar ingestion
grep "ingest-message" logs/app.log | tail -20

# 2. Verificar pipeline
grep "AgentPipeline" logs/app.log | tail -20

# 3. Verificar MongoDB
# Ver se tickets estão sendo criados:
mongosh "..." --eval "db.tickets.find().sort({created_at:-1}).limit(5)"

# 4. Verificar OpenAI
grep "OpenAI" logs/app.log | tail -20
```

**Soluções:**
- Se OpenAI error: Verificar API key e rate limits
- Se MongoDB error: Verificar conexão e índices
- Se pipeline não roda: Verificar exceptions no código

---

### Problema: Respostas em idioma errado

**Sintomas:** Bot responde em inglês quando deveria ser português

**Causa:** Configuração de company ou prompts dos agentes

**Solução:**
```python
# 1. Verificar company config
curl -H "X-API-Key: sk_xxx" \
  "http://localhost:8000/api/companies/<company_id>"

# 2. Adicionar custom_instructions
{
  "custom_instructions": "Sempre responda em português brasileiro. Seja cordial e profissional."
}

# 3. Update via API
curl -X PUT \
  -H "X-API-Key: sk_xxx" \
  -H "Content-Type: application/json" \
  -d '{"custom_instructions": "Sempre responda em português brasileiro..."}' \
  "http://localhost:8000/api/companies/<company_id>"
```

---

### Problema: ChromaDB corrupted

**Sintomas:** Erros ao query knowledge base

```bash
# 1. Backup atual (se possível)
cp -r chroma_db chroma_db.backup

# 2. Delete collection
rm -rf chroma_db/<collection_name>

# 3. Re-ingest
python scripts/ingest_knowledge.py \
  --company-id <id> \
  --source ./docs/knowledge_base/

# 4. Verificar
python -c "
from src.rag.knowledge_base import KnowledgeBase
kb = KnowledgeBase()
results = kb.query('test query', company_id='xxx')
print(results)
"
```

---

### Problema: Memory leak

**Sintomas:** Memory usage cresce continuamente

**Diagnóstico:**
```bash
# Monitor memory
docker stats customer-support-api --no-stream

# Se memory > 85% sustained:
# 1. Restart imediato
docker restart customer-support-api

# 2. Investigar logs por memory patterns
grep -i "memory\|leak\|gc" logs/app.log

# 3. Verificar ChromaDB cache
# Pode estar crescendo sem limite
```

**Soluções:**
- Implementar LRU cache com limite
- Periodic restarts (cron job diário)
- Scale up memory allocation

---

## 🔄 Manutenção

### Manutenção Programada

**Quando:** Último domingo de cada mês, 2:00 AM - 4:00 AM

**Checklist:**

```bash
# 1. Notificar usuários 48h antes
# (Email, Telegram broadcast)

# 2. Backup completo
docker exec customer-support-api tar -czf /backup/full_$(date +%Y%m%d).tar.gz /app
mongodump --uri="mongodb+srv://..." --out=/backup/mongodb_$(date +%Y%m%d)

# 3. Deploy atualizações
git pull origin main
docker-compose pull
docker-compose up -d --build

# 4. Verificar health
curl https://api.yourcompany.com/health

# 5. Smoke tests
# - Enviar mensagem teste Telegram
# - Criar ticket via API
# - Login no dashboard

# 6. Monitor próximas 2h
watch -n 60 'curl -s https://api.yourcompany.com/health'
```

### Patches de Segurança

**Urgência:** IMEDIATO se CVE crítico

```bash
# 1. Verificar vulnerabilidades
pip install safety
safety check -r requirements.txt

# 2. Atualizar pacotes
pip install --upgrade <package>
pip freeze > requirements.txt

# 3. Rebuild + redeploy
docker-compose build --no-cache
docker-compose up -d

# 4. Verificar
docker logs customer-support-api --tail 100
```

---

## 📞 Contatos de Emergência

### Equipe On-Call

| Turno | Responsável | Telefone | Email |
|-------|-------------|----------|-------|
| **08:00 - 16:00** | Dev Lead | +55 11 99999-0001 | lead@company.com |
| **16:00 - 00:00** | SRE | +55 11 99999-0002 | sre@company.com |
| **00:00 - 08:00** | On-Call | +55 11 99999-0003 | oncall@company.com |

### Escalation Path

1. **L1 - DevOps** (você) - 0-15 min
2. **L2 - Tech Lead** - 15-30 min  
3. **L3 - CTO** - 30+ min (P1 apenas)

### Serviços Externos

| Serviço | Contato | Status Page |
|---------|---------|-------------|
| **MongoDB Atlas** | support@mongodb.com | status.mongodb.com |
| **OpenAI** | help@openai.com | status.openai.com |
| **AWS** | aws-support | status.aws.amazon.com |

---

## 📚 Documentação Adicional

- [DEPLOYMENT.md](./DEPLOYMENT.md) - Guia de deployment
- [ARCHITECTURE.md](../ARCHITECTURE.md) - Arquitetura detalhada
- [TELEGRAM_SETUP.md](./TELEGRAM_SETUP.md) - Setup Telegram
- [MULTI_TENANCY.md](./MULTI_TENANCY.md) - Multi-tenancy guide

---

**Última revisão:** 2026-01-23  
**Autor:** Agent Copilot  
**Versão:** 1.0  
**Status:** Production Ready
