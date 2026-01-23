# TODO - Active Tasks

> **Tarefas ativas com ownership por agent**
> Última atualização: 2026-01-23

---

## 🔵 Claude (Agent 1) - Backend/Infra

| Task | File(s) | Status | Priority | Est. |
|------|---------|--------|----------|------|
| Dockerfile + docker-compose | `Dockerfile`, `docker-compose.yml` | ⏳ Pending | HIGH | 5h |
| AWS ECS deployment config | `scripts/deploy_*.py` | ⏳ Pending | HIGH | 6h |
| Sentry integration | `src/utils/monitoring.py` | ⏳ Pending | MEDIUM | 2h |
| Health checks deep | `src/api/health_routes.py` | ⏳ Pending | MEDIUM | 2h |
| Circuit breaker OpenAI | `src/utils/circuit_breaker.py` | ⏳ Pending | MEDIUM | 2h |

---

## 🟢 Codex (Agent 2) - Testing/Quality

| Task | File(s) | Status | Priority | Est. |
|------|---------|--------|----------|------|
| Pytest suite - agents | `tests/unit/test_agents.py` | ⏳ Pending | HIGH | 4h |
| Pytest suite - routes | `tests/unit/test_routes.py` | ⏳ Pending | HIGH | 4h |
| Pytest suite - pipeline | `tests/unit/test_pipeline.py` | ⏳ Pending | HIGH | 3h |
| E2E integration tests | `tests/integration/*` | ⏳ Pending | HIGH | 4h |
| Coverage report setup | `pytest.ini`, `pyproject.toml` | ⏳ Pending | MEDIUM | 1h |

---

## 🟣 Copilot (Agent 3) - Docs/Features

| Task | File(s) | Status | Priority | Est. |
|------|---------|--------|----------|------|
| DEPLOYMENT.md | `docs/DEPLOYMENT.md` | ✅ Completed | HIGH | 3h |
| RUNBOOK.md | `docs/RUNBOOK.md` | ✅ Completed | HIGH | 2h |
| Fix Bug #2: Business hours | `src/utils/business_hours.py` | ✅ Completed | MEDIUM | 2h |
| Timeouts HTTP clients | `src/utils/http_client.py` | ⏳ Pending | MEDIUM | 1h |

---

## 📊 Status Legend

| Symbol | Meaning |
|--------|---------|
| ⏳ | Pending |
| 🔄 | In Progress |
| ✅ | Completed |
| ❌ | Blocked |

---

## 🔒 Locked Files

| File | Owner | Until | Reason |
|------|-------|-------|--------|
| *Nenhum arquivo lockado* | — | — | — |

---

## 📝 Notes

- PRs: por **feature completa** (não diário)
- Sync: `git merge origin/dev_integration` antes de iniciar
- Conflitos: Verificar seção "Locked Files" antes de editar arquivos compartilhados
