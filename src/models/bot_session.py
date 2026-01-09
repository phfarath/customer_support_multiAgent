"""
Bot Session Model
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SessionState(str, Enum):
    """Estados da sessão"""
    NEW = "new"                       # Novo usuário
    AWAITING_PHONE = "awaiting_phone" # Aguardando telefone
    AWAITING_COMPANY = "awaiting_company"  # Telefone novo, escolher empresa
    REGISTERED = "registered"         # Registrado e pode usar
    RATE_LIMITED = "rate_limited"     # Bloqueado temporariamente


class BotSession(BaseModel):
    """Sessão do usuário no bot Telegram"""
    
    chat_id: int = Field(..., description="ID do chat Telegram")
    state: SessionState = Field(default=SessionState.NEW)
    
    # Dados do Telegram
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    
    # Vínculo com sistema
    customer_id: Optional[str] = Field(None, description="ID do cliente (após registro)")
    company_id: Optional[str] = Field(None, description="ID da empresa")
    phone_number: Optional[str] = Field(None, description="Telefone registrado")
    
    # Rate limiting
    message_count: int = Field(default=0)
    rate_limit_until: Optional[datetime] = Field(None)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_message_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True
        json_encoders = {datetime: lambda v: v.isoformat()}
