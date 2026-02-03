"""
Main FastAPI application for MultiAgent Customer Support System
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from src.config import settings
from src.database import ensure_indexes, close_connection
from src.api import router, ingest_router, telegram_router, company_router, human_router
from src.api.api_key_routes import router as api_key_router
from src.api.health_routes import router as health_router
from src.utils.monitoring import init_sentry, flush_events
from src.utils.secure_logging import configure_secure_logging
from src.middleware.rate_limiter import get_rate_limit_key
from src.middleware.cors import get_cors_origins
from src.middleware.security_headers import SecurityHeadersMiddleware
from src.security.error_handler import secure_exception_handler

# Configure secure logging (masks sensitive data automatically)
configure_secure_logging(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format_type='text',  # Use 'json' in production for log aggregation
    include_trace_id=True,
)

# Initialize rate limiter with fingerprint-based key (IP + User-Agent + API Key)
limiter = Limiter(key_func=get_rate_limit_key, default_limits=["100/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("Starting MultiAgent Customer Support System...")

    # Initialize Sentry for error tracking and performance monitoring
    init_sentry()

    # Setup database indexes
    await ensure_indexes()
    print("Database indexes created/verified")

    yield

    # Shutdown
    print("Shutting down...")
    
    # Cleanup HTTP clients
    from src.utils.http_client import cleanup_http_clients
    await cleanup_http_clients()
    print("HTTP clients closed")

    # Flush pending Sentry events
    flush_events(timeout=2.0)

    # Close database connection
    await close_connection()
    print("Database connection closed")


# Create FastAPI app
app = FastAPI(
    title="MultiAgent Customer Support System",
    description="AI-powered customer support with multiple specialized agents",
    version="0.1.0",
    lifespan=lifespan
)

# Add rate limiter to app state
app.state.limiter = limiter

# Add exception handler for rate limit exceeded
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add SlowAPI middleware
app.add_middleware(SlowAPIMiddleware)

# Add CORS middleware (HARDENED - specific origins only, localhost filtered in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),              # Whitelist specific origins (localhost filtered in production)
    allow_credentials=True,                        # Allow credentials (cookies, authorization headers)
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Specific methods only
    allow_headers=[                                # Specific headers only
        "Content-Type",
        "X-API-Key",
        "Authorization",
        "Accept",
        "Origin",
    ],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining"],  # Expose rate limit info
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Add Security Headers middleware (CSP, X-Frame-Options, HSTS, etc.)
app.add_middleware(
    SecurityHeadersMiddleware,
    environment=settings.environment,
    excluded_paths=["/health", "/api/health", "/metrics"],
)

# Add global exception handler (never exposes internal details)
app.add_exception_handler(Exception, secure_exception_handler)

# Include routes
app.include_router(health_router)  # Health checks (no auth required)
app.include_router(router)
app.include_router(ingest_router)
app.include_router(telegram_router)
app.include_router(company_router)
app.include_router(human_router)
app.include_router(api_key_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MultiAgent Customer Support System",
        "version": "0.1.0",
        "status": "running",
        "endpoints": {
            "health": "/api/health",
            "create_ticket": "POST /api/tickets",
            "run_pipeline": "POST /api/run_pipeline/{ticket_id}",
            "get_ticket": "GET /api/tickets/{ticket_id}",
            "get_audit": "GET /api/tickets/{ticket_id}/audit",
            "list_tickets": "GET /api/tickets",
            "ingest_message": "POST /api/ingest-message",
            "telegram_webhook": "POST /telegram/webhook"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload
    )
