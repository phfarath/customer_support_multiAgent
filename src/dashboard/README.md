# Dashboard Module - Interface para Agentes Humanos

> **Localização:** `src/dashboard/`
> **Propósito:** Interface Streamlit para agentes humanos gerenciarem tickets escalados

---

## 📖 Visão Geral

O Dashboard é uma aplicação **Streamlit** que permite agentes humanos visualizarem e responderem tickets que foram escalados pelo `EscalatorAgent`. É a interface onde humanos assumem casos que a IA não conseguiu resolver automaticamente.

### Funcionalidades

✅ **Login por Empresa** - Seleciona empresa para acessar
✅ **Inbox de Tickets Escalados** - Lista tickets que precisam de atenção humana
✅ **Detalhes do Ticket** - Visualiza histórico completo de interações
✅ **Responder Cliente** - Envia resposta que vai direto para o cliente
✅ **Configuração de Bot** - Edita nome, welcome message, policies
✅ **Gestão de Produtos** - Adiciona/edita produtos da empresa
✅ **Business Hours** - Configura horário de atendimento

---

## 📁 Estrutura de Arquivos

```
src/dashboard/
├── app.py              # ⭐ Aplicação Streamlit principal
└── connection.py       # MongoDB connection helper
```

---

## 🚀 Como Executar

### Modo Desenvolvimento

```bash
# Navegar para raiz do projeto
cd /path/to/customer_support_multiAgent

# Executar dashboard
streamlit run src/dashboard/app.py
```

**URL:** http://localhost:8501

### Modo Produção

```bash
# Com configurações específicas
streamlit run src/dashboard/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true
```

### Deploy (Cloud)

```bash
# Streamlit Cloud (grátis)
# 1. Push para GitHub
# 2. Conectar em share.streamlit.io
# 3. Deploy automático

# OU Docker
docker build -t dashboard .
docker run -p 8501:8501 dashboard
```

---

## 🎨 Interface do Dashboard

### 1. Login Page

```
┌─────────────────────────────────────┐
│  🏢 Customer Support Dashboard      │
├─────────────────────────────────────┤
│                                     │
│  Selecione sua Empresa:             │
│  ┌─────────────────────────────┐   │
│  │ Empresa ABC                 ▼│   │
│  └─────────────────────────────┘   │
│                                     │
│         [ Entrar ]                  │
│                                     │
└─────────────────────────────────────┘
```

**Funcionalidade:**
- Lista todas as empresas de `company_configs`
- Salva `company_id` em `st.session_state`
- Redireciona para inbox

### 2. Inbox de Tickets Escalados

```
┌─────────────────────────────────────────────────────────┐
│  📥 Tickets Escalados                                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔴 TICKET-123  [CRITICAL]  Billing                     │
│      Cliente: João Silva                                │
│      Escalado: há 2 horas                               │
│      Motivo: Low confidence (0.45)                      │
│      [ Ver Detalhes ]                                   │
│                                                         │
│  🟡 TICKET-456  [HIGH]  Technical                       │
│      Cliente: Maria Santos                              │
│      Escalado: há 5 horas                               │
│      Motivo: SLA breach (6 hours)                       │
│      [ Ver Detalhes ]                                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Funcionalidade:**
- Query MongoDB: `{"escalated": true, "status": {"$ne": "resolved"}}`
- Ordenado por prioridade (critical → low)
- Badge visual por prioridade
- Botão para abrir detalhes

### 3. Detalhes do Ticket

```
┌─────────────────────────────────────────────────────────┐
│  📋 TICKET-123  [CRITICAL]                              │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Cliente: João Silva (+5511999999999)                   │
│  Canal: Telegram                                        │
│  Categoria: Billing                                     │
│  Criado: 2026-01-20 10:00                               │
│  Escalado: 2026-01-20 12:00 (há 2 horas)                │
│  Motivo: Low confidence response (0.45)                 │
│                                                         │
│  ━━━━━━━━━ HISTÓRICO ━━━━━━━━━                        │
│                                                         │
│  👤 Cliente (10:00):                                    │
│      "Fui cobrado em duplicidade! Urgente!"            │
│                                                         │
│  🤖 Bot (10:01):                                        │
│      "Vou verificar sua cobrança..."                    │
│                                                         │
│  👤 Cliente (10:05):                                    │
│      "Preciso de ajuda imediata!"                       │
│                                                         │
│  🚨 Sistema:                                            │
│      Ticket escalado para agente humano                │
│                                                         │
│  ━━━━━━━━━ RESPONDER ━━━━━━━━━                        │
│                                                         │
│  ┌─────────────────────────────────────┐               │
│  │ Digite sua resposta...              │               │
│  │                                     │               │
│  │                                     │               │
│  └─────────────────────────────────────┘               │
│                                                         │
│  [ Enviar Resposta ]  [ Resolver Ticket ]              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Funcionalidade:**
- Mostra histórico completo de `interactions`
- Caixa de texto para resposta
- Botão "Enviar Resposta": salva interação + envia para cliente
- Botão "Resolver Ticket": marca como resolvido

