"""
Customer Model
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class Customer(BaseModel):
    """Cliente registrado no sistema"""
    
    customer_id: str = Field(..., description="ID único do cliente")
    phone_number: str = Field(..., description="Telefone do cliente")
    company_id: str = Field(..., description="ID da empresa do cliente")
    
    name: Optional[str] = Field(None, description="Nome do cliente")
    email: Optional[str] = Field(None, description="Email do cliente")
    telegram_chat_id: Optional[int] = Field(None, description="Chat ID do Telegram")
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class CustomerCreate(BaseModel):
    """Modelo para criar novo cliente"""
    
    phone_number: str
    company_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    telegram_chat_id: Optional[int] = None
