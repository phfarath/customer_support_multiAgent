# AWS ECS Deployment Guide

> **Guia completo para deploy do Customer Support MultiAgent System em produção na AWS**

---

## 📋 Pré-requisitos

### Ferramentas necessárias
- **AWS CLI** v2.x configurado com credenciais
- **Docker** instalado e rodando
- **Python 3.10+** com boto3: `pip install boto3 python-dotenv`
- **Git** para versionamento

### Recursos AWS necessários
- **IAM Roles:**
  - `ecsTaskExecutionRole` - Para ECS executar tarefas
  - `ecsTaskRole` - Para aplicação acessar recursos AWS
- **VPC** com subnets públicas (ou use script para criar)
- **Conta AWS** com permissões para:
  - ECS, ECR, EC2, ELB, Secrets Manager, CloudWatch

### Verificar AWS CLI
```bash
aws --version
aws sts get-caller-identity  # Verifica credenciais
```

---

## 🚀 Deployment Workflow

### Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│  DEPLOYMENT PIPELINE                                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Setup Infrastructure (one-time)                         │
│     ├─ VPC, Subnets, Security Groups                       │
│     ├─ ECS Cluster                                          │
│     ├─ Application Load Balancer                            │
│     └─ ECS Service                                          │
│                                                             │
│  2. Configure Secrets (one-time)                            │
│     ├─ MongoDB URI                                          │
│     ├─ OpenAI API Key                                       │
│     ├─ JWT Secret                                           │
│     ├─ Telegram Token                                       │
│     └─ SMTP Password                                        │
│                                                             │
│  3. Deploy Application (repeatable)                         │
│     ├─ Build Docker image                                   │
│     ├─ Push to ECR                                          │
│     ├─ Update Task Definition                               │
│     ├─ Update ECS Service                                   │
│     └─ Monitor deployment                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🏗️ Step 1: Setup Infrastructure (One-Time)

### Option A: Create New VPC

```bash
python scripts/deploy_setup_infrastructure.py \
  --env production \
  --region us-east-1 \
  --create-vpc
```

**O que é criado:**
- ✅ VPC (10.0.0.0/16)
- ✅ 2 Public Subnets (multi-AZ)
- ✅ Internet Gateway
- ✅ Route Tables
- ✅ Security Groups (ALB + ECS)
- ✅ ECS Cluster (Fargate)
- ✅ Application Load Balancer
- ✅ Target Group
- ✅ ECS Service (initial)
- ✅ Auto Scaling (1-10 tasks)

**Tempo estimado:** 5-10 minutos

### Option B: Use Existing VPC

```bash
python scripts/deploy_setup_infrastructure.py \
  --env production \
  --region us-east-1 \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-111,subnet-222
```

**Nota:** Subnets devem ser públicas e em diferentes AZs.

### Verificar recursos criados

```bash
# ECS Cluster
aws ecs describe-clusters --clusters customer-support-production

# Load Balancer
aws elbv2 describe-load-balancers --names cs-production

# Service
aws ecs describe-services \
  --cluster customer-support-production \
  --services customer-support-api-production
```

---

## 🔐 Step 2: Configure Secrets (One-Time)

### Option A: Interactive Mode (Recommended)

```bash
python scripts/deploy_setup_secrets.py \
  --env production \
  --region us-east-1 \
  --interactive
```

**Prompts interativos para:**
1. MongoDB URI (MongoDB Atlas ou self-hosted)
2. OpenAI API Key
3. JWT Secret (auto-gerado se vazio)
4. Telegram Bot Token
5. SMTP Password (Gmail app password)

### Option B: From Environment Variables

```bash
# Configurar .env primeiro
cp .env.example .env
nano .env  # Preencher valores

# Importar para Secrets Manager
python scripts/deploy_setup_secrets.py \
  --env production \
  --region us-east-1 \
  --from-env
```

### Secrets criados no AWS Secrets Manager:

| Secret Name | Descrição |
|------------|-----------|
| `customer-support/production/mongodb-uri` | Connection string MongoDB |
| `customer-support/production/openai-key` | OpenAI API Key |
| `customer-support/production/jwt-secret` | JWT signing key |
| `customer-support/production/telegram-token` | Telegram Bot Token |
| `customer-support/production/smtp-password` | Email SMTP password |

