"""
Channel adapters for external integrations
"""
from .telegram_adapter import TelegramAdapter
from .whatsapp_adapter import WhatsAppAdapter

__all__ = ["TelegramAdapter", "WhatsAppAdapter"]
