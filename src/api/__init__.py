"""
API endpoints
"""
from .routes import router
from .ingest_routes import router as ingest_router
from .telegram_routes import router as telegram_router
from .whatsapp_routes import router as whatsapp_router
from .company_routes import router as company_router
from .human_routes import router as human_router

__all__ = [
    "router",
    "ingest_router",
    "telegram_router",
    "whatsapp_router",
    "company_router",
    "human_router",
]