### Verificar secrets

```bash
aws secretsmanager list-secrets --region us-east-1 | grep customer-support

aws secretsmanager get-secret-value \
  --secret-id customer-support/production/mongodb-uri \
  --region us-east-1
```

---

## 🚀 Step 3: Deploy Application

### Deploy automático (CI/CD Ready)

```bash
python scripts/deploy_ecs.py \
  --env production \
  --region us-east-1
```

**Pipeline executado:**
1. ✅ Create ECR repository (se não existir)
2. ✅ Build Docker image (multi-stage)
3. ✅ Push image to ECR
4. ✅ Register new ECS Task Definition
5. ✅ Update ECS Service (rolling update)
6. ✅ Monitor deployment até completion
7. ✅ Display service info e logs URL

**Tempo estimado:** 10-15 minutos

### Deploy para outros ambientes

```bash
# Staging
python scripts/deploy_ecs.py --env staging --region us-east-1

# Development
python scripts/deploy_ecs.py --env development --region us-east-1
```

### Deploy com custom cluster/service

```bash
python scripts/deploy_ecs.py \
  --env production \
  --region us-east-1 \
  --cluster my-custom-cluster \
  --service my-custom-service
```

### Verificar deployment

```bash
# Status do serviço
aws ecs describe-services \
  --cluster customer-support-production \
  --services customer-support-api-production

# Tasks rodando
aws ecs list-tasks \
  --cluster customer-support-production \
  --service-name customer-support-api-production

# Logs (CloudWatch)
aws logs tail /ecs/customer-support-production --follow
```

---

## 🔄 Updates e Rollbacks

### Deploy nova versão

Apenas rode o deploy script novamente:

```bash
git pull
python scripts/deploy_ecs.py --env production --region us-east-1
```

**Estratégia de deploy:**
- Rolling update (zero downtime)
- Health checks automáticos
- Circuit breaker (rollback automático em falha)
- 2 min grace period para startup

### Rollback manual

```bash
# Listar task definitions
aws ecs list-task-definitions --family-prefix customer-support-production

# Rollback para versão anterior
aws ecs update-service \
  --cluster customer-support-production \
  --service customer-support-api-production \
  --task-definition customer-support-production:42
```

### Rollback automático

Configurado via **Circuit Breaker** no service:
- Se deployment falhar health checks → rollback automático
- Se tasks crasharem → rollback automático

---

## 📊 Monitoramento e Logs

### CloudWatch Logs

```bash
# Ver logs em tempo real
aws logs tail /ecs/customer-support-production --follow

# Buscar erros
aws logs filter-events \
  --log-group-name /ecs/customer-support-production \
  --filter-pattern "ERROR"

# Logs de container específico
aws logs tail /ecs/customer-support-production --follow \
  --log-stream-prefix api/
```

**Console AWS:**
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups

### CloudWatch Metrics

Métricas automáticas:
- CPU Utilization
- Memory Utilization
- Request Count (ALB)
- Target Response Time
- Unhealthy Host Count

**Criar dashboard:**
```bash
# Via AWS Console: CloudWatch → Dashboards → Create
# Métricas recomendadas:
# - ECS/Service: CPUUtilization, MemoryUtilization
# - ALB: TargetResponseTime, RequestCount, HealthyHostCount
# - Application: Custom metrics via CloudWatch SDK
```

### Health Checks

```bash
# Health check da aplicação
curl http://<ALB-DNS>/api/health

# Target Group health
aws elbv2 describe-target-health \
  --target-group-arn <TARGET-GROUP-ARN>
```

### Alarmes CloudWatch (Recomendado)

```bash
# Alarme: CPU > 80%
aws cloudwatch put-metric-alarm \
  --alarm-name customer-support-high-cpu \
  --alarm-description "Alert when CPU exceeds 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Alarme: Unhealthy targets
aws cloudwatch put-metric-alarm \
  --alarm-name customer-support-unhealthy-targets \
  --metric-name UnHealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold
```

---

## 🔧 Troubleshooting

### Task não inicia (Status: PENDING)

**Causas comuns:**
1. Secrets Manager não acessível
2. ECR image pull failed
3. Falta de capacity (Fargate)

