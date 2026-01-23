# Input Sanitization (XSS & Injection Prevention)

> **Implementado em:** 2026-01-23
> **Status:** ✅ 90% Production-ready

---

## Descrição

Sistema completo de sanitização de inputs para prevenir ataques XSS, SQL Injection e payloads maliciosos. Todas as entradas de usuários são sanitizadas antes de serem processadas ou armazenadas no banco de dados.

---

## Arquivos Modificados/Criados

- **Sanitization Module:** `src/utils/sanitization.py` (237 linhas)
- **Endpoints Protegidos:** 10 endpoints com user input
  - `src/api/ingest_routes.py`
  - `src/api/routes.py`
  - `src/api/human_routes.py`
  - `src/api/telegram_routes.py`
  - `src/api/company_routes.py`

---

## Funções Disponíveis

### 1. Text Sanitization
```python
sanitize_text(text: str, max_length: int = 4000) -> str
```
- HTML escape: `<script>` → `<script>`
- Truncate to max_length
- Remove null bytes
- Normalize whitespace

**Uso:** Mensagens, descrições, respostas

### 2. Identifier Sanitization
```python
sanitize_identifier(identifier: str, max_length: int = 100) -> str
```
- HTML escape
- Truncate
- Remove null bytes

**Uso:** IDs de ticket, customer, etc

### 3. Email Validation
```python
sanitize_email(email: str) -> str
```
- Lowercase
- Regex validation (RFC 5322)
- Truncate to 254 chars
- Raises ValueError if invalid

**Uso:** Validação de emails

### 4. Phone Normalization
```python
sanitize_phone(phone: str) -> str
```
- Remove non-digits (except +)
- Ensure starts with +
- Truncate to 20 chars

**Uso:** Normalização de telefones

### 5. Company ID Validation
```python
sanitize_company_id(company_id: str) -> str
```
- Alphanumeric + underscore only
- Truncate to 50 chars
- Raises ValueError if invalid chars

**Uso:** Validação de company IDs

### 6. Dict Key Filtering
```python
sanitize_dict_keys(data: dict, allowed_keys: list) -> dict
```
- Remove keys not in whitelist
- Prevents parameter pollution

**Uso:** Filtragem de parâmetros

### 7. Safe Filename
```python
sanitize_filename(filename: str, max_length: int = 255) -> str
```
- Remove path separators (/, \)
- Remove dangerous chars
- Truncate

**Uso:** Upload de arquivos

---

## Endpoints Protegidos (10)

### Message Ingestion
```python
# src/api/ingest_routes.py
text = sanitize_text(request.text, max_length=4000)
external_user_id = sanitize_identifier(request.external_user_id)
company_id = sanitize_company_id(request.company_id)
customer_phone = sanitize_phone(request.customer_phone)
customer_email = sanitize_email(request.customer_email)
```

### Ticket Creation
```python
# src/api/routes.py
ticket_id = sanitize_identifier(ticket_data.ticket_id)
subject = sanitize_text(ticket_data.subject, max_length=200)
description = sanitize_text(ticket_data.description, max_length=4000)
customer_id = sanitize_identifier(ticket_data.customer_id)
```

### Human Agent Reply
```python
# src/api/human_routes.py
ticket_id = sanitize_identifier(request.ticket_id)
reply_text = sanitize_text(request.reply_text, max_length=4000)
```

### Telegram Webhook
```python
# src/api/telegram_routes.py
text = sanitize_text(parsed["text"], max_length=4000)
external_user_id = sanitize_identifier(parsed["external_user_id"])
company_id = sanitize_company_id(company_id) if company_id else None
```

### Company Config
```python
# src/api/company_routes.py (create/update)
company_id = sanitize_company_id(config.company_id)
company_name = sanitize_text(config.company_name, max_length=100)
escalation_email = sanitize_email(config.escalation_email)
bot_handoff_message = sanitize_text(config.bot_handoff_message, max_length=1000)
```

---

## Exemplos de Ataques Prevenidos

### XSS (Cross-Site Scripting)
```python
# Antes (VULNERÁVEL):
message = "<script>alert('XSS')</script>"
await save_interaction(message=message)  # Armazenado sem escape!

# Depois (SEGURO):
message = sanitize_text("<script>alert('XSS')</script>")
# Result: "<script>alert('XSS')</script>"
await save_interaction(message=message)  # Seguro!
```

