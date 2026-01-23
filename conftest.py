import os
from typing import Any, Dict

# Ensure required env vars exist before importing app modules.
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("OPENAI_API_KEY", "test-key")


class FakeCollection:
    def __init__(self) -> None:
        self.inserted = []
        self.updated = []
        self.find_one_result = None

    async def insert_one(self, document: Dict[str, Any], *args, **kwargs):
        self.inserted.append({"document": document, "args": args, "kwargs": kwargs})
        return {"inserted_id": document.get("_id")}

    async def update_one(self, *args, **kwargs):
        self.updated.append({"args": args, "kwargs": kwargs})
        return {"matched_count": 1, "modified_count": 1}

    async def find_one(self, *args, **kwargs):
        return self.find_one_result


class FakeOpenAIClient:
    def __init__(self, json_result=None, chat_result=None, raise_on=None) -> None:
        self.json_result = json_result or {}
        self.chat_result = chat_result or ""
        self.raise_on = raise_on

    async def json_completion(self, *args, **kwargs):
        if self.raise_on == "json":
            raise RuntimeError("json_completion failed")
        return self.json_result

    async def chat_completion(self, *args, **kwargs):
        if self.raise_on == "chat":
            raise RuntimeError("chat_completion failed")
        return self.chat_result


import pytest
from src.database import (
    COLLECTION_TICKETS,
    COLLECTION_AGENT_STATES,
    COLLECTION_INTERACTIONS,
    COLLECTION_ROUTING_DECISIONS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_COMPANY_CONFIGS,
)


@pytest.fixture
def fake_db(monkeypatch):
    collections = {
        COLLECTION_TICKETS: FakeCollection(),
        COLLECTION_AGENT_STATES: FakeCollection(),
        COLLECTION_INTERACTIONS: FakeCollection(),
        COLLECTION_ROUTING_DECISIONS: FakeCollection(),
        COLLECTION_AUDIT_LOGS: FakeCollection(),
        COLLECTION_COMPANY_CONFIGS: FakeCollection(),
    }

    def _get_collection(name: str) -> FakeCollection:
        return collections[name]

    monkeypatch.setattr("src.database.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.triage_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.router_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.resolver_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.escalator_agent.get_collection", _get_collection)

    return collections


@pytest.fixture
def fake_openai_factory():
    def _factory(json_result=None, chat_result=None, raise_on=None):
        return FakeOpenAIClient(json_result=json_result, chat_result=chat_result, raise_on=raise_on)

    return _factory
