"""
User model for dashboard authentication
"""
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from passlib.context import CryptContext
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel):
    """Dashboard user model"""
    user_id: str = Field(default_factory=lambda: f"user_{secrets.token_hex(8)}")
    email: EmailStr
    password_hash: str
    company_id: str
    full_name: str
    role: str = "operator"  # operator | admin
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    last_login_at: Optional[datetime] = None

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password with bcrypt

        Args:
            password: Plain text password

        Returns:
            Hashed password

        Note:
            bcrypt has a 72-byte limit. Passwords are automatically truncated.
        """
        # Truncate password to 72 bytes (bcrypt limit)
        # This is safe because we're using UTF-8 encoding
        password_bytes = password.encode('utf-8')[:72]
        password_truncated = password_bytes.decode('utf-8', errors='ignore')
        return pwd_context.hash(password_truncated)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify password against hash

        Args:
            plain_password: Plain text password
            hashed_password: Hashed password from database

        Returns:
            True if password matches, False otherwise

        Note:
            Passwords are truncated to 72 bytes to match bcrypt's limit
        """
        # Apply same truncation as hash_password
        password_bytes = plain_password.encode('utf-8')[:72]
        password_truncated = password_bytes.decode('utf-8', errors='ignore')
        return pwd_context.verify(password_truncated, hashed_password)

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_a1b2c3d4e5f6g7h8",
                "email": "admin@techcorp.com",
                "company_id": "techcorp_001",
                "full_name": "Admin User",
                "role": "admin",
                "active": True
            }
        }


class UserCreate(BaseModel):
    """User creation request"""
    email: EmailStr
    password: str
    company_id: str
    full_name: str
    role: str = "operator"

    class Config:
        json_schema_extra = {
            "example": {
                "email": "operator@techcorp.com",
                "password": "SecurePassword123!",
                "company_id": "techcorp_001",
                "full_name": "Operator User",
                "role": "operator"
            }
        }
