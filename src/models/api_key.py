"""
API Key Model for Authentication
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
import secrets


class APIKey(BaseModel):
    """API Key for authentication"""
    key_id: str = Field(default_factory=lambda: f"key_{secrets.token_hex(8)}")
    api_key: str = Field(default_factory=lambda: f"sk_{secrets.token_urlsafe(32)}")
    company_id: str  # Isolation per company
    name: str  # Description (e.g., "Production API", "Telegram Integration")
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None  # Optional expiration
    permissions: list[str] = ["read", "write"]  # Future: granular permissions

    class Config:
        json_schema_extra = {
            "example": {
                "key_id": "key_a1b2c3d4",
                "api_key": "sk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890",
                "company_id": "techcorp_001",
                "name": "Production API",
                "active": True,
                "permissions": ["read", "write"]
            }
        }
