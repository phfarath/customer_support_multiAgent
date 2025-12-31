"""
Audit log models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class AuditOperation(str, Enum):
    """Audit operation types"""
    UPDATE_PRIORITY = "UPDATE_PRIORITY"
    ROUTE_TO_TEAM = "ROUTE_TO_TEAM"
    ESCALATE = "ESCALATE"
    CREATE_TICKET = "CREATE_TICKET"
    UPDATE_STATUS = "UPDATE_STATUS"
    AGENT_EXECUTION = "AGENT_EXECUTION"


class AuditLogBase(BaseModel):
    """Base audit log model"""
    ticket_id: str
    agent_name: str
    operation: AuditOperation
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None


class AuditLogCreate(AuditLogBase):
    """Model for creating a new audit log"""
    pass


class AuditLog(AuditLogBase):
    """Complete audit log model with timestamp"""
    id: Optional[str] = Field(None, alias="_id")
    timestamp: Optional[datetime] = None

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
