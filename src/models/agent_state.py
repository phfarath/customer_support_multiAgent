"""
Agent state models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any


class AgentStateBase(BaseModel):
    """Base agent state model"""
    ticket_id: str
    agent_name: str
    phase: str
    state: Dict[str, Any] = {}


class AgentStateCreate(AgentStateBase):
    """Model for creating a new agent state"""
    pass


class AgentState(AgentStateBase):
    """Complete agent state model with timestamps"""
    id: Optional[str] = Field(None, alias="_id")
    lock_version: int = 0
    updated_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
