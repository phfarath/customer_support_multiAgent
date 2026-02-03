"""
Application Configuration
"""
import json
from pydantic_settings import BaseSettings
from pydantic import model_validator, field_validator
from typing import Optional, List, Any


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Environment Configuration
    environment: str = "development"  # development, staging, production

    # MongoDB Configuration
    mongodb_uri: str
    database_name: str = "customer_support"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Telegram Configuration
    telegram_bot_token: Optional[str] = None
    telegram_polling_timeout: int = 30
    telegram_webhook_secret: Optional[str] = None  # Required in production for webhook verification

    # JWT Configuration (for dashboard authentication)
    jwt_secret_key: str = "CHANGE_THIS_IN_PRODUCTION"  # Must be set in .env
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24

    # SMTP Configuration (for escalation emails)
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None
    smtp_use_tls: bool = True
    escalation_default_email: Optional[str] = None
    escalation_handoff_message: str = (
        "Sua solicitacao foi encaminhada para um atendente humano. "
        "Ticket: {ticket_id}. Em breve responderemos por aqui."
    )
    
    # Bot Business Logic
    bot_require_phone: bool = True
    bot_rate_limit_messages: int = 10      # Max messages
    bot_rate_limit_window: int = 60        # Per minute (seconds)
    bot_rate_limit_block_time: int = 300   # Block for 5 min (seconds)
    bot_default_company_id: Optional[str] = None  # Default company if not identified
    
    # Agent Configuration
    escalation_max_interactions: int = 2
    escalation_min_confidence: float = 0.6
    escalation_min_sentiment: float = -0.7
    escalation_sla_hours: int = 4

    # Rate Limiting Configuration (API protection)
    rate_limit_default: str = "100/minute"  # Default rate limit for endpoints
    rate_limit_ingest: str = "20/minute"    # Message ingestion (prevents spam)
    rate_limit_pipeline: str = "10/minute"  # Pipeline execution (expensive)
    rate_limit_read: str = "200/minute"     # Read-only operations
    rate_limit_write: str = "30/minute"     # Write operations
    rate_limit_admin: str = "10/minute"     # Admin operations (create/delete configs)

    # CORS Configuration (Cross-Origin Resource Sharing)
    cors_allowed_origins: List[str] = [
        "http://localhost:3000",      # React dev server
        "http://localhost:8501",      # Streamlit dashboard
        "http://127.0.0.1:3000",      # Alternative localhost
        "http://127.0.0.1:8501",      # Alternative localhost
        # Production domains should be added via environment variable
        # Example: CORS_ALLOWED_ORIGINS=https://dashboard.yourdomain.com,https://api.yourdomain.com
    ]

    # Logging
    log_level: str = "INFO"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def parse_cors_allowed_origins(cls, v: Any) -> Any:
        # Accept comma-separated strings or JSON arrays in env vars.
        if v is None:
            return v
        if isinstance(v, str):
            raw = v.strip()
            if not raw:
                return []
            if raw.startswith("["):
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in raw.split(",") if item.strip()]
        return v

    @model_validator(mode='after')
    def validate_production_settings(self) -> 'Settings':
        """Validate security-critical settings in production environment"""
        if self.environment == "production":
            # Validate JWT secret
            if self.jwt_secret_key == "CHANGE_THIS_IN_PRODUCTION":
                raise ValueError(
                    "JWT_SECRET_KEY must be changed from default value in production. "
                    "Generate a secure random string of at least 32 characters."
                )
            if len(self.jwt_secret_key) < 32:
                raise ValueError(
                    f"JWT_SECRET_KEY must be at least 32 characters in production "
                    f"(current: {len(self.jwt_secret_key)} chars)"
                )

            # Validate Telegram webhook secret
            if not self.telegram_webhook_secret:
                raise ValueError(
                    "TELEGRAM_WEBHOOK_SECRET is required in production for webhook security. "
                    "Set this when configuring the Telegram webhook."
                )

            # Validate CORS origins (no localhost in production)
            localhost_origins = [
                o for o in self.cors_allowed_origins
                if "localhost" in o or "127.0.0.1" in o
            ]
            if localhost_origins:
                raise ValueError(
                    f"CORS_ALLOWED_ORIGINS contains localhost origins in production: {localhost_origins}. "
                    "Remove localhost origins and use production domain names."
                )
            if not self.cors_allowed_origins:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS cannot be empty in production. "
                    "Add your production domain(s)."
                )

        return self

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
