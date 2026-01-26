from datetime import datetime, timedelta

import pytest

from src.agents.triage_agent import TriageAgent
from src.agents.router_agent import RouterAgent
from src.agents.resolver_agent import ResolverAgent
from src.agents.escalator_agent import EscalatorAgent
from src.database import (
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_ROUTING_DECISIONS,
    COLLECTION_COMPANY_CONFIGS,
)
from src.config import settings


@pytest.mark.asyncio
async def test_triage_agent_fallback_saves_results(fake_db, fake_openai_factory, monkeypatch):
    fake_client = fake_openai_factory(raise_on="json")
    monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

    agent = TriageAgent()
    ticket = {
        "ticket_id": "T-1",
        "subject": "Quero cancelar agora",
        "description": "Preciso cancelar urgente e pedir reembolso",
        "channel": "telegram",
    }
    context = {"ticket": ticket, "interactions": []}

    result = await agent.execute("T-1", context)

    assert result.success is True
    assert result.decisions["priority"] == "P1"
    assert fake_db[COLLECTION_TICKETS].updated
    assert fake_db[COLLECTION_INTERACTIONS].inserted
    assert fake_db[COLLECTION_AUDIT_LOGS].inserted


@pytest.mark.asyncio
async def test_router_agent_fallback_routes_by_category(fake_db, fake_openai_factory, monkeypatch):
    fake_client = fake_openai_factory(raise_on="json")
    monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

    fake_db[COLLECTION_COMPANY_CONFIGS].find_one_result = {
        "company_id": "comp_001",
        "company_name": "Acme",
        "teams": [
            {"team_id": "billing", "name": "Billing", "description": "Billing help"},
            {"team_id": "tech", "name": "Tech", "description": "Tech help"},
            {"team_id": "general", "name": "General", "description": "General help"},
        ],
    }

    agent = RouterAgent()
    context = {
        "ticket": {"ticket_id": "T-2", "subject": "App", "description": "Erro", "company_id": "comp_001"},
        "triage_result": {"category": "tech"},
        "customer_history": [],
    }

    result = await agent.execute("T-2", context)

    assert result.success is True
    assert result.decisions["target_team"] == "tech"
    assert fake_db[COLLECTION_ROUTING_DECISIONS].inserted
    assert fake_db[COLLECTION_TICKETS].updated


@pytest.mark.asyncio
async def test_resolver_agent_escalation_and_response_fallback(fake_db, fake_openai_factory, monkeypatch):
    fake_client = fake_openai_factory(chat_result="", raise_on="chat")
    monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

    async def fake_search(*args, **kwargs):
        return ["KB entry 1", "KB entry 2"]

    monkeypatch.setattr("src.agents.resolver_agent.knowledge_base.search", fake_search)

    agent = ResolverAgent()
    ticket = {
        "ticket_id": "T-3",
        "subject": "Falha crítica",
        "description": "Sistema caiu",
        "priority": "P1",
        "created_at": datetime.utcnow().isoformat(),
    }
    interactions = [
        {"type": "customer_message", "content": "Mensagem 1"},
        {"type": "customer_message", "content": "Mensagem 2"},
        {"type": "customer_message", "content": "Mensagem 3"},
    ]
    context = {
        "ticket": ticket,
        "triage_result": {"sentiment": -0.8, "confidence": 0.4},
        "routing_result": {"target_team": "tech"},
        "interactions": interactions,
        "company_config": {
            "company_id": "comp_001",
            "company_name": "Acme",
            "knowledge_base": {"enabled": True, "vector_db_collection": "company_knowledge"},
            "teams": [{"team_id": "tech", "name": "Tech", "description": "Tech help"}],
        },
    }

    result = await agent.execute("T-3", context)

    assert result.success is True
    assert result.needs_escalation is True
    assert result.escalation_reasons
    assert fake_db[COLLECTION_INTERACTIONS].inserted
    assert fake_db[COLLECTION_AUDIT_LOGS].inserted


@pytest.mark.asyncio
async def test_escalator_agent_fallback_escalates_and_updates_ticket(fake_db, fake_openai_factory, monkeypatch):
    fake_client = fake_openai_factory(raise_on="json")
    monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

    agent = EscalatorAgent()
    ticket = {
        "ticket_id": "T-4",
        "subject": "Falha",
        "description": "Erro",
        "priority": "P1",
        "created_at": datetime.utcnow() - timedelta(hours=settings.escalation_sla_hours + 1),
    }
    context = {
        "ticket": ticket,
        "triage_result": {"sentiment": -0.9},
        "routing_result": {"target_team": "tech"},
        "resolver_result": {"needs_escalation": True, "confidence": 0.3, "escalation_reasons": ["Low confidence"]},
        "interactions": [
            {"type": "customer_message", "content": "Mensagem 1"},
            {"type": "customer_message", "content": "Mensagem 2"},
            {"type": "customer_message", "content": "Mensagem 3"},
        ],
    }

    result = await agent.execute("T-4", context)

    assert result.success is True
    assert result.needs_escalation is True
    assert fake_db[COLLECTION_TICKETS].updated
    assert fake_db[COLLECTION_AUDIT_LOGS].inserted
