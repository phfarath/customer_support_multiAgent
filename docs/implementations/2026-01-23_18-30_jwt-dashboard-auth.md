# JWT Dashboard Authentication

> **Implementado em:** 2026-01-22
> **Status:** ✅ 85% Production-ready

---

## Descrição

Sistema completo de autenticação com JWT tokens para o Streamlit Dashboard. Permite que agentes humanos façam login com email e senha, com proteção via bcrypt e isolamento por empresa.

---

## Arquivos Modificados/Criados

- **Modelo:** `src/models/user.py` - User model com hash/verify de senha
- **JWT Handler:** `src/utils/jwt_handler.py` - create_jwt_token, verify_jwt_token, refresh_jwt_token
- **Dashboard:** `src/dashboard/app.py` - Login, autenticação, session management
- **Components:**
  - `src/dashboard/components/escalated_inbox.py` - Filtro por company_id
  - `src/dashboard/components/bot_config.py` - Filtro por company_id
  - `src/dashboard/components/products_config.py` - Filtro por company_id
- **Script:** `scripts/create_dashboard_user.py` - Criação de usuários
- **Database:** MongoDB `users` collection

---

## Como Usar

### 1. Criar Primeiro Usuário (Bootstrap)

```bash
python scripts/create_dashboard_user.py \
    --email admin@techcorp.com \
    --password Admin123! \
    --company-id techcorp_001 \
    --full-name "Admin Techcorp" \
    --role admin
```

**Output:**
```
✅ User created successfully!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
User ID:     user_a1b2c3d4e5f6g7h8
Email:       admin@techcorp.com
Full Name:   Admin Techcorp
Company ID:  techcorp_001
Role:        admin
Active:      True
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔐 Login Information:
   Email:    admin@techcorp.com
   Password: Admin123!

🌐 Dashboard URL:
   http://localhost:8501
```

### 2. Criar Usuário Operador

```bash
python scripts/create_dashboard_user.py \
    --email operador@techcorp.com \
    --password Operador123! \
    --company-id techcorp_001 \
    --full-name "João Silva"
    # role padrão é "operator"
```

### 3. Acessar o Dashboard

1. Navegue para `http://localhost:8501`
2. Faça login com email e senha
3. O dashboard filtrará automaticamente por company_id do usuário

---

## Roles de Usuário

### Admin
- Acesso completo ao dashboard
- Pode modificar configurações do bot
- Pode gerenciar produtos
- Pode responder tickets escalados

### Operator
- Pode visualizar tickets escalados
- Pode responder tickets
- Pode visualizar configurações (sem editar)

---

## Segurança

### Senhas
- Hasheadas com bcrypt (custo: 12 rounds)
- Truncadas automaticamente a 72 bytes (limite do bcrypt)
- Nunca armazenadas em plaintext

### JWT Tokens
- Assinados com `settings.jwt_secret_key` (deve ser configurado no `.env`)
- Algoritmo: HS256
- Payload inclui: `user_id`, `company_id`, `email`, `full_name`, `role`, `exp`, `iat`
- Expiração: 24 horas

### Company Isolation (CRÍTICO)
- Todos os componentes do dashboard filtram por `company_id` do usuário autenticado
- Impossível ver/modificar dados de outras empresas
- Queries MongoDB sempre incluem filtro: `{"company_id": user_data["company_id"]}`

---

## Configuração Necessária

### `.env` file:
```bash
# JWT Secret (IMPORTANTE: Gerar valor único em produção)
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
```

### Gerar secret seguro:
```python
import secrets
print(secrets.token_urlsafe(32))
# Output: "AbCdEfGhIjKlMnOpQrStUvWxYz1234567890AbCdEf"
```

---

## Exemplos de Código

### Company Isolation

```python
# ✅ CORRETO - Todos os componentes filtram por company_id
def render_escalated_inbox(company_id: str):
    tickets = tickets_col.find({
        "status": "escalated",
        "company_id": company_id  # ← CRÍTICO
    })

# ❌ ERRADO - Sem filtro, vaza dados de outras empresas
def render_escalated_inbox():
    tickets = tickets_col.find({"status": "escalated"})
```

### JWT Handler

```python
# src/utils/jwt_handler.py
import jwt
from datetime import datetime, timedelta

def create_jwt_token(user_data: dict) -> str:
    """Cria JWT token com dados do usuário"""
    payload = {
        "user_id": user_data["user_id"],
        "company_id": user_data["company_id"],
        "email": user_data["email"],
        "full_name": user_data["full_name"],
        "role": user_data["role"],
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")

def verify_jwt_token(token: str) -> dict:
    """Verifica JWT token e retorna payload"""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
```

### Login Flow

```python
# src/dashboard/app.py
import streamlit as st
from src.utils.jwt_handler import create_jwt_token, verify_jwt_token

def login_page():
    st.title("🔐 Login")
    
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        # 1. Validar credenciais
        user = authenticate_user(email, password)
        
        if user:
            # 2. Criar JWT token
            token = create_jwt_token(user)
            
            # 3. Armazenar em session
            st.session_state["jwt_token"] = token
            st.session_state["user_data"] = user
            
            # 4. Redirecionar
            st.rerun()

def check_auth():
    """Verifica se usuário está autenticado"""
    if "jwt_token" not in st.session_state:
        return False
    
    try:
        # Verificar token
        user_data = verify_jwt_token(st.session_state["jwt_token"])
        return True
    except ValueError:
        # Token inválido ou expirado
        if "jwt_token" in st.session_state:
            del st.session_state["jwt_token"]
        return False
```

---

## Boas Práticas

### DO:
- ✅ Usar senhas fortes (mínimo 8 chars, letras + números + símbolos)
- ✅ Configurar `JWT_SECRET_KEY` única por ambiente
- ✅ Criar usuários separados por operador (não compartilhar credenciais)
- ✅ Desativar usuários que saíram da empresa (`active: False`)

### DON'T:
- ❌ Usar `JWT_SECRET_KEY` padrão em produção
- ❌ Compartilhar credenciais de login
- ❌ Deletar usuários (desative com `active: False` para manter audit trail)
- ❌ Commitar senhas no git

---

## Troubleshooting

### Login não funciona:
```bash
# 1. Verificar se usuário existe no MongoDB
mongo --eval 'db.users.findOne({email: "admin@techcorp.com"})'

# 2. Verificar se senha foi hasheada corretamente
# Password hash deve começar com "$2b$"

# 3. Verificar logs do Streamlit
streamlit run src/dashboard/app.py
```

### JWT expira muito rápido:
```bash
# Aumentar tempo de expiração em .env
JWT_EXPIRATION_HOURS=48  # 2 dias
```

### KeyError ao fazer login:
```bash
# Erro: KeyError: 'full_name' ou 'role'
# Fix: Fazer logout e login novamente (token antigo não tem esses campos)
```

---

## Testes Realizados

- ✅ Criação de usuário via script
- ✅ Login com email/senha válidos
- ✅ Rejeição de credenciais inválidas
- ✅ JWT token creation e verification
- ✅ Expiração de token (24h)
- ✅ Company isolation no dashboard
- ✅ Role-based access (admin vs operator)
- ✅ Logout (limpeza de session)

---

## Referências

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Visão geral do projeto
- [AI_INSTRUCTIONS.md](../../AI_INSTRUCTIONS.md) - Guia para agentes de IA
- [API Key Authentication](2026-01-23_18-30_api-key-authentication.md) - Autenticação da API