### SQL Injection (MongoDB)
```python
# Antes (VULNERÁVEL):
company_id = "techcorp'; DROP TABLE users; --"
await companies.find_one({"company_id": company_id})  # Risco!

# Depois (SEGURO):
company_id = sanitize_company_id("techcorp'; DROP TABLE users; --")
# Raises ValueError: Invalid company_id (chars especiais rejeitados)
```

### Null Byte Attack
```python
# Antes (VULNERÁVEL):
filename = "document.pdf\x00.exe"
# Sistema pode interpretar como document.pdf (bypass de extensão)

# Depois (SEGURO):
filename = sanitize_text("document.pdf\x00.exe")
# Result: "document.pdf.exe" (null byte removido)
```

### DoS via Payload Gigante
```python
# Antes (VULNERÁVEL):
message = "A" * 10_000_000  # 10MB de texto
await save_interaction(message=message)  # Sobrecarrega DB!

# Depois (SEGURO):
message = sanitize_text("A" * 10_000_000, max_length=4000)
# Result: "AAAA..." (4000 chars) - Truncado!
```

---

## Error Handling

Sanitização sempre retorna valor ou lança `ValueError`:

```python
try:
    email = sanitize_email(user_input)
except ValueError as e:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid input: {str(e)}"
    )
```

---

## Boas Práticas

### DO:
- ✅ Sanitize ANTES de salvar no DB
- ✅ Sanitize ANTES de usar em queries
- ✅ Usar função específica para cada tipo (email, phone, text)
- ✅ Definir max_length apropriado para cada campo

### DON'T:
- ❌ Confiar em input do usuário sem sanitização
- ❌ Sanitizar apenas no frontend (sempre no backend também)
- ❌ Usar mesma função para todos os tipos de input
- ❌ Esquecer de truncar strings longas

---

## Exemplos de Código

### Sanitização Completa de Request
```python
from src.utils.sanitization import (
    sanitize_text,
    sanitize_identifier,
    sanitize_email,
    sanitize_phone,
    sanitize_company_id
)
from fastapi import HTTPException

@router.post("/api/ingest-message")
async def ingest_message(request: IngestMessageRequest):
    try:
        # Sanitizar todos os inputs
        sanitized_data = {
            "text": sanitize_text(request.text, max_length=4000),
            "external_user_id": sanitize_identifier(request.external_user_id),
            "company_id": sanitize_company_id(request.company_id),
            "customer_phone": sanitize_phone(request.customer_phone),
            "customer_email": sanitize_email(request.customer_email)
        }
        
        # Processar com dados sanitizados
        ticket = await create_ticket(**sanitized_data)
        
        return {"ticket_id": ticket["ticket_id"]}
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid input: {str(e)}"
        )
```

### Validação de Email
```python
from src.utils.sanitization import sanitize_email

def create_user(email: str, password: str):
    try:
        # Valida e normaliza email
        validated_email = sanitize_email(email)
        
        # Verifica se já existe
        existing = await users.find_one({"email": validated_email})
        if existing:
            raise ValueError("Email already registered")
        
        # Cria usuário
        await users.insert_one({
            "email": validated_email,
            "password_hash": hash_password(password),
            "created_at": datetime.utcnow()
        })
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
```

---

## Testes Realizados

- ✅ XSS prevention (HTML escape)
- ✅ SQL injection prevention (MongoDB)
- ✅ Null byte removal
- ✅ DoS prevention (length limiting)
- ✅ Email validation (RFC 5322)
- ✅ Phone normalization
- ✅ Company ID validation
- ✅ Dict key filtering
- ✅ Filename sanitization
- ✅ Error handling (ValueError)

---

## Troubleshooting

### Erro: "Invalid input"
```bash
# Verifique o tipo de input usado
# - sanitize_text() para mensagens
# - sanitize_identifier() para IDs
# - sanitize_email() para emails
# - sanitize_phone() para telefones
# - sanitize_company_id() para company IDs
```

### Input truncado inesperadamente
```bash
# Verifique o max_length definido
# - sanitize_text(text, max_length=4000) - padrão
# - sanitize_identifier(id, max_length=100) - padrão
# Ajuste conforme necessário
```

---

## Referências

- [ARCHITECTURE.md](../../ARCHITECTURE.md) - Visão geral do projeto
- [AI_INSTRUCTIONS.md](../../AI_INSTRUCTIONS.md) - Guia para agentes de IA
- [Rate Limiting](2026-01-23_18-30_rate-limiting.md) - Prevenção de DoS
- [CORS Hardening](2026-01-23_18-30_cors-hardening.md) - Segurança de origem
