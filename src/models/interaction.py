"""
Interaction models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from enum import Enum


class InteractionType(str, Enum):
    """Interaction type values"""
    CUSTOMER_MESSAGE = "customer_message"
    AGENT_RESPONSE = "agent_response"
    SYSTEM_UPDATE = "system_update"


class InteractionBase(BaseModel):
    """Base interaction model"""
    ticket_id: str
    type: InteractionType
    content: str
    sentiment_score: float = 0.0


class InteractionCreate(InteractionBase):
    """Model for creating a new interaction"""
    pass


class Interaction(InteractionBase):
    """Complete interaction model with timestamp"""
    id: Optional[str] = Field(None, alias="_id")
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
