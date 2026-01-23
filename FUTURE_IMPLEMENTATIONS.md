# Future Implementations

> **Backlog de features organizadas por versão**
> Baseado no roadmap de `ARCHITECTURE.md`
> Última atualização: 2026-01-23

---

## V1.0 - MVP Production-Ready (Semana 3)

### 🐛 Bugs Pendentes
- [ ] Fix Bug #2: Implementar business hours (2h) → **Copilot**
- [ ] Chamar ensure_indexes() no startup (15min)
- [ ] Adicionar timeouts em HTTP clients (1h) → **Copilot**

### 🏗️ Infraestrutura
- [ ] Dockerfile + docker-compose (5h) → **Claude**
- [ ] AWS ECS deployment config (6h) → **Claude**
- [ ] Sentry integration (2h) → **Claude**
- [ ] Health checks deep (2h) → **Claude**
- [ ] Circuit breaker OpenAI (2h) → **Claude**

### 🧪 Testing
- [ ] Pytest suite completa (15h) → **Codex**
- [ ] Coverage 70%+

### 📖 Documentação
- [ ] DEPLOYMENT.md (3h) → **Copilot**
- [ ] RUNBOOK.md (2h) → **Copilot**

---

## V1.1 - Canais Adicionais (Mês 2)

### WhatsApp Integration
- [ ] Criar WhatsAppAdapter
- [ ] Webhook routes + validação
- [ ] Testar fluxo E2E

### Email Inbound
- [ ] IMAP/POP3 ou webhook
- [ ] Email parsing e thread tracking
- [ ] Testar fluxo E2E

---

## V1.2 - Dashboard Completo (Mês 2-3)

- [ ] Testar componentes existentes
- [ ] Página de métricas/analytics
- [ ] Logs viewer funcional
- [ ] Multi-user support (roles)

---

## V1.3 - Advanced RAG (Mês 3)

- [ ] Re-ranking de results
- [ ] Metadata filtering avançado
- [ ] UI para upload de docs

---

## V1.4-1.5 - Analytics + Feedback (Mês 3-4)

- [ ] Customer feedback system
- [ ] Dashboards Grafana/Metabase
- [ ] SLA tracking por empresa

---

## V2.0+ - Long Term (Mês 6+)

- [ ] Voice support (Twilio)
- [ ] Multi-language (i18n/l10n)
- [ ] Proactive support
- [ ] Fine-tuning de modelos
- [ ] Integração CRM (Salesforce, HubSpot)

---

## 📊 Prioridade

| Versão | Prioridade | Prazo |
|--------|------------|-------|
| V1.0 | 🔴 Crítica | Semana 3 |
| V1.1 | 🟠 Alta | Mês 2 |
| V1.2 | 🟡 Média | Mês 2-3 |
| V1.3+ | 🟢 Baixa | Mês 3+ |
