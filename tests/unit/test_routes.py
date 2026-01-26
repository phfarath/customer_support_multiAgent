from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

import pytest

from src.api.routes import router as tickets_router
from src.api.ingest_routes import router as ingest_router
from src.middleware.auth import verify_api_key
from src.database import COLLECTION_TICKETS, COLLECTION_INTERACTIONS, COLLECTION_AUDIT_LOGS
from src.models import TicketStatus


def build_app():
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(tickets_router)
    app.include_router(ingest_router)
    app.dependency_overrides[verify_api_key] = lambda: {"company_id": "comp_001"}
    return app


@pytest.mark.unit
def test_create_ticket_success(fake_db):
    app = build_app()
    client = TestClient(app)

    fake_db[COLLECTION_TICKETS].find_one_result = None

    payload = {
        "ticket_id": "T-100",
        "customer_id": "C-1",
        "channel": "telegram",
        "subject": "Ajuda",
        "description": "Preciso de suporte",
        "company_id": "comp_001",
    }

    response = client.post("/api/tickets", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["ticket_id"] == "T-100"
    assert fake_db[COLLECTION_TICKETS].inserted
    assert fake_db[COLLECTION_AUDIT_LOGS].inserted


@pytest.mark.unit
def test_create_ticket_company_mismatch_returns_403(fake_db):
    app = build_app()
    client = TestClient(app)

    payload = {
        "ticket_id": "T-200",
        "customer_id": "C-1",
        "channel": "telegram",
        "subject": "Ajuda",
        "description": "Preciso de suporte",
        "company_id": "other_company",
    }

    response = client.post("/api/tickets", json=payload)

    assert response.status_code == 403


@pytest.mark.unit
def test_run_pipeline_returns_results(fake_db, monkeypatch):
    app = build_app()
    client = TestClient(app)

    fake_db[COLLECTION_TICKETS].find_one_result = {
        "ticket_id": "T-300",
        "company_id": "comp_001",
    }

    async def fake_run_pipeline(self, ticket_id: str):
        return {"ticket_id": ticket_id, "final_status": "in_progress"}

    monkeypatch.setattr("src.api.routes.AgentPipeline.run_pipeline", fake_run_pipeline)

    response = client.post("/api/run_pipeline/T-300")

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["results"]["final_status"] == "in_progress"


@pytest.mark.unit
def test_get_ticket_not_found_returns_404(fake_db):
    app = build_app()
    client = TestClient(app)

    fake_db[COLLECTION_TICKETS].find_one_result = None

    response = client.get("/api/tickets/T-404")

    assert response.status_code == 404


@pytest.mark.unit
def test_list_tickets_returns_count(fake_db):
    app = build_app()
    client = TestClient(app)

    fake_db[COLLECTION_TICKETS].find_results = [
        {"_id": "1", "ticket_id": "T-1", "company_id": "comp_001"},
        {"_id": "2", "ticket_id": "T-2", "company_id": "comp_001"},
    ]

    response = client.get("/api/tickets")

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2


@pytest.mark.unit
def test_ingest_message_success_non_escalated(fake_db, monkeypatch):
    app = build_app()
    client = TestClient(app)

    async def fake_find_or_create_ticket(*args, **kwargs):
        return ({"ticket_id": "T-500", "status": TicketStatus.OPEN, "company_id": "comp_001"}, True)

    interactions = []

    async def fake_add_interaction(*args, **kwargs):
        interactions.append(kwargs)
        return {"_id": "i1"}

    async def fake_update_ticket_interactions_count(*args, **kwargs):
        return None

    async def fake_update_ticket_status(*args, **kwargs):
        return None

    class FakePipeline:
        async def run_pipeline(self, ticket_id: str):
            return {
                "resolution": {"decisions": {"response": "Resposta"}},
                "escalation": {"escalate_to_human": False, "decisions": {}},
            }

    monkeypatch.setattr("src.api.ingest_routes.find_or_create_ticket", fake_find_or_create_ticket)
    monkeypatch.setattr("src.api.ingest_routes.add_interaction", fake_add_interaction)
    monkeypatch.setattr("src.api.ingest_routes.update_ticket_interactions_count", fake_update_ticket_interactions_count)
    monkeypatch.setattr("src.api.ingest_routes.update_ticket_status", fake_update_ticket_status)
    monkeypatch.setattr("src.api.ingest_routes.AgentPipeline", lambda: FakePipeline())

    payload = {
        "channel": "telegram",
        "external_user_id": "user_1",
        "text": "Oi",
        "company_id": "comp_001",
    }

    response = client.post("/api/ingest-message", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["ticket_id"] == "T-500"
    assert data["reply_text"] == "Resposta"
    assert interactions
