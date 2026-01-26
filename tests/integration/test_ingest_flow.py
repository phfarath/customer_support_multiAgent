from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

import pytest

from src.api.ingest_routes import router as ingest_router
from src.middleware.auth import verify_api_key
from src.database import COLLECTION_TICKETS, COLLECTION_INTERACTIONS, COLLECTION_AUDIT_LOGS


def build_app():
    app = FastAPI()
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
    app.include_router(ingest_router)
    app.dependency_overrides[verify_api_key] = lambda: {"company_id": "comp_001"}
    return app


@pytest.mark.integration
def test_ingest_message_creates_ticket_and_interactions(fake_db, monkeypatch):
    app = build_app()
    client = TestClient(app)

    class FakePipeline:
        async def run_pipeline(self, ticket_id: str):
            return {
                "resolution": {"decisions": {"response": "Tudo certo"}},
                "escalation": {"escalate_to_human": False, "decisions": {}},
            }

    monkeypatch.setattr("src.api.ingest_routes.AgentPipeline", lambda: FakePipeline())

    payload = {
        "channel": "telegram",
        "external_user_id": "user_123",
        "text": "Quero ajuda",
        "company_id": "comp_001",
    }

    response = client.post("/api/ingest-message", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["reply_text"] == "Tudo certo"
    assert fake_db[COLLECTION_TICKETS].inserted
    assert len(fake_db[COLLECTION_INTERACTIONS].inserted) >= 2
    assert fake_db[COLLECTION_AUDIT_LOGS].inserted
