# Docker Setup Guide

> **Guia completo para executar o Customer Support MultiAgent System com Docker**

---

## 📋 Pré-requisitos

- Docker Engine 20.10+
- Docker Compose V2
- 4GB RAM mínimo (recomendado 8GB)
- 10GB espaço em disco

---

## 🚀 Quick Start

### 1. Configurar variáveis de ambiente

```bash
# Copiar arquivo de exemplo
cp .env.docker .env

# Editar com suas credenciais
nano .env  # ou vim, code, etc
```

**Variáveis obrigatórias:**
- `OPENAI_API_KEY` - Sua chave da OpenAI API
- `TELEGRAM_BOT_TOKEN` - Token do bot Telegram (do @BotFather)
- `JWT_SECRET_KEY` - String aleatória de 32+ caracteres
- `MONGO_ROOT_PASSWORD` - Senha do MongoDB (produção)

### 2. Iniciar serviços (Produção - API + MongoDB)

```bash
docker-compose up -d
```

Isso inicia:
- ✅ MongoDB
- ✅ FastAPI (porta 8000)

### 3. Verificar status

```bash
# Ver logs
docker-compose logs -f api

# Verificar health
curl http://localhost:8000/api/health

# Listar containers
docker-compose ps
```

### 4. Acessar a aplicação

- **API Docs (Swagger):** http://localhost:8000/docs
- **API:** http://localhost:8000
- **Health Check:** http://localhost:8000/api/health

---

## 🛠️ Perfis de Execução

### Modo Produção (padrão)
Apenas API + MongoDB

```bash
docker-compose up -d
```

### Modo Desenvolvimento (com Telegram Bot e Dashboard)

```bash
docker-compose --profile dev up -d
```

Inicia:
- MongoDB
- FastAPI API
- Telegram Bot (polling mode)
- Streamlit Dashboard (porta 8501)

**Acessar Dashboard:** http://localhost:8501

### Modo Completo (todos os serviços)

```bash
docker-compose --profile full up -d
```

---

## 📦 Gerenciamento de Containers

### Parar serviços

```bash
docker-compose down
```

### Parar e remover volumes (⚠️ perde dados)

```bash
docker-compose down -v
```

### Reiniciar um serviço específico

```bash
docker-compose restart api
```

### Ver logs de um serviço

```bash
docker-compose logs -f api
docker-compose logs -f mongodb
```

### Executar comandos dentro do container

```bash
# Shell interativo
docker-compose exec api bash

# Comando único
docker-compose exec api python scripts/ingest_knowledge.py
```

---

## 🔧 Inicialização e Scripts

### Criar primeira API Key

```bash
docker-compose exec api python scripts/create_initial_api_key.py \
  --company-id "empresa_001" \
  --name "Production Key"
```

### Criar usuário do Dashboard

```bash
docker-compose exec api python scripts/create_dashboard_user.py \
  --email admin@empresa.com \
  --password SenhaSegura123! \
  --company-id empresa_001 \
  --full-name "Admin User"
```

### Configurar indexes do MongoDB

```bash
docker-compose exec api python scripts/setup_indexes.py
```

### Ingerir documentos no RAG

```bash
docker-compose exec api python scripts/ingest_knowledge.py \
  --company-id empresa_001 \
  --file docs/knowledge_base/produto_info.txt
```

---

## 🗄️ Persistência de Dados

### Volumes criados

```bash
# Listar volumes
docker volume ls | grep customer-support

# Inspecionar volume
docker volume inspect customer-support-mongodb-data
```

**Volumes:**
- `customer-support-mongodb-data` - Dados do MongoDB
- `customer-support-mongodb-config` - Configuração do MongoDB
- `./chroma_db` - Vector database (bind mount)
- `./logs` - Logs da aplicação (bind mount)

### Backup do MongoDB

```bash
# Backup
docker-compose exec mongodb mongodump \
  --username admin \
  --password changeme \
  --authenticationDatabase admin \
  --db customer_support_esc \
  --out /data/backup

# Copiar para host
docker cp customer-support-mongodb:/data/backup ./mongodb-backup
```

### Restore do MongoDB

```bash
# Copiar backup para container
docker cp ./mongodb-backup customer-support-mongodb:/data/backup

# Restore
docker-compose exec mongodb mongorestore \
  --username admin \
  --password changeme \
  --authenticationDatabase admin \
  --db customer_support_esc \
  /data/backup/customer_support_esc
```

---

## 🔍 Troubleshooting

### API não inicia

**Sintoma:** Container reiniciando constantemente

```bash
# Ver logs
docker-compose logs api

# Verificar variáveis de ambiente
docker-compose exec api env | grep MONGODB_URI
```

**Soluções:**
1. Verificar se MongoDB está healthy: `docker-compose ps`
2. Conferir `.env` - credenciais corretas
3. Verificar portas em uso: `lsof -i :8000`

