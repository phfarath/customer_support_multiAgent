"""
WhatsApp Business API models for webhook handling and message sending

Based on WhatsApp Cloud API documentation:
https://developers.facebook.com/docs/whatsapp/cloud-api/
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class WhatsAppMessageType(str, Enum):
    """Types of WhatsApp messages"""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    STICKER = "sticker"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    BUTTON = "button"
    REACTION = "reaction"
    UNKNOWN = "unknown"


class WhatsAppMessageStatus(str, Enum):
    """Status of WhatsApp messages"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


# ============================================================
# Webhook Payload Models (Incoming from WhatsApp)
# ============================================================

class WhatsAppProfile(BaseModel):
    """WhatsApp user profile"""
    name: str


class WhatsAppContact(BaseModel):
    """WhatsApp contact information"""
    profile: WhatsAppProfile
    wa_id: str = Field(..., description="WhatsApp ID (phone number without +)")


class WhatsAppTextContent(BaseModel):
    """Text message content"""
    body: str


class WhatsAppMediaContent(BaseModel):
    """Media message content (image, audio, video, document)"""
    id: str = Field(..., description="Media ID for downloading")
    mime_type: Optional[str] = None
    sha256: Optional[str] = None
    caption: Optional[str] = None
    filename: Optional[str] = None  # For documents


class WhatsAppLocationContent(BaseModel):
    """Location message content"""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


class WhatsAppInteractiveContent(BaseModel):
    """Interactive message response (button/list)"""
    type: str  # "button_reply" or "list_reply"
    button_reply: Optional[Dict[str, str]] = None  # {"id": "...", "title": "..."}
    list_reply: Optional[Dict[str, str]] = None  # {"id": "...", "title": "...", "description": "..."}


class WhatsAppButtonContent(BaseModel):
    """Button response content"""
    payload: str
    text: str


class WhatsAppReactionContent(BaseModel):
    """Reaction message content"""
    message_id: str
    emoji: str


class WhatsAppMessage(BaseModel):
    """Incoming WhatsApp message"""
    id: str = Field(..., description="Message ID")
    from_: str = Field(..., alias="from", description="Sender's WhatsApp ID")
    timestamp: str = Field(..., description="Unix timestamp string")
    type: WhatsAppMessageType

    # Optional content based on message type
    text: Optional[WhatsAppTextContent] = None
    image: Optional[WhatsAppMediaContent] = None
    audio: Optional[WhatsAppMediaContent] = None
    video: Optional[WhatsAppMediaContent] = None
    document: Optional[WhatsAppMediaContent] = None
    sticker: Optional[WhatsAppMediaContent] = None
    location: Optional[WhatsAppLocationContent] = None
    interactive: Optional[WhatsAppInteractiveContent] = None
    button: Optional[WhatsAppButtonContent] = None
    reaction: Optional[WhatsAppReactionContent] = None

    # Context for replies
    context: Optional[Dict[str, Any]] = None

    class Config:
        populate_by_name = True


class WhatsAppStatusUpdate(BaseModel):
    """Message status update from WhatsApp"""
    id: str = Field(..., description="Message ID")
    status: WhatsAppMessageStatus
    timestamp: str
    recipient_id: str
    conversation: Optional[Dict[str, Any]] = None
    pricing: Optional[Dict[str, Any]] = None
    errors: Optional[List[Dict[str, Any]]] = None


class WhatsAppMetadata(BaseModel):
    """Webhook metadata"""
    display_phone_number: str
    phone_number_id: str


class WhatsAppValue(BaseModel):
    """Value object in webhook payload"""
    messaging_product: str = "whatsapp"
    metadata: WhatsAppMetadata
    contacts: Optional[List[WhatsAppContact]] = None
    messages: Optional[List[WhatsAppMessage]] = None
    statuses: Optional[List[WhatsAppStatusUpdate]] = None
    errors: Optional[List[Dict[str, Any]]] = None


class WhatsAppChange(BaseModel):
    """Change object in webhook payload"""
    value: WhatsAppValue
    field: str = "messages"


class WhatsAppEntry(BaseModel):
    """Entry object in webhook payload"""
    id: str = Field(..., description="WhatsApp Business Account ID")
    changes: List[WhatsAppChange]


class WhatsAppWebhookPayload(BaseModel):
    """
    Full webhook payload from WhatsApp Cloud API

    Reference: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/payload-examples
    """
    object: str = "whatsapp_business_account"
    entry: List[WhatsAppEntry]


# ============================================================
# Outgoing Message Models (Sending to WhatsApp)
# ============================================================

class WhatsAppSendTextMessage(BaseModel):
    """Request to send a text message"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str = Field(..., description="Recipient's WhatsApp ID (phone number)")
    type: str = "text"
    text: Dict[str, Any] = Field(..., description="{'body': 'message text', 'preview_url': bool}")


class WhatsAppSendMediaMessage(BaseModel):
    """Request to send a media message"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str  # "image", "audio", "video", "document"
    # Dynamic field based on type
    image: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    video: Optional[Dict[str, Any]] = None
    document: Optional[Dict[str, Any]] = None


class WhatsAppSendTemplateMessage(BaseModel):
    """Request to send a template message"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "template"
    template: Dict[str, Any] = Field(
        ...,
        description="{'name': 'template_name', 'language': {'code': 'en_US'}, 'components': [...]}"
    )


class WhatsAppSendInteractiveMessage(BaseModel):
    """Request to send an interactive message (buttons, lists)"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "interactive"
    interactive: Dict[str, Any] = Field(
        ...,
        description="{'type': 'button'|'list', 'header': {...}, 'body': {...}, 'footer': {...}, 'action': {...}}"
    )


class WhatsAppSendReactionMessage(BaseModel):
    """Request to send a reaction to a message"""
    messaging_product: str = "whatsapp"
    recipient_type: str = "individual"
    to: str
    type: str = "reaction"
    reaction: Dict[str, str] = Field(
        ...,
        description="{'message_id': '...', 'emoji': '...'}"
    )


class WhatsAppMarkAsRead(BaseModel):
    """Request to mark a message as read"""
    messaging_product: str = "whatsapp"
    status: str = "read"
    message_id: str


# ============================================================
# API Response Models
# ============================================================

class WhatsAppSendMessageResponse(BaseModel):
    """Response from sending a message"""
    messaging_product: str
    contacts: List[Dict[str, str]]  # [{"input": "...", "wa_id": "..."}]
    messages: List[Dict[str, str]]  # [{"id": "wamid.xxx"}]


class WhatsAppError(BaseModel):
    """WhatsApp API error"""
    code: int
    title: str
    message: Optional[str] = None
    error_data: Optional[Dict[str, Any]] = None


class WhatsAppErrorResponse(BaseModel):
    """Error response from WhatsApp API"""
    error: WhatsAppError


# ============================================================
# Parsed Message Model (Internal use)
# ============================================================

class WhatsAppParsedMessage(BaseModel):
    """
    Parsed message for internal processing.
    Normalized format similar to TelegramAdapter output.
    """
    external_user_id: str = Field(..., description="whatsapp:{wa_id}")
    text: str = Field(..., description="Message text or caption")
    message_type: WhatsAppMessageType
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # Original message data
    message_id: str
    wa_id: str  # Sender's WhatsApp ID
    phone_number_id: str  # Business phone number ID
    timestamp: datetime

    # Optional fields
    sender_name: Optional[str] = None
    media_id: Optional[str] = None
    media_url: Optional[str] = None
    is_reply: bool = False
    reply_to_message_id: Optional[str] = None
