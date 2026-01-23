# Health Checks Guide

> **Comprehensive health monitoring for production deployments**

---

## 📊 Overview

O sistema possui **5 health check endpoints** para diferentes casos de uso:

| Endpoint | Uso | Retorno |
|----------|-----|---------|
| `/api/health` | Load balancers, basic monitoring | Status básico |
| `/api/health/detailed` | Monitoring dashboards, ops teams | Status detalhado de componentes |
| `/api/health/ready` | Kubernetes/ECS readiness probe | Ready para receber tráfego? |
| `/api/health/live` | Kubernetes/ECS liveness probe | Processo está vivo? |
| `/api/health/metrics` | Prometheus/monitoring | Métricas em formato Prometheus |

---

## 🚀 Endpoints

### 1. Basic Health Check

**Endpoint:** `GET /api/health`

**Uso:** Load balancers (ALB Target Group), uptime monitoring

**Retorna:**
```json
{
  "status": "healthy",
  "timestamp": "2026-01-23T12:34:56.789Z",
  "uptime_seconds": 3456.78,
  "version": "1.0.0",
  "environment": "production"
}
```

**HTTP Status:**
- `200 OK` - Serviço está rodando

**Características:**
- ✅ Sem verificações pesadas (resposta rápida)
- ✅ Não requer autenticação
- ✅ Usado por ALB health checks

**Exemplo:**
```bash
curl http://localhost:8000/api/health
```

---

### 2. Detailed Health Check

**Endpoint:** `GET /api/health/detailed`

**Uso:** Monitoring dashboards, troubleshooting, ops teams

**Retorna:**
```json
{
  "status": "healthy",  // "healthy" | "degraded" | "unhealthy"
  "timestamp": "2026-01-23T12:34:56.789Z",
  "uptime_seconds": 3456.78,
  "version": "1.0.0",
  "environment": "production",
  "checks": {
    "mongodb": {
      "status": "up",
      "response_time_ms": 12.34
    },
    "openai": {
      "status": "up",
      "response_time_ms": 5.67,
      "message": "API key configured"
    },
    "chromadb": {
      "status": "up",
      "response_time_ms": 2.34
    },
    "system": {
      "status": "up",
      "details": {
        "cpu_percent": 45.2,
        "memory_percent": 62.5,
        "memory_available_mb": 1234.56,
        "disk_percent": 35.0,
        "disk_free_gb": 89.12
      }
    }
  }
}
```

**HTTP Status:**
- `200 OK` - Healthy ou degraded (ainda aceitando tráfego)
- `503 Service Unavailable` - Unhealthy (componente crítico down)

**Status de Componentes:**

| Component | Status | Significado |
|-----------|--------|-------------|
| **mongodb** | `up` | Conectado e respondendo rápido (< 500ms) |
| | `degraded` | Conectado mas lento (> 500ms) |
| | `down` | Sem conexão |
| **openai** | `up` | API key configurada |
| | `down` | API key não configurada ou inválida |
| **chromadb** | `up` | Diretório existe e acessível |
| | `degraded` | Problemas de acesso |
| **system** | `up` | Recursos normais (CPU < 70%, Memory < 80%, Disk < 80%) |
| | `degraded` | Recursos altos (70-90%) |
| | `down` | Recursos críticos (> 90%) |

**Exemplo:**
```bash
curl http://localhost:8000/api/health/detailed
```

---

### 3. Readiness Probe

**Endpoint:** `GET /api/health/ready`

**Uso:** Kubernetes/ECS readiness probe, deployment automation

**Retorna:**
```json
{
  "status": "ready"
}
```

ou

```json
{
  "status": "not_ready",
  "reason": "MongoDB unavailable"
}
```

**HTTP Status:**
- `200 OK` - Ready (pode receber tráfego)
- `503 Service Unavailable` - Not ready (não enviar tráfego)

**Verificações:**
- ✅ MongoDB conectado (crítico)

**Quando usar:**
- Deployment rolling updates (ECS)
- Kubernetes readiness probe
- Waiting for dependencies antes de adicionar ao load balancer

**Exemplo - Docker Compose:**
```yaml
services:
  api:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health/ready"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 40s
```

