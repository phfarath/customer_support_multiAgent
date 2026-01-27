# Docker Development Environment Guide

> **Guia completo para desenvolvimento local do Customer Support MultiAgent System usando Docker Compose e MongoDB Atlas**

---

## 📋 Pré-requisitos

### Ferramentas necessárias

- **Docker Desktop** (ou Docker Engine) instalado e rodando
  - [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
- **Docker Compose** v2.x (incluído no Docker Desktop)
- **MongoDB Atlas account** (gratuito)
  - [Criar conta Atlas](https://www.mongodb.com/cloud/atlas/register)
- **Editor de código** (VS Code, PyCharm, etc.)

### Verificar instalação

```bash
docker --version
docker compose version
```

---

## 🗄️ MongoDB Atlas Setup

### Criar cluster gratuito

1. Acesse [MongoDB Atlas](https://cloud.mongodb.com/)
2. Clique em "Create a Database"
3. Selecione **"M0 Free"** (512MB)
4. Escolha região preferencial (ex: AWS São Paulo)
5. Dê um nome ao cluster (ex: `customer-support-dev`)
6. Aguarde a criação (2-3 minutos)

### Configurar acesso

1. **Criar usuário de banco:**
   - Database Access → Add New Database User
   - Username: `customer_support_dev`
   - Password: gere uma senha forte
   - Database User Privileges: Read and write to any database
   - Clique "Add User"

2. **Configurar IP whitelist:**
   - Network Access → Add IP Address
   - Clique "Allow Access from Anywhere" (0.0.0.0/0)
   - ⚠️ **Para produção:** use IP específico

### Obter connection string

1. Cluster → Connect → Connect your application
2. Driver: Python
3. Version: 3.6 or later
4. Copie a connection string:

```
mongodb+srv://customer_support_dev:<password>@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

5. Substitua `<password>` pela senha criada

---

## 🚀 Setup do Ambiente de Desenvolvimento

### 1. Clonar o repositório (se ainda não tiver)

```bash
git clone <seu-repositorio>
cd customer_support_multiAgent
```

### 2. Configurar variáveis de ambiente

Copie o arquivo `.env.example`:

```bash
cp .env.example .env
```

Edite `.env` e preencha:

```env
# MongoDB (Atlas)
MONGODB_URI=mongodb+srv://customer_support_dev:SUA_SENHA@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DATABASE_NAME=customer_support_esc

# OpenAI (necessário para IA)
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_MODEL=gpt-3.5-turbo

# Telegram Bot (opcional - se quiser testar)
TELEGRAM_BOT_TOKEN=seu_bot_token_aqui

# SMTP (opcional - para notificações por email)
SMTP_USERNAME=seu_email@gmail.com
SMTP_PASSWORD=app_password_do_gmail
SMTP_FROM=seu_email@gmail.com
ESCALATION_DEFAULT_EMAIL=seu_email@gmail.com

# API
API_PORT=8000
API_RELOAD=True
DASHBOARD_PORT=8501

# JWT
JWT_SECRET_KEY=uma_chave_secreta_muito_longa_e_aleatoria_no_menos_32_caracteres

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:8501,http://localhost:3000

# Logging
LOG_LEVEL=INFO
```

### 3. Construir imagem de desenvolvimento

```bash
docker compose -f docker-compose.dev.yml build api
```

### 4. Iniciar os serviços

#### Opção A: Apenas API (recomendado para iniciar)

```bash
docker compose -f docker-compose.dev.yml up -d api
```

#### Opção B: API + Dashboard + Telegram Bot

```bash
docker compose -f docker-compose.dev.yml --profile full up -d
```

### 5. Verificar que tudo está rodando

```bash
# Ver status dos containers
docker compose -f docker-compose.dev.yml ps

# Ver logs da API
docker compose -f docker-compose.dev.yml logs -f api

# Testar health check
curl http://localhost:8000/api/health
```

---

## 🌐 Acessar os Serviços

| Serviço | URL |
|---------|-----|
| **API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **Dashboard** | http://localhost:8501 |
| **Health Check** | http://localhost:8000/api/health |

---

## 🔄 Hot-Reload no Desenvolvimento

O ambiente de desenvolvimento tem **hot-reload automático** ativado:

1. Faça alterações nos arquivos Python
2. Salve o arquivo
3. O uvicorn detecta automaticamente e reinicia a API
4. Demora ~2-5 segundos

**Para desativar hot-reload** (mais rápido, mas requires restart manual):

```bash
# Editar .env
API_RELOAD=False

# Reiniciar serviço
docker compose -f docker-compose.dev.yml restart api
```

---

## 📝 Comandos Úteis

### Gestão de Containers

```bash
# Subir serviços
docker compose -f docker-compose.dev.yml up -d

# Subir com todos os serviços (api + dashboard + telegram)
docker compose -f docker-compose.dev.yml --profile full up -d

# Parar serviços
docker compose -f docker-compose.dev.yml down

# Parar e remover volumes (reseta tudo)
docker compose -f docker-compose.dev.yml down -v

# Reiniciar serviço específico
docker compose -f docker-compose.dev.yml restart api

# Reconstruir imagem (após mudanças no Dockerfile.dev)
docker compose -f docker-compose.dev.yml build --no-cache api

# Reconstruir e subir
docker compose -f docker-compose.dev.yml up -d --build api
```

### Logs e Debug

```bash
# Ver logs de todos os serviços
docker compose -f docker-compose.dev.yml logs

# Ver logs de serviço específico
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f telegram-bot
docker compose -f docker-compose.dev.yml logs -f dashboard

# Ver últimos 100 linhas
docker compose -f docker-compose.dev.yml logs --tail=100 api

# Logs com timestamps
docker compose -f docker-compose.dev.yml logs -f --timestamps api
```

### Executar comandos dentro de containers

```bash
# Acessar shell do container API
docker compose -f docker-compose.dev.yml exec api bash

# Executar comando Python
docker compose -f docker-compose.dev.yml exec api python -c "import sys; print(sys.version)"

# Rodar tests
docker compose -f docker-compose.dev.yml exec api pytest

# Ver variáveis de ambiente
docker compose -f docker-compose.dev.yml exec api env | grep MONGODB
```

### Volumes e Arquivos

```bash
# Ver volumes montados
docker compose -f docker-compose.dev.yml config | grep volumes

# Entrar no container para debug
docker compose -f docker-compose.dev.yml exec api vim src/main.py

# Copiar arquivos para o host
docker compose -f docker-compose.dev.yml exec api cat /app/logs/app.log > local_app.log
```

---

## 🐛 Troubleshooting

### Container não inicia

**Sintoma:** `Exited (1)` nos logs

```bash
# Ver logs de erro
docker compose -f docker-compose.dev.yml logs api

# Verificar variáveis de ambiente
docker compose -f docker-compose.dev.yml exec api env
```

**Soluções comuns:**
1. Verifique se `.env` está configurado corretamente
2. Verifique se `MONGODB_URI` está válida
3. Verifique se `OPENAI_API_KEY` está presente

### MongoDB Connection Error

**Sintoma:** `ServerSelectionTimeoutError`

```bash
# Testar conexão MongoDB do host
mongosh "mongodb+srv://user:pass@cluster.mongodb.net/"

# Verificar IP whitelist no Atlas
# Network Access → Ver se 0.0.0.0/0 está presente
```

**Soluções:**
1. Verifique se usuário e senha estão corretos
2. Verifique se IP está whitelistado no Atlas
3. Verifique se cluster está ativo

### Port já em uso

**Sintoma:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

```bash
# Ver qual processo está usando a porta (Mac/Linux)
lsof -i :8000

# Ver no Windows
netstat -ano | findstr :8000

# Mudar a porta no .env
API_PORT=8001
```

**Solução:**
1. Pare o processo que está usando a porta, ou
2. Mude `API_PORT` em `.env` e reinicie

### Hot-reload não funciona

**Sintoma:** Alterações no código não refletem

```bash
# Verificar se API_RELOAD=True
docker compose -f docker-compose.dev.yml exec api env | grep API_RELOAD

# Reiniciar serviço
docker compose -f docker-compose.dev.yml restart api
```

**Solução:**
1. Verifique se `API_RELOAD=True` no `.env`
2. Verifique se volumes estão montados corretamente: `docker compose -f docker-compose.dev.yml config`
3. Tente reiniciar o container

### Memória insuficiente

**Sintoma:** Containers reiniciam constantemente

```bash
# Ver recursos do Docker Desktop
# Settings → Resources → Memory (recomendado: 4GB+)

# Ver uso de memória do container
docker stats customer-support-api-dev
```

**Solução:**
1. Aumente a memória do Docker para 4GB+
2. Pare containers não utilizados
3. Reduza o número de workers no uvicorn

---

## 📊 Monitoramento e Debug

### Ver recursos dos containers

```bash
# Tempo real
docker stats

# Específico
docker stats customer-support-api-dev
```

### Ver eventos do container

```bash
docker compose -f docker-compose.dev.yml events
```

### Inspecionar container

```bash
# Ver configuração completa
docker inspect customer-support-api-dev

# Ver processos rodando
docker compose -f docker-compose.dev.yml exec api ps aux

# Ver portas mapeadas
docker compose -f docker-compose.dev.yml ps
```

### Logs do arquivo local

```bash
# Logs da aplicação
tail -f logs/app.log

# Logs do bot Telegram
tail -f logs/telegram_bot.log
```

---

## 🧪 Testar a Aplicação

### Via cURL

```bash
# Health check
curl http://localhost:8000/api/health

# Criar ticket (exemplo)
curl -X POST http://localhost:8000/api/v1/tickets \
  -H "Content-Type: application/json" \
  -d '{"customer_message": "Meu produto chegou danificado", "channel": "whatsapp"}'
```

### Via Swagger UI

1. Acesse http://localhost:8000/docs
2. Expanda os endpoints
3. Clique em "Try it out"
4. Execute requisições diretamente do browser

### Via Dashboard Streamlit

1. Acesse http://localhost:8501
2. Faça login (se configurado)
3. Visualize métricas e tickets em tempo real

---

## 🚀 Deploy para Produção

Quando estiver pronto para produção, use o ambiente de produção:

```bash
# Usar docker-compose.yml (com MongoDB local ou Atlas)
docker compose -f docker-compose.yml up -d

# Ou deploy para AWS ECS
python scripts/deploy_ecs.py --env production
```

Veja [AWS_ECS_DEPLOYMENT.md](AWS_ECS_DEPLOYMENT.md) para detalhes.

---

## 💡 Dicas de Desenvolvimento

### 1. Usar volumes para persistência

Os volumes são montados automaticamente:
- `./chroma_db` - Base de dados vetorial
- `./logs` - Logs da aplicação
- `./src` - Código fonte (hot-reload)

### 2. Limpar containers antigos

```bash
# Remover containers parados
docker container prune

# Remover imagens não utilizadas
docker image prune -a

# Limpar tudo com cuidado
docker system prune -a
```

### 3. Debug interativo

```bash
# Acessar container com Python shell
docker compose -f docker-compose.dev.yml exec api python

# Executar script de testes
docker compose -f docker-compose.dev.yml exec api python scripts/test_mongodb.py
```

### 4. Variáveis de ambiente temporárias

```bash
# Passar variável sem editar .env
MONGODB_URI="nova_uri" docker compose -f docker-compose.dev.yml up api
```

---

## 📚 Referências

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [MongoDB Atlas Documentation](https://docs.atlas.mongodb.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Dockerfile.dev](../Dockerfile.dev) - Dockerfile de desenvolvimento
- [docker-compose.dev.yml](../docker-compose.dev.yml) - Compose file de desenvolvimento

---

## 🆘 Suporte

Para problemas ou dúvidas:
1. Verifique os logs: `docker compose -f docker-compose.dev.yml logs -f`
2. Consulte o troubleshooting acima
3. Abra uma issue no repositório

---

**Última atualização:** 2026-01-25
**Versão:** 1.0.0
**Autor:** Dev Team
