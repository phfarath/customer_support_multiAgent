import pytest

from src.models import CompanyConfig
from src.agents.base_agent import AgentResult
from src.utils.pipeline import AgentPipeline


class FakeSession:
    def start_transaction(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def end_session(self):
        return None


class FakeClient:
    async def start_session(self):
        return FakeSession()


class FakeAgent:
    def __init__(self, name, decisions, needs_escalation=False):
        self.name = name
        self.decisions = decisions
        self.needs_escalation = needs_escalation
        self.calls = []

    async def execute(self, ticket_id, context, session=None):
        self.calls.append((ticket_id, context))
        return AgentResult(
            success=True,
            confidence=0.9,
            decisions=self.decisions,
            message=f"{self.name} ok",
            needs_escalation=self.needs_escalation,
            escalation_reasons=[]
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pipeline_runs_all_agents(monkeypatch):
    monkeypatch.setattr("src.database.transactions.get_client", lambda: FakeClient())

    pipeline = AgentPipeline()

    triage_agent = FakeAgent("triage", {"priority": "P2"})
    router_agent = FakeAgent("router", {"target_team": "tech"})
    resolver_agent = FakeAgent("resolver", {"response": "ok"})
    escalator_agent = FakeAgent("escalator", {"reasons": []}, needs_escalation=False)

    pipeline.triage_agent = triage_agent
    pipeline.router_agent = router_agent
    pipeline.resolver_agent = resolver_agent
    pipeline.escalator_agent = escalator_agent

    async def fake_get_ticket(ticket_id, session):
        return {"ticket_id": ticket_id, "customer_id": "cust_1", "company_id": "comp_001"}

    async def fake_get_interactions(ticket_id, session):
        return []

    async def fake_get_customer_history(customer_id, session):
        return []

    async def fake_get_company_config(company_id):
        return CompanyConfig(company_id=company_id, company_name="Acme")

    pipeline._get_ticket = fake_get_ticket
    pipeline._get_interactions = fake_get_interactions
    pipeline._get_customer_history = fake_get_customer_history
    pipeline._get_company_config = fake_get_company_config

    result = await pipeline.run_pipeline("T-1")

    assert result["ticket_id"] == "T-1"
    assert result["final_status"] == "in_progress"
    assert triage_agent.calls
    assert router_agent.calls
    assert resolver_agent.calls
    assert escalator_agent.calls


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pipeline_raises_when_ticket_missing(monkeypatch):
    monkeypatch.setattr("src.database.transactions.get_client", lambda: FakeClient())

    pipeline = AgentPipeline()

    async def fake_get_ticket(ticket_id, session):
        return None

    pipeline._get_ticket = fake_get_ticket

    with pytest.raises(RuntimeError) as exc:
        await pipeline.run_pipeline("T-missing")

    assert "Ticket T-missing not found" in str(exc.value)