### 4. Configuração do Bot

```
┌─────────────────────────────────────────────────────────┐
│  ⚙️ Configuração do Bot                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Nome do Bot:                                           │
│  ┌─────────────────────────────────────┐               │
│  │ Assistente ABC                      │               │
│  └─────────────────────────────────────┘               │
│                                                         │
│  Mensagem de Boas-vindas:                               │
│  ┌─────────────────────────────────────┐               │
│  │ Olá! Sou o Assistente ABC.         │               │
│  │ Como posso ajudar hoje?            │               │
│  └─────────────────────────────────────┘               │
│                                                         │
│  Políticas:                                             │
│  ┌─────────────────────────────────────┐               │
│  │ Refund: Reembolso em 7 dias        │               │
│  │ Cancellation: Sem taxa             │               │
│  └─────────────────────────────────────┘               │
│                                                         │
│  [ Salvar Configurações ]                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Funcionalidade:**
- Edita `company_configs` collection
- Campos: `bot_name`, `welcome_message`, `policies`
- Salva no MongoDB em tempo real

### 5. Gestão de Produtos

```
┌─────────────────────────────────────────────────────────┐
│  📦 Produtos e Serviços                                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Produto 1: Plano Básico                                │
│      Preço: R$ 29,90/mês                                │
│      Descrição: Acesso básico aos recursos              │
│      [ Editar ]  [ Remover ]                            │
│                                                         │
│  Produto 2: Plano Premium                               │
│      Preço: R$ 99,90/mês                                │
│      Descrição: Todos os recursos + suporte 24/7        │
│      [ Editar ]  [ Remover ]                            │
│                                                         │
│  ━━━━━━━━━ ADICIONAR PRODUTO ━━━━━━━━━                │
│                                                         │
│  Nome: ┌────────────────┐                               │
│        │                │                               │
│        └────────────────┘                               │
│                                                         │
│  Preço: ┌────────────────┐                              │
│         │                │                              │
│         └────────────────┘                              │
│                                                         │
│  [ Adicionar Produto ]                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Funcionalidade:**
- Lista produtos de `company_config.products`
- Adiciona novo produto (nome, preço, descrição)
- Edita/remove produtos existentes

---

## 💻 Código Principal

### Estrutura do app.py