**Exemplo - ECS Task Definition:**
```json
{
  "healthCheck": {
    "command": [
      "CMD-SHELL",
      "curl -f http://localhost:8000/api/health/ready || exit 1"
    ],
    "interval": 30,
    "timeout": 5,
    "retries": 3,
    "startPeriod": 60
  }
}
```

---

### 4. Liveness Probe

**Endpoint:** `GET /api/health/live`

**Uso:** Kubernetes/ECS liveness probe

**Retorna:**
```json
{
  "status": "alive"
}
```

**HTTP Status:**
- `200 OK` - Processo está vivo

**Quando usar:**
- Detectar deadlocks
- Detectar processos travados
- Decidir se deve reiniciar container

**Diferença entre Readiness e Liveness:**
- **Readiness:** Pode receber tráfego? (dependências OK?)
- **Liveness:** Processo está vivo? (não travado?)

**Exemplo - Kubernetes:**
```yaml
livenessProbe:
  httpGet:
    path: /api/health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /api/health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

---

### 5. Prometheus Metrics

**Endpoint:** `GET /api/health/metrics`

**Uso:** Prometheus scraper, Grafana, monitoring tools

**Retorna (Prometheus text format):**
```
# HELP service_uptime_seconds Service uptime in seconds
# TYPE service_uptime_seconds gauge
service_uptime_seconds 3456.78

# HELP service_health_status Overall service health (1=healthy, 0=unhealthy)
# TYPE service_health_status gauge
service_health_status 1

# HELP component_health_status Component health status (1=up, 0.5=degraded, 0=down)
# TYPE component_health_status gauge
component_health_status{component="mongodb"} 1
component_health_status{component="openai"} 1
component_health_status{component="chromadb"} 1
component_health_status{component="system"} 1

# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent 45.2

# HELP system_memory_percent Memory usage percentage
# TYPE system_memory_percent gauge
system_memory_percent 62.5

# HELP system_disk_percent Disk usage percentage
# TYPE system_disk_percent gauge
system_disk_percent 35.0
```

**Métricas disponíveis:**
- `service_uptime_seconds` - Uptime do serviço
- `service_health_status` - Status geral (1=healthy, 0=unhealthy)
- `component_health_status{component="X"}` - Status por componente
- `system_cpu_percent` - CPU usage
- `system_memory_percent` - Memory usage
- `system_disk_percent` - Disk usage

**Prometheus Configuration:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'customer-support'
    scrape_interval: 15s
    static_configs:
      - targets: ['customer-support-api:8000']
    metrics_path: '/api/health/metrics'
```

---

## 🎯 Use Cases

### AWS ECS/Fargate

**Target Group Health Check:**
```hcl
# terraform
resource "aws_lb_target_group" "api" {
  health_check {
    enabled             = true
    path                = "/api/health"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200"
  }
}
```

**Task Definition Health Check:**
```json
{
  "healthCheck": {
    "command": [
      "CMD-SHELL",
      "curl -f http://localhost:8000/api/health/ready || exit 1"
    ],
    "interval": 30,
    "timeout": 5,
    "retries": 3,
    "startPeriod": 60
  }
}
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: customer-support-api
spec:
  template:
    spec:
      containers:
      - name: api
        image: customer-support:latest
        ports:
        - containerPort: 8000

        # Liveness: Restart if unhealthy
        livenessProbe:
          httpGet:
            path: /api/health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3

        # Readiness: Remove from service if not ready
        readinessProbe:
          httpGet:
            path: /api/health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 2
```

### Uptime Monitoring (UptimeRobot, Pingdom)

```
Monitor URL: https://api.yourcompany.com/api/health
Method: GET
Interval: 5 minutes
Expected: 200 OK
Alert if down: 2 times consecutively
```

### Grafana Dashboard

**Query 1 - Service Uptime:**
```promql
service_uptime_seconds
```

**Query 2 - Component Health:**
```promql
component_health_status
```

**Query 3 - System Resources:**
```promql
system_cpu_percent
system_memory_percent
system_disk_percent
```

**Alert Rule - MongoDB Down:**
```promql
component_health_status{component="mongodb"} < 1
```

---

## 🔧 Configuration

### System Metrics (Optional)

