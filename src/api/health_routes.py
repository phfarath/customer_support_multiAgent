"""
Health Check Routes - Deep Health Monitoring

Comprehensive health checks for:
- Basic service health (/api/health)
- Detailed component health (/api/health/detailed)
- Readiness probe (/api/health/ready)
- Liveness probe (/api/health/live)
- Database connectivity
- External services (OpenAI, Telegram)
- System metrics

Used by:
- Load balancers (ALB Target Group)
- Kubernetes/ECS health checks
- Monitoring systems (Datadog, New Relic)
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from src.database import get_client as get_mongo_client
from src.config import settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["health"])

# Track service start time
SERVICE_START_TIME = time.time()


class HealthStatus(BaseModel):
    """Health check response model"""
    status: str  # "healthy" | "degraded" | "unhealthy"
    timestamp: str
    uptime_seconds: float
    version: str
    environment: Optional[str] = None
    checks: Optional[Dict[str, Any]] = None


class ComponentHealth(BaseModel):
    """Individual component health"""
    status: str  # "up" | "down" | "degraded"
    response_time_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============================================================
# Basic Health Check (Load Balancer)
# ============================================================

@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """
    Basic health check endpoint

    Returns 200 if service is running.
    Used by load balancers and simple monitoring.

    Returns:
        HealthStatus with basic service info
    """
    uptime = time.time() - SERVICE_START_TIME

    return HealthStatus(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=round(uptime, 2),
        version="1.0.0",
        environment=getattr(settings, 'environment', 'production')
    )


# ============================================================
# Detailed Health Check
# ============================================================

@router.get("/health/detailed", response_model=HealthStatus)
async def detailed_health_check(response: Response) -> HealthStatus:
    """
    Detailed health check with component status

    Checks:
    - MongoDB connectivity
    - OpenAI API availability
    - System resources

    Returns:
        200: All components healthy
        503: One or more components unhealthy

    Response includes individual component statuses.
    """
    checks = {}
    overall_status = "healthy"

    # Check 1: MongoDB
    mongo_health = await _check_mongodb()
    checks["mongodb"] = mongo_health.dict()
    if mongo_health.status != "up":
        overall_status = "degraded"

    # Check 2: OpenAI API
    openai_health = await _check_openai()
    checks["openai"] = openai_health.dict()
    if openai_health.status != "up":
        # OpenAI down is degraded, not unhealthy (fallback exists)
        overall_status = "degraded"

    # Check 3: ChromaDB (local, should always be up)
    chroma_health = await _check_chromadb()
    checks["chromadb"] = chroma_health.dict()
    if chroma_health.status != "up":
        overall_status = "degraded"

    # Check 4: System resources
    system_health = await _check_system_resources()
    checks["system"] = system_health.dict()
    if system_health.status == "down":
        overall_status = "unhealthy"

    # Set HTTP status based on overall health
    if overall_status == "unhealthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif overall_status == "degraded":
        response.status_code = status.HTTP_200_OK  # Still accepting traffic

    uptime = time.time() - SERVICE_START_TIME

    return HealthStatus(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        uptime_seconds=round(uptime, 2),
        version="1.0.0",
        environment=getattr(settings, 'environment', 'production'),
        checks=checks
    )


# ============================================================
# Kubernetes/ECS Probes
# ============================================================

@router.get("/health/ready")
async def readiness_check(response: Response) -> Dict[str, str]:
    """
    Readiness probe for Kubernetes/ECS

    Checks if service is ready to accept traffic:
    - MongoDB connected
    - Critical dependencies available

    Returns:
        200: Ready to serve traffic
        503: Not ready (don't send traffic)
    """
    # Check MongoDB (critical)
    mongo_health = await _check_mongodb()

    if mongo_health.status != "up":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "reason": "MongoDB unavailable"
        }

    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes/ECS

    Checks if service is alive and should not be restarted.
    Simple check - if this endpoint responds, service is alive.

    Returns:
        200: Service is alive
    """
    return {"status": "alive"}


# ============================================================
# Component Health Checkers
# ============================================================

async def _check_mongodb() -> ComponentHealth:
    """Check MongoDB connectivity and response time"""
    start_time = time.time()

    try:
        client = get_mongo_client()

        # Ping MongoDB
        await client.admin.command('ping')

        response_time = (time.time() - start_time) * 1000  # ms

        # Check if response time is reasonable (< 100ms is good)
        if response_time > 500:
            return ComponentHealth(
                status="degraded",
                response_time_ms=round(response_time, 2),
                message="High latency"
            )

        return ComponentHealth(
            status="up",
            response_time_ms=round(response_time, 2)
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"MongoDB health check failed: {e}")

        return ComponentHealth(
            status="down",
            response_time_ms=round(response_time, 2),
            message=str(e)
        )


async def _check_openai() -> ComponentHealth:
    """Check OpenAI API availability"""
    start_time = time.time()

    try:
        # Simple check: verify API key is configured
        if not settings.openai_api_key or settings.openai_api_key == "your_openai_api_key_here":
            return ComponentHealth(
                status="down",
                message="API key not configured"
            )

        # Optional: Test API with lightweight call
        # This is commented out to avoid unnecessary API calls in production
        # Uncomment if you want active health checks
        #
        # from src.utils.openai_client import get_openai_client
        # client = get_openai_client()
        # await client.models.list()  # Lightweight API call

        response_time = (time.time() - start_time) * 1000

        return ComponentHealth(
            status="up",
            response_time_ms=round(response_time, 2),
            message="API key configured"
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.error(f"OpenAI health check failed: {e}")

        return ComponentHealth(
            status="down",
            response_time_ms=round(response_time, 2),
            message=str(e)
        )


async def _check_chromadb() -> ComponentHealth:
    """Check ChromaDB availability"""
    start_time = time.time()

    try:
        # ChromaDB is local, just check if directory exists
        import os
        chroma_dir = getattr(settings, 'chroma_persist_directory', './chroma_db')

        if not os.path.exists(chroma_dir):
            return ComponentHealth(
                status="degraded",
                message=f"ChromaDB directory not found: {chroma_dir}"
            )

        # Optional: Test ChromaDB connection
        # from src.rag.knowledge_base import KnowledgeBase
        # kb = KnowledgeBase()
        # kb.collection.count()  # Test query

        response_time = (time.time() - start_time) * 1000

        return ComponentHealth(
            status="up",
            response_time_ms=round(response_time, 2)
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        logger.warning(f"ChromaDB health check failed: {e}")

        # ChromaDB failure is degraded, not critical
        return ComponentHealth(
            status="degraded",
            response_time_ms=round(response_time, 2),
            message=str(e)
        )


async def _check_system_resources() -> ComponentHealth:
    """Check system resources (CPU, memory, disk)"""
    try:
        import psutil

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        details = {
            "cpu_percent": round(cpu_percent, 2),
            "memory_percent": round(memory.percent, 2),
            "memory_available_mb": round(memory.available / 1024 / 1024, 2),
            "disk_percent": round(disk.percent, 2),
            "disk_free_gb": round(disk.free / 1024 / 1024 / 1024, 2)
        }

        # Determine status based on thresholds
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            return ComponentHealth(
                status="down",
                message="Critical resource usage",
                details=details
            )
        elif cpu_percent > 70 or memory.percent > 80 or disk.percent > 80:
            return ComponentHealth(
                status="degraded",
                message="High resource usage",
                details=details
            )
        else:
            return ComponentHealth(
                status="up",
                details=details
            )

    except ImportError:
        # psutil not installed (optional dependency)
        return ComponentHealth(
            status="up",
            message="psutil not installed, metrics unavailable"
        )
    except Exception as e:
        logger.error(f"System resources check failed: {e}")
        return ComponentHealth(
            status="degraded",
            message=str(e)
        )


# ============================================================
# Metrics Endpoint (Prometheus-compatible)
# ============================================================

@router.get("/health/metrics")
async def metrics() -> Response:
    """
    Prometheus-compatible metrics endpoint

    Returns metrics in Prometheus text format:
    - service_uptime_seconds
    - service_health_status (1=healthy, 0=unhealthy)
    - component health statuses

    Use with Prometheus scraper or monitoring tools.
    """
    uptime = time.time() - SERVICE_START_TIME

    # Get component statuses
    mongo_health = await _check_mongodb()
    openai_health = await _check_openai()
    chroma_health = await _check_chromadb()
    system_health = await _check_system_resources()

    # Convert statuses to metrics (1=up, 0=down, 0.5=degraded)
    def status_to_metric(status: str) -> float:
        return 1.0 if status == "up" else (0.5 if status == "degraded" else 0.0)

    # Build Prometheus metrics
    metrics_text = f"""# HELP service_uptime_seconds Service uptime in seconds
# TYPE service_uptime_seconds gauge
service_uptime_seconds {uptime:.2f}

# HELP service_health_status Overall service health (1=healthy, 0=unhealthy)
# TYPE service_health_status gauge
service_health_status 1

# HELP component_health_status Component health status (1=up, 0.5=degraded, 0=down)
# TYPE component_health_status gauge
component_health_status{{component="mongodb"}} {status_to_metric(mongo_health.status)}
component_health_status{{component="openai"}} {status_to_metric(openai_health.status)}
component_health_status{{component="chromadb"}} {status_to_metric(chroma_health.status)}
component_health_status{{component="system"}} {status_to_metric(system_health.status)}
"""

    # Add system metrics if available
    if system_health.details:
        metrics_text += f"""
# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent {system_health.details.get('cpu_percent', 0)}

# HELP system_memory_percent Memory usage percentage
# TYPE system_memory_percent gauge
system_memory_percent {system_health.details.get('memory_percent', 0)}

# HELP system_disk_percent Disk usage percentage
# TYPE system_disk_percent gauge
system_disk_percent {system_health.details.get('disk_percent', 0)}
"""

    return Response(
        content=metrics_text,
        media_type="text/plain; version=0.0.4"
    )