```python
import streamlit as st
from src.dashboard.connection import get_mongo_client
from src.database.operations import get_collection, COLLECTION_TICKETS, COLLECTION_INTERACTIONS
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Customer Support Dashboard",
    page_icon="🎧",
    layout="wide"
)

# Session state
if "company_id" not in st.session_state:
    st.session_state.company_id = None

# Sidebar navigation
def sidebar():
    st.sidebar.title("📊 Dashboard")

    if st.session_state.company_id:
        st.sidebar.info(f"Empresa: {st.session_state.company_name}")

        page = st.sidebar.radio(
            "Navegação",
            ["📥 Inbox", "⚙️ Configurações", "📦 Produtos"]
        )

        if st.sidebar.button("🚪 Sair"):
            st.session_state.company_id = None
            st.rerun()

        return page
    return None

# Login page
def login_page():
    st.title("🏢 Customer Support Dashboard")

    # Buscar empresas
    companies = get_companies()

    if not companies:
        st.error("Nenhuma empresa cadastrada")
        return

    # Select company
    company_names = {c["company_name"]: c["company_id"] for c in companies}
    selected = st.selectbox("Selecione sua Empresa", list(company_names.keys()))

    if st.button("Entrar"):
        st.session_state.company_id = company_names[selected]
        st.session_state.company_name = selected
        st.rerun()

# Inbox page
async def inbox_page():
    st.title("📥 Tickets Escalados")

    # Buscar tickets escalados
    tickets = await get_escalated_tickets(st.session_state.company_id)

    if not tickets:
        st.info("Nenhum ticket escalado no momento")
        return

    # Mostrar cada ticket
    for ticket in tickets:
        with st.expander(
            f"{'🔴' if ticket['priority'] == 'critical' else '🟡'} "
            f"{ticket['ticket_id']} - {ticket['category']}"
        ):
            show_ticket_details(ticket)

# Ticket details
async def show_ticket_details(ticket):
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Detalhes")
        st.write(f"**Cliente:** {ticket.get('customer_name', 'N/A')}")
        st.write(f"**Categoria:** {ticket['category']}")
        st.write(f"**Prioridade:** {ticket['priority']}")

    with col2:
        st.subheader("Status")
        st.write(f"**Criado:** {ticket['created_at']}")
        st.write(f"**Escalado:** {ticket.get('escalated_at', 'N/A')}")

    # Histórico
    st.subheader("📜 Histórico de Interações")
    interactions = await get_interactions(ticket["ticket_id"])

    for interaction in interactions:
        icon = "👤" if interaction["sender"] == "customer" else "🤖"
        st.markdown(f"{icon} **{interaction['sender']}** ({interaction['timestamp']})")
        st.markdown(f"> {interaction['message']}")
        st.markdown("---")

    # Responder
    st.subheader("💬 Responder")
    response = st.text_area("Digite sua resposta", key=f"response_{ticket['ticket_id']}")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Enviar Resposta", key=f"send_{ticket['ticket_id']}"):
            await send_response(ticket["ticket_id"], response)
            st.success("Resposta enviada!")
            st.rerun()

    with col2:
        if st.button("Resolver Ticket", key=f"resolve_{ticket['ticket_id']}"):
            await resolve_ticket(ticket["ticket_id"])
            st.success("Ticket resolvido!")
            st.rerun()

# Main
async def main():
    page = sidebar()

    if not st.session_state.company_id:
        login_page()
    else:
        if page == "📥 Inbox":
            await inbox_page()
        elif page == "⚙️ Configurações":
            config_page()
        elif page == "📦 Produtos":
            products_page()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 🔌 Integração com Backend

### Buscar Tickets Escalados

```python
async def get_escalated_tickets(company_id: str):
    """Busca tickets escalados da empresa"""
    tickets_collection = get_collection(COLLECTION_TICKETS)

    tickets = await tickets_collection.find({
        "company_id": company_id,
        "escalated": True,
        "status": {"$ne": "resolved"}
    }).sort("priority", -1).to_list(length=100)

    return tickets
```

### Enviar Resposta

```python
async def send_response(ticket_id: str, message: str):
    """Envia resposta do agente humano ao cliente"""
    # 1. Salvar interação
    await save_interaction(
        ticket_id=ticket_id,
        sender="human_agent",
        message=message,
        channel="dashboard"
    )

    # 2. Buscar canal do cliente
    ticket = await get_ticket(ticket_id)
    channel = ticket["channel"]

    # 3. Enviar via canal apropriado
    if channel == "telegram":
        await send_telegram_message(ticket["customer_id"], message)
    elif channel == "whatsapp":
        await send_whatsapp_message(ticket["customer_id"], message)

    # 4. Atualizar ticket
    await update_ticket(ticket_id, {"status": "in_progress"})
```

### Resolver Ticket

```python
async def resolve_ticket(ticket_id: str):
    """Marca ticket como resolvido"""
    tickets_collection = get_collection(COLLECTION_TICKETS)

    await tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$set": {
                "status": "resolved",
                "resolved_at": datetime.now(),
                "resolved_by": "human_agent"
            }
        }
    )
```

---

## 🎨 Customização da UI

### Tema Personalizado

```python
# .streamlit/config.toml
[theme]
primaryColor = "#FF4B4B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
```

### CSS Customizado

```python
# app.py