**Debug:**
```bash
# Ver eventos do serviço
aws ecs describe-services \
  --cluster customer-support-production \
  --services customer-support-api-production \
  | jq '.services[0].events[:5]'

# Ver motivo de stopped tasks
aws ecs describe-tasks \
  --cluster customer-support-production \
  --tasks <TASK-ARN> \
  | jq '.tasks[0].stoppedReason'
```

**Soluções:**
- Verificar IAM role `ecsTaskExecutionRole` tem permissões para Secrets Manager
- Verificar se secrets existem: `aws secretsmanager list-secrets`
- Tentar região diferente se Fargate capacity issue

### Health check falhando

**Sintoma:** Tasks reiniciando constantemente

```bash
# Ver logs de health check
aws logs tail /ecs/customer-support-production --follow | grep health
```

**Soluções:**
1. Aumentar `healthCheckGracePeriodSeconds` (padrão: 60s)
2. Verificar se `/api/health` responde 200 localmente
3. Verificar security group permite tráfego do ALB

### Deployment stuck

**Sintoma:** Deployment não progride

```bash
# Forçar novo deployment
aws ecs update-service \
  --cluster customer-support-production \
  --service customer-support-api-production \
  --force-new-deployment

# Ou aumentar deployment timeout no script
```

### Secrets não encontrados

**Erro:** `ResourceNotFoundException` no task

**Soluções:**
1. Verificar nome do secret: `customer-support/{env}/{key}`
2. Verificar região (deve ser mesma do ECS)
3. Verificar IAM role tem permissão `secretsmanager:GetSecretValue`

```bash
# Testar acesso ao secret
aws secretsmanager get-secret-value \
  --secret-id customer-support/production/mongodb-uri
```

### High CPU/Memory

**Ajustar recursos da task:**

Editar `scripts/deploy_ecs.py`:
```python
"cpu": "2048",     # 2 vCPU (era 1024)
"memory": "4096",  # 4 GB (era 2048)
```

Redeploy:
```bash
python scripts/deploy_ecs.py --env production
```

---

## 🎯 Auto Scaling

### Configurado automaticamente

- **Min tasks:** 1
- **Max tasks:** 10
- **Target CPU:** 70%
- **Scale out cooldown:** 60s
- **Scale in cooldown:** 180s

### Ajustar limites

```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/customer-support-production/customer-support-api-production \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 20
```

### Adicionar policy baseada em requests

```bash
aws application-autoscaling put-scaling-policy \
  --policy-name customer-support-request-scaling \
  --service-namespace ecs \
  --resource-id service/customer-support-production/customer-support-api-production \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 1000.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ALBRequestCountPerTarget",
      "ResourceLabel": "app/cs-production/xxx/targetgroup/cs-tg-production/yyy"
    }
  }'
```

---

## 💰 Custos Estimados

### AWS ECS Fargate (us-east-1)

**Task Definition:**
- 1 vCPU, 2 GB RAM
- $0.04048/hour = ~$29/mês (1 task 24/7)

**Scaling (médio):**
- 3 tasks médios = ~$87/mês

**Load Balancer:**
- ALB: $16.20/mês + $0.008/LCU-hour
- Estimado: ~$25/mês (baixo tráfego)

**ECR:**
- Storage: $0.10/GB/mês
- 1GB image = $0.10/mês

**CloudWatch:**
- Logs: $0.50/GB ingestão
- Estimado: $5/mês (logs moderados)

**Total estimado (produção):**
- **1 task:** ~$75/mês
- **3 tasks (avg):** ~$142/mês
- **10 tasks (peak):** ~$320/mês

### Reduzir custos

1. **Usar Fargate Spot** (70% desconto, pode ser interrompido):
```python
# Em deploy_setup_infrastructure.py
defaultCapacityProviderStrategy=[
    {"capacityProvider": "FARGATE_SPOT", "weight": 1, "base": 0}
]
```

2. **Reserved Compute** (1-3 anos, até 50% desconto)

3. **Reduzir logs retention:**
```bash
aws logs put-retention-policy \
  --log-group-name /ecs/customer-support-production \
  --retention-in-days 7  # Padrão: infinito
```

---

## 🔒 Segurança Best Practices

### ✅ Implementado

