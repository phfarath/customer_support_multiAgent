"""
Ingest message models for channel-agnostic message ingestion
"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class IngestChannel(str, Enum):
    """Supported channels for message ingestion"""
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    CHAT = "chat"
    PHONE = "phone"


class IngestMessageRequest(BaseModel):
    """Request model for ingesting a message from any channel"""
    channel: IngestChannel = Field(..., description="Channel where the message originated")
    external_user_id: str = Field(..., description="External user ID from the channel (e.g., telegram:1234567)")
    text: str = Field(..., description="Message text content")
    metadata: Optional[dict] = Field(default_factory=dict, description="Additional channel-specific metadata")


class IngestMessageResponse(BaseModel):
    """Response model for message ingestion"""
    success: bool
    ticket_id: Optional[str] = None
    reply_text: Optional[str] = None
    escalated: bool = False
    message: str
    ticket_status: Optional[str] = None