st.markdown("""
    <style>
    .ticket-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }

    .priority-critical {
        color: #ff4b4b;
        font-weight: bold;
    }

    .priority-high {
        color: #ffa500;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)
```

---

## 🔔 Notificações em Tempo Real

### Polling Automático

```python
import time

# Auto-refresh a cada 30 segundos
if "last_refresh" not in st.session_state:
    st.session_state.last_refresh = time.time()

current_time = time.time()
if current_time - st.session_state.last_refresh > 30:
    st.session_state.last_refresh = current_time
    st.rerun()

st.sidebar.info(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
```

### Notificações de Novos Tickets

```python
# Conta tickets não lidos
new_tickets_count = await count_new_escalated_tickets(company_id)

if new_tickets_count > 0:
    st.sidebar.error(f"🔔 {new_tickets_count} novos tickets!")
```

---

## 📊 Métricas e Analytics (Futuro)

### Dashboard de Métricas

```python
def metrics_page():
    st.title("📊 Métricas e Analytics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Tickets Hoje", 45, delta="+5")

    with col2:
        st.metric("Taxa Escalação", "12%", delta="-2%")

    with col3:
        st.metric("Tempo Médio", "2.5h", delta="+0.3h")

    with col4:
        st.metric("Satisfação", "4.2/5", delta="+0.1")

    # Gráficos
    st.subheader("Tickets por Categoria")
    # chart_data = ...
    # st.bar_chart(chart_data)
```

---

## 🧪 Testando o Dashboard

### Teste Manual

1. **Executar dashboard:**
   ```bash
   streamlit run src/dashboard/app.py
   ```

2. **Criar ticket escalado para teste:**
   ```python
   # scripts/create_test_escalation.py
   ticket = {
       "ticket_id": "TEST-001",
       "company_id": "comp_123",
       "escalated": True,
       "priority": "critical",
       "category": "billing",
       "subject": "Teste de escalação"
   }
   await tickets_collection.insert_one(ticket)
   ```

3. **Verificar no dashboard:** Deve aparecer na inbox

### Teste Automatizado (Selenium)

```python
from selenium import webdriver

def test_dashboard_login():
    driver = webdriver.Chrome()
    driver.get("http://localhost:8501")

    # Select company
    company_select = driver.find_element_by_css_selector("select")
    company_select.select_by_visible_text("Empresa ABC")

    # Click login
    login_button = driver.find_element_by_text("Entrar")
    login_button.click()

    # Assert redirected to inbox
    assert "Tickets Escalados" in driver.page_source
```

---

## 🔐 Autenticação e Segurança

### Autenticação Simples (Atual)

Atualmente usa apenas seleção de empresa (sem senha).

### Autenticação com Senha (Futuro)

```python
import hashlib

def login_page_with_auth():
    st.title("🔐 Login")

    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = authenticate(email, password)
        if user:
            st.session_state.user = user
            st.session_state.company_id = user["company_id"]
            st.rerun()
        else:
            st.error("Credenciais inválidas")

def authenticate(email: str, password: str):
    """Verifica credenciais no MongoDB"""
    users_collection = get_collection("users")

    password_hash = hashlib.sha256(password.encode()).hexdigest()

    user = users_collection.find_one({
        "email": email,
        "password_hash": password_hash
    })

    return user
```

### JWT Tokens (Produção)

```python
import jwt

def generate_token(user_id: str) -> str:
    return jwt.encode(
        {"user_id": user_id, "exp": datetime.now() + timedelta(hours=24)},
        SECRET_KEY,
        algorithm="HS256"
    )

def verify_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
```

---

## 📱 Mobile Responsive

Streamlit é automaticamente responsivo, mas pode melhorar:

```python
# Detectar mobile
is_mobile = st.sidebar.checkbox("Modo Mobile", value=False)

if is_mobile:
    # Layout simplificado
    show_mobile_layout()
else:
    # Layout completo
    show_desktop_layout()
```

---

## 🚀 Deploy

### Streamlit Cloud (Grátis)

1. Push código para GitHub
2. Criar conta em https://share.streamlit.io
3. Conectar repositório
4. Deploy automático!

**Secrets management:**
```toml
# .streamlit/secrets.toml
MONGODB_URI = "mongodb+srv://..."
OPENAI_API_KEY = "sk-..."
```

### Docker

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```bash
docker build -t dashboard .
docker run -p 8501:8501 dashboard
```

---

## 🐛 Troubleshooting

### Dashboard não conecta ao MongoDB

**Problema:** Erro de conexão

**Solução:**
```python
# Verify .env
MONGODB_URI=mongodb://localhost:27017

# Test connection
from src.dashboard.connection import get_mongo_client
client = get_mongo_client()
print(client.server_info())
```

### Session state não persiste

**Problema:** Dados perdidos após refresh

**Solução:**
```python
# Usar session_state corretamente
if "company_id" not in st.session_state:
    st.session_state.company_id = None

# Nunca sobrescrever sem verificar
```

### Auto-refresh muito frequente

**Problema:** Dashboard recarrega constantemente

**Solução:**
```python
# Aumentar intervalo
REFRESH_INTERVAL = 60  # 60 segundos

if time.time() - st.session_state.last_refresh > REFRESH_INTERVAL:
    st.rerun()
```

---

## 📚 Referências

### Internal Docs
- **ARCHITECTURE.md** - Visão geral do projeto
- **src/agents/README.md** - Como agentes escalam tickets

### External Docs
- Streamlit: https://docs.streamlit.io/
- Streamlit Cloud: https://share.streamlit.io/

---

**Última atualização:** 2026-01-20
**Versão:** 1.0
**Mantenedor:** Aethera Labs Team
