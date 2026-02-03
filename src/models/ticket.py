"""
Ticket models
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from enum import Enum


class TicketCategory(str, Enum):
    """Ticket category values"""
    BILLING = "billing"
    TECH = "tech"
    GENERAL = "general"


class TicketStatus(str, Enum):
    """Ticket status values"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    ESCALATED = "escalated"
    RESOLVED = "resolved"


class TicketPriority(str, Enum):
    """Ticket priority levels"""
    P1 = "P1"  # Critical
    P2 = "P2"  # High
    P3 = "P3"  # Normal


class TicketPhase(str, Enum):
    """Ticket processing phases"""
    TRIAGE = "triage"
    ROUTING = "routing"
    RESOLUTION = "resolution"
    ESCALATION = "escalation"


class TicketChannel(str, Enum):
    """Communication channels"""
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"


class TicketBase(BaseModel):
    """Base ticket model"""
    ticket_id: str
    customer_id: str
    company_id: Optional[str] = None
    channel: TicketChannel
    external_user_id: Optional[str] = None
    subject: str
    description: str
    priority: TicketPriority = TicketPriority.P3
    status: TicketStatus = TicketStatus.OPEN
    current_phase: TicketPhase = TicketPhase.TRIAGE
    interactions_count: int = 0
    category: Optional[TicketCategory] = None
    tags: List[str] = Field(default_factory=list)


class TicketCreate(TicketBase):
    """Model for creating a new ticket"""
    pass


class TicketUpdate(BaseModel):
    """Model for updating a ticket"""
    priority: Optional[TicketPriority] = None
    status: Optional[TicketStatus] = None
    current_phase: Optional[TicketPhase] = None
    interactions_count: Optional[int] = None
    lock_version: Optional[int] = None
    category: Optional[TicketCategory] = None
    tags: Optional[List[str]] = None


class Ticket(TicketBase):
    """Complete ticket model with timestamps"""
    id: Optional[str] = Field(None, alias="_id")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    lock_version: int = 0

    class Config:
        populate_by_name = True
        json_encoders = {datetime: lambda v: v.isoformat()}