- [x] Secrets no AWS Secrets Manager (não env vars)
- [x] IAM roles com least privilege
- [x] Security groups restritivos
- [x] Container non-root user
- [x] Image scanning (ECR)
- [x] HTTPS-only (ALB listener)
- [x] VPC isolation
- [x] CloudWatch logging

### 🔧 Configurar manualmente

#### 1. HTTPS com ACM Certificate

```bash
# Requisitar certificado
aws acm request-certificate \
  --domain-name api.seudominio.com \
  --validation-method DNS

# Após validação, adicionar listener HTTPS ao ALB
aws elbv2 create-listener \
  --load-balancer-arn <ALB-ARN> \
  --protocol HTTPS \
  --port 443 \
  --certificates CertificateArn=<CERT-ARN> \
  --default-actions Type=forward,TargetGroupArn=<TG-ARN>

# Redirecionar HTTP → HTTPS
aws elbv2 modify-listener \
  --listener-arn <HTTP-LISTENER-ARN> \
  --default-actions '[{
    "Type": "redirect",
    "RedirectConfig": {
      "Protocol": "HTTPS",
      "Port": "443",
      "StatusCode": "HTTP_301"
    }
  }]'
```

#### 2. WAF (Web Application Firewall)

```bash
# Criar Web ACL
aws wafv2 create-web-acl \
  --name customer-support-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://waf-rules.json

# Associar com ALB
aws wafv2 associate-web-acl \
  --web-acl-arn <WAF-ARN> \
  --resource-arn <ALB-ARN>
```

#### 3. Secrets Rotation

```bash
# Habilitar rotação automática (MongoDB)
aws secretsmanager rotate-secret \
  --secret-id customer-support/production/mongodb-uri \
  --rotation-lambda-arn <LAMBDA-ARN> \
  --rotation-rules AutomaticallyAfterDays=30
```

#### 4. VPC Endpoints (Private ECR/Secrets)

```bash
# ECR VPC Endpoint (reduz custos NAT)
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.us-east-1.ecr.api \
  --route-table-ids rtb-xxx

# Secrets Manager VPC Endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id vpc-xxx \
  --service-name com.amazonaws.us-east-1.secretsmanager \
  --route-table-ids rtb-xxx
```

---

## 🚀 CI/CD Integration

### GitHub Actions

Criar `.github/workflows/deploy-production.yml`:

```yaml
name: Deploy to AWS ECS

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Install dependencies
        run: pip install boto3

      - name: Deploy to ECS
        run: python scripts/deploy_ecs.py --env production --region us-east-1
```

**Secrets necessários no GitHub:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### GitLab CI

Criar `.gitlab-ci.yml`:

```yaml
deploy:production:
  stage: deploy
  image: python:3.10
  before_script:
    - pip install boto3 awscli
    - aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
    - aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
    - aws configure set region us-east-1
  script:
    - python scripts/deploy_ecs.py --env production --region us-east-1
  only:
    - main
```

---

## 📚 Referências

### Scripts criados

| Script | Descrição |
|--------|-----------|
| `deploy_setup_infrastructure.py` | Setup inicial: VPC, ECS, ALB |
| `deploy_setup_secrets.py` | Configurar secrets no Secrets Manager |
| `deploy_ecs.py` | Deploy/update da aplicação |

### Documentação AWS

- [ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [Fargate Pricing](https://aws.amazon.com/fargate/pricing/)
- [Secrets Manager](https://docs.aws.amazon.com/secretsmanager/)
- [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)

### Arquivos de configuração

- `Dockerfile` - Multi-stage production image
- `docker-compose.yml` - Local development
- `docs/DOCKER.md` - Docker setup guide

---

## 🆘 Suporte

### Logs úteis

```bash
# ECS task logs
aws logs tail /ecs/customer-support-production --follow

# ECS service events
aws ecs describe-services --cluster customer-support-production --services customer-support-api-production

# ALB access logs (se habilitado)
aws s3 ls s3://my-alb-logs/customer-support-production/
```

### Comandos de debug

```bash
# Executar comando em task rodando
aws ecs execute-command \
  --cluster customer-support-production \
  --task <TASK-ARN> \
  --container api \
  --interactive \
  --command "/bin/bash"

# Nota: Requer enableExecuteCommand=true no service
```

### Contato

Para issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**Última atualização:** 2026-01-23
**Versão:** 1.0.0
**Autor:** Agent Claude - Backend/Infra Team
