# Agent Coordination System

> **Documento de coordenação para 3 coding agents trabalhando em paralelo**
> Última atualização: 2026-01-23

---

## 🎯 Visão Geral

Sistema de coordenação para **Claude**, **Codex**, e **Copilot** trabalhando simultaneamente usando **git worktrees**.

### Estrutura

```
worktrees/
├── agent-claude/    → feat/agent-claude   (Backend/Infra)
├── agent-codex/     → feat/agent-codex    (Testing)
└── agent-copilot/   → feat/agent-copilot  (Docs/Features)

Integration: Todos fazem PR → dev_integration → main
```

---

## 🔵 Agent Claude - Backend/Infra

**Responsabilidade:** Deployment, DevOps, Core infrastructure

**Tarefas designadas:**
- Dockerfile + docker-compose (5h)
- AWS ECS deployment config (6h)
- Sentry integration (2h)
- Health checks + Circuit breaker (4h)

**Arquivos exclusivos:**
- `Dockerfile`, `docker-compose.yml`
- `scripts/deploy_*.py`
- `src/utils/circuit_breaker.py`
- `.github/workflows/`

**Worktree:** `/Users/phfarath/Library/Mobile Documents/com~apple~CloudDocs/Pessoal-PF/worktrees/agent-claude`

---

## 🟢 Agent Codex - Testing/Quality

**Responsabilidade:** Testes, qualidade de código, coverage

**Tarefas designadas:**
- Pytest suite completa (15h)
- Coverage 70%+
- Testes de integração E2E

**Arquivos exclusivos:**
- `tests/**/*`
- `conftest.py`
- `pytest.ini` / `pyproject.toml` (seção test)

**Worktree:** `/Users/phfarath/Library/Mobile Documents/com~apple~CloudDocs/Pessoal-PF/worktrees/agent-codex`

---

## 🟣 Agent Copilot - Docs/Features

**Responsabilidade:** Documentação e features menores

**Tarefas designadas:**
- `DEPLOYMENT.md` + `RUNBOOK.md` (5h)
- Fix Bug #2: Business hours (2h)
- Timeouts em HTTP clients (1h)

**Arquivos exclusivos:**
- `docs/**/*`
- `README.md`
- `src/utils/business_hours.py`

**Worktree:** `/Users/phfarath/Library/Mobile Documents/com~apple~CloudDocs/Pessoal-PF/worktrees/agent-copilot`

---

## 🔒 Locked Files (Avoid Conflicts)

| File | Owner | Until | Reason |
|------|-------|-------|--------|
| *Nenhum arquivo lockado no momento* | | | |

### Como Adicionar Lock

Antes de editar arquivo compartilhado, adicione à tabela acima com:
- **File:** path relativo
- **Owner:** Nome do agent
- **Until:** Data/hora estimada de término
- **Reason:** Breve descrição

---

## 📋 Workflow

### 1. Antes de Começar
```bash
cd /path/to/worktree
git fetch origin
git merge origin/dev_integration --no-edit
```

### 2. Durante o Trabalho
- Commits frequentes com mensagens descritivas
- Verificar locks antes de editar arquivos compartilhados
- Atualizar `TODO.md` ao iniciar/completar tarefas

### 3. Ao Completar Feature
```bash
git push origin feat/agent-X
# Criar PR: feat/agent-X → dev_integration
```

### 4. Sync Após Merge (outros agents)
```bash
git fetch origin
git merge origin/dev_integration --no-edit
```

---

## ⚠️ Protocolo Anti-Conflito

### Arquivos NUNCA Compartilhados
Cada agent só edita seus arquivos exclusivos listados acima.

### Arquivos Compartilhados (Requer Lock)
- `ARCHITECTURE.md`
- `AI_INSTRUCTIONS.md`
- `requirements.txt`
- `main.py`
- `src/config.py`

### Resolução de Conflitos
1. **Primeiro a declarar vence** - Quem adicionar lock primeiro edita
2. **Dividir por função** - Se possível, editar funções diferentes
3. **Sequencial** - Agent A termina → Agent B começa

---

## 📞 Comunicação

Atualizações de status devem ser feitas em:
- `TODO.md` - Status de tarefas
- `AGENT_COORDINATION.md` - Locks de arquivos

PRs: Frequência **por feature completa** (não diária)
