"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB Configuration
    mongodb_uri: str
    database_name: str = "customer_support"
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-5-nano"
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    
    # Telegram Configuration
    telegram_bot_token: Optional[str] = None
    telegram_polling_timeout: int = 30
    
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
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()
