"""
Company Configuration Model
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


class Team(BaseModel):
    """Team definition for routing and responsibilities"""
    team_id: str = Field(..., description="Unique team identifier (e.g. 'sales', 'tech')")
    name: str = Field(..., description="Display name")
    description: str = Field(..., description="Description for Router Agent")
    responsibilities: List[str] = Field(default_factory=list, description="List of key responsibilities")
    instructions: Optional[str] = Field(None, description="Specific instructions for agents acting in this team")
    is_sales: bool = Field(False, description="Flag for specific sales logic")


class KnowledgeBaseConfig(BaseModel):
    """Configuration for RAG/Knowledge Base"""
    enabled: bool = Field(False, description="Whether KB lookup is enabled")
    sources: List[str] = Field(default_factory=list, description="List of sources (manuals, policies)")
    vector_db_collection: str = Field("company_knowledge", description="Collection name in Vector DB")


class IntegrationConfig(BaseModel):
    """Configuration for external integrations"""
    telegram_bot_token: Optional[str] = Field(None, description="Telegram Bot Token")
    whatsapp_api_key: Optional[str] = Field(None, description="WhatsApp API Key")


class TicketLifecycleConfig(BaseModel):
    """Automatic follow-up and closure behavior for escalated tickets."""
    followup_1_hours: int = Field(24, description="Hours after escalation to send first follow-up")
    followup_2_hours: int = Field(48, description="Hours after escalation to send second follow-up")
    auto_close_hours: int = Field(72, description="Hours after escalation to auto-close the ticket")

    followup_1_message: str = Field(
        "Olá! Conseguimos resolver o problema que você reportou? "
        "Se sim, pode confirmar para fecharmos o atendimento? 😊",
        description="First follow-up message",
    )
    followup_2_message: str = Field(
        "Caso não recebamos retorno em até 24h, marcaremos este atendimento como resolvido. "
        "Você pode reabrir a qualquer momento se precisar! 📝",
        description="Second follow-up message",
    )
    auto_close_message: str = Field(
        "Como não recebemos retorno, marcamos este atendimento como resolvido. "
        "Se precisar de ajuda, é só nos chamar novamente! 👋",
        description="Message sent when ticket is auto-closed",
    )

    enable_auto_followup: bool = Field(True, description="Enable automated follow-up messages")
    enable_auto_close: bool = Field(True, description="Enable automatic ticket closure")
    reopen_on_customer_reply: bool = Field(True, description="Reopen auto-closed ticket on customer reply")
    

class CompanyConfig(BaseModel):
    """Company configuration for multi-tenancy support"""
    
    company_id: str = Field(..., description="Unique company identifier")
    company_name: str = Field(..., description="Company name")
    
    # Contact Information
    support_email: Optional[str] = Field(None, description="Support email")
    support_phone: Optional[str] = Field(None, description="Support phone")
    
    # Policies
    refund_policy: Optional[str] = Field(None, description="Refund policy text")
    cancellation_policy: Optional[str] = Field(None, description="Cancellation policy text")
    payment_methods: Optional[List[str]] = Field(default_factory=list, description="Accepted payment methods")
    
    # Products/Services
    products: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="List of products/services")
    
    # Services
    services: Optional[List[str]] = Field(default_factory=list, description="Available services")
    
    # Business Hours
    business_hours: Optional[Dict[str, str]] = Field(None, description="Business hours")
    
    # Teams & Routing
    teams: List[Team] = Field(default_factory=list, description="Teams structure")
    
    # Integrations
    knowledge_base: Optional[KnowledgeBaseConfig] = Field(default_factory=KnowledgeBaseConfig, description="Knowledge Base Config")
    integrations: Optional[IntegrationConfig] = Field(default_factory=IntegrationConfig, description="Integration credentials")
    lifecycle_config: TicketLifecycleConfig = Field(default_factory=TicketLifecycleConfig, description="Ticket lifecycle automation")
    
    # Custom Instructions (Global)
    custom_instructions: Optional[str] = Field(
        None, 
        description="Global custom instructions for agents"
    )
    
    # Bot Configuration
    bot_name: Optional[str] = Field(None, description="Bot display name")
    bot_welcome_message: Optional[str] = Field(
        None, 
        description="Welcome message when starting new conversation"
    )
    bot_outside_hours_message: Optional[str] = Field(
        None,
        description="Message shown outside business hours"
    )
    bot_handoff_message: Optional[str] = Field(
        None,
        description="Message shown when a ticket is escalated to a human"
    )
    handoff_warning_message: Optional[str] = Field(
        None,
        description="Warning message sent BEFORE escalation explaining why (supports {reason} placeholder)"
    )
    
    # Escalation
    escalation_contact: Optional[str] = Field(None, description="Telegram Group/Chat ID for human escalation")
    escalation_email: Optional[str] = Field(None, description="Email for human escalation notifications")
    
    class Config:
        populate_by_name = True


class CompanyConfigCreate(BaseModel):
    """Model for creating a new company configuration"""
    
    company_id: str
    company_name: str
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    refund_policy: Optional[str] = None
    cancellation_policy: Optional[str] = None
    payment_methods: Optional[List[str]] = None
    products: Optional[List[Dict[str, Any]]] = None
    services: Optional[List[str]] = None
    business_hours: Optional[Dict[str, str]] = None
    custom_instructions: Optional[str] = None
    bot_name: Optional[str] = None
    bot_welcome_message: Optional[str] = None
    bot_outside_hours_message: Optional[str] = None
    bot_handoff_message: Optional[str] = None
    handoff_warning_message: Optional[str] = None
    
    # New fields
    teams: Optional[List[Team]] = None
    knowledge_base: Optional[KnowledgeBaseConfig] = None
    integrations: Optional[IntegrationConfig] = None
    escalation_contact: Optional[str] = None
    escalation_email: Optional[str] = None
    lifecycle_config: Optional[TicketLifecycleConfig] = None


class CompanyConfigUpdate(BaseModel):
    """Model for updating company configuration"""
    
    company_name: Optional[str] = None
    support_email: Optional[str] = None
    support_phone: Optional[str] = None
    refund_policy: Optional[str] = None
    cancellation_policy: Optional[str] = None
    payment_methods: Optional[List[str]] = None
    products: Optional[List[Dict[str, Any]]] = None
    services: Optional[List[str]] = None
    business_hours: Optional[Dict[str, str]] = None
    custom_instructions: Optional[str] = None
    bot_name: Optional[str] = None
    bot_welcome_message: Optional[str] = None
    bot_outside_hours_message: Optional[str] = None
    bot_handoff_message: Optional[str] = None
    handoff_warning_message: Optional[str] = None
    
    # New fields
    teams: Optional[List[Team]] = None
    knowledge_base: Optional[KnowledgeBaseConfig] = None
    integrations: Optional[IntegrationConfig] = None
    escalation_contact: Optional[str] = None
    escalation_email: Optional[str] = None
    lifecycle_config: Optional[TicketLifecycleConfig] = None
