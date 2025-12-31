"""
Routing decision models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class RoutingDecisionBase(BaseModel):
    """Base routing decision model"""
    ticket_id: str
    agent_name: str = "router"
    target_team: str
    confidence: float
    reasons: List[str] = []


class RoutingDecisionCreate(RoutingDecisionBase):
    """Model for creating a new routing decision"""
    pass


class RoutingDecision(RoutingDecisionBase):
    """Complete routing decision model with timestamp"""
    id: Optional[str] = Field(None, alias="_id")
    created_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