### MongoDB não conecta

**Sintoma:** `MongoServerError: Authentication failed`

```bash
# Reiniciar com volumes limpos
docker-compose down -v
docker-compose up -d

# Verificar senha no .env
echo $MONGO_ROOT_PASSWORD
```

### Health check falhando

**Sintoma:** Container unhealthy

```bash
# Testar manualmente
docker-compose exec api curl http://localhost:8000/api/health

# Ver logs detalhados
docker-compose logs -f api
```

**Soluções:**
1. Aumentar `start_period` no health check
2. Verificar se OpenAI API key está válida
3. Conferir conectividade com MongoDB

### Permissões de arquivos

**Sintoma:** `Permission denied` ao acessar `chroma_db/` ou `logs/`

```bash
# Corrigir ownership (Linux/Mac)
sudo chown -R 1000:1000 chroma_db logs

# Alternativa: rodar como root (não recomendado)
# Editar Dockerfile: USER root
```

### Porta já em uso

**Sintoma:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

```bash
# Ver o que está usando a porta
lsof -i :8000

# Mudar porta no .env
echo "API_PORT=8001" >> .env
docker-compose up -d
```

---

## 🏗️ Build e Desenvolvimento

### Rebuild da imagem após mudanças

```bash
# Rebuild sem cache
docker-compose build --no-cache api

# Rebuild e restart
docker-compose up -d --build
```

### Desenvolvimento local (sem Docker)

Caso queira rodar localmente para debug:

```bash
# Apenas MongoDB no Docker
docker-compose up -d mongodb

# Aplicação local
export MONGODB_URI=mongodb://admin:changeme@localhost:27017/customer_support_esc?authSource=admin
python main.py
```

### Multi-stage build otimizado

O Dockerfile usa **multi-stage build**:

**Estágio 1 (builder):**
- Instala dependências de compilação
- Cria virtual environment
- Instala pacotes Python

**Estágio 2 (runtime):**
- Imagem mínima (slim)
- Copia apenas venv
- Usuário não-root (appuser)
- Healthcheck configurado

**Tamanho da imagem:** ~800MB (vs ~1.5GB single-stage)

---

## 🔐 Segurança em Produção

### Checklist de segurança

- [ ] Alterar `MONGO_ROOT_PASSWORD` (não usar "changeme")
- [ ] Gerar `JWT_SECRET_KEY` aleatório (32+ chars)
- [ ] Configurar `CORS_ALLOWED_ORIGINS` específicos (não wildcard)
- [ ] Usar secrets manager (AWS Secrets, Vault)
- [ ] Configurar TLS/SSL (nginx reverse proxy)
- [ ] Limitar acesso ao MongoDB (não expor porta 27017)
- [ ] Rotacionar API keys periodicamente
- [ ] Habilitar Sentry para monitoramento

### Usar Docker Secrets (produção)

```bash
# Criar secret
echo "sk-abc123..." | docker secret create openai_api_key -

# docker-compose.yml (modo swarm)
services:
  api:
    secrets:
      - openai_api_key
    environment:
      OPENAI_API_KEY_FILE: /run/secrets/openai_api_key

secrets:
  openai_api_key:
    external: true
```

### Não expor MongoDB publicamente

```yaml
# docker-compose.yml - remover ports em produção
services:
  mongodb:
    # ports:
    #   - "27017:27017"  # ❌ Comentar em produção
```

---

## 📊 Monitoramento

### Verificar recursos

```bash
# Uso de CPU/RAM
docker stats

# Logs com timestamp
docker-compose logs -f --timestamps api

# Apenas erros
docker-compose logs api 2>&1 | grep ERROR
```

### Health checks

```bash
# API
curl http://localhost:8000/api/health

# MongoDB
docker-compose exec mongodb mongosh \
  --username admin \
  --password changeme \
  --authenticationDatabase admin \
  --eval "db.adminCommand('ping')"
```

---

## 🚀 Deploy em Produção

### AWS ECS (ver DEPLOYMENT.md)

O deploy em AWS ECS está documentado em:
- `docs/DEPLOYMENT.md` - Configuração ECS
- `scripts/deploy_ecs.py` - Script automatizado

### Docker Swarm (alternativa)

```bash
# Inicializar swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml customer-support

# Escalar serviço
docker service scale customer-support_api=3
```

---

## 📚 Referências

- **Dockerfile:** Configuração multi-stage otimizada
- **docker-compose.yml:** Orquestração de serviços
- **.dockerignore:** Arquivos excluídos do build
- **.env.docker:** Template de variáveis de ambiente

**Documentação adicional:**
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)

---

**Última atualização:** 2026-01-23
**Autor:** Agent Claude - Backend/Infra Team
