"""
Interaction models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class InteractionType(str, Enum):
    """Interaction type values"""
    CUSTOMER_MESSAGE = "customer_message"
    AGENT_RESPONSE = "agent_response"
    SYSTEM_UPDATE = "system_update"


class AIDecisionMetadata(BaseModel):
    """Metadata about AI decision for transparency and auditability"""
    confidence_score: float = 0.0  # 0.0 to 1.0
    reasoning: Optional[str] = None  # Textual explanation of the decision
    decision_type: Optional[str] = None  # "triage", "routing", "resolution", "escalation"
    factors: List[str] = []  # List of factors considered in the decision


class InteractionBase(BaseModel):
    """Base interaction model"""
    ticket_id: str
    type: InteractionType
    content: str
    channel: Optional[str] = None
    sentiment_score: float = 0.0
    ai_metadata: Optional[AIDecisionMetadata] = None  # AI decision transparency


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

