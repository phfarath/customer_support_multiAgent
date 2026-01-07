"""
Company Configuration Model
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List


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
    
    # Custom Instructions
    custom_instructions: Optional[str] = Field(
        None, 
        description="Custom instructions for agents"
    )
    
    # Bot Configuration
    bot_name: Optional[str] = Field(None, description="Bot display name")
    bot_welcome_message: Optional[str] = Field(
        None, 
        description="Welcome message when starting new conversation"
    )
    
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