Para habilitar métricas de sistema (CPU, memory, disk), instale `psutil`:

```bash
pip install psutil
```

Se `psutil` não estiver instalado, métricas de sistema retornam:
```json
{
  "status": "up",
  "message": "psutil not installed, metrics unavailable"
}
```

### Thresholds

**MongoDB Response Time:**
- < 100ms: ✅ Bom
- 100-500ms: ✅ Aceitável
- > 500ms: ⚠️ Degraded (high latency)

**System Resources:**
- < 70%: ✅ Normal
- 70-90%: ⚠️ Degraded
- > 90%: ❌ Critical (unhealthy)

**Customizar thresholds:**
```python
# src/api/health_routes.py

async def _check_mongodb() -> ComponentHealth:
    # ...
    if response_time > 1000:  # Aumentar threshold para 1s
        return ComponentHealth(status="degraded", ...)
```

---

## 🐛 Troubleshooting

### Health check retorna 503

**Causa:** Componente crítico está down

**Debug:**
```bash
# Ver status detalhado
curl http://localhost:8000/api/health/detailed | jq

# Verificar MongoDB
curl http://localhost:8000/api/health/detailed | jq '.checks.mongodb'

# Verificar sistema
curl http://localhost:8000/api/health/detailed | jq '.checks.system'
```

**Soluções:**
1. **MongoDB down:** Verificar connection string, firewall, credenciais
2. **High CPU/Memory:** Escalar verticalmente ou adicionar réplicas
3. **Disk full:** Limpar logs, aumentar volume

### Readiness probe falha constantemente

**Causa:** MongoDB não está acessível durante startup

**Solução:** Aumentar `initialDelaySeconds` e `startPeriod`

```yaml
# ECS
"startPeriod": 90  # Era 60, aumentar para 90

# Kubernetes
readinessProbe:
  initialDelaySeconds: 20  # Era 10
```

### Load balancer marca targets como unhealthy

**Causa 1:** Health check path incorreto

**Verificar:**
```bash
# Testar localmente
curl http://task-ip:8000/api/health

# Ver logs ECS
aws logs tail /ecs/customer-support-production --follow
```

**Causa 2:** Security group não permite tráfego do ALB

**Verificar:**
- Security group do ECS task permite porta 8000 do ALB
- ALB consegue acessar tasks nas subnets

---

## 📊 Monitoring Best Practices

### 1. Use múltiplos endpoints

- **ALB:** `/api/health` (básico, rápido)
- **Container:** `/api/health/ready` (com dependências)
- **Monitoring:** `/api/health/detailed` (completo)

### 2. Configure alertas

**Prometheus AlertManager:**
```yaml
groups:
  - name: customer-support
    rules:
      - alert: ServiceDown
        expr: component_health_status{component="mongodb"} < 1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "MongoDB is down"

      - alert: HighCPU
        expr: system_cpu_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"
```

### 3. Dashboard de saúde

**Grafana:**
```json
{
  "title": "Service Health",
  "panels": [
    {
      "title": "Component Status",
      "targets": [
        {
          "expr": "component_health_status",
          "legendFormat": "{{component}}"
        }
      ]
    },
    {
      "title": "System Resources",
      "targets": [
        {
          "expr": "system_cpu_percent"
        },
        {
          "expr": "system_memory_percent"
        }
      ]
    }
  ]
}
```

### 4. Log de health checks

**CloudWatch Insights Query:**
```
fields @timestamp, @message
| filter @message like /health/
| stats count() by bin(5m)
```

---

## 🚀 Production Checklist

- [ ] `/api/health` configurado no ALB Target Group
- [ ] `/api/health/ready` usado em ECS healthCheck
- [ ] Prometheus scraping `/api/health/metrics`
- [ ] Grafana dashboard criado
- [ ] Alertas configurados (MongoDB down, High CPU)
- [ ] Uptime monitoring externo (UptimeRobot)
- [ ] Thresholds ajustados para produção
- [ ] `psutil` instalado para métricas de sistema
- [ ] Security groups permitem health checks

---

**Última atualização:** 2026-01-23
**Versão:** 1.0.0
**Autor:** Agent Claude - Backend/Infra Team
