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
        self.find_one_results = []
        self.find_results = []
        self.last_update_data = None  # Store last update data for assertions

    async def insert_one(self, document: Dict[str, Any], *args, **kwargs):
        class _InsertResult:
            def __init__(self, inserted_id):
                self.inserted_id = inserted_id

        self.inserted.append({"document": document, "args": args, "kwargs": kwargs})
        inserted_id = document.get("_id", "fake_id")
        return _InsertResult(inserted_id)

    async def update_one(self, filter_dict, update_dict, *args, **kwargs):
        self.updated.append({"filter": filter_dict, "update": update_dict, "args": args, "kwargs": kwargs})
        self.last_update_data = update_dict  # Store for test assertions
        return {"matched_count": 1, "modified_count": 1}

    async def find_one(self, *args, **kwargs):
        if self.find_one_results:
            return self.find_one_results.pop(0)
        return self.find_one_result

    def find(self, *args, **kwargs):
        return FakeCursor(list(self.find_results))


class FakeCursor:
    def __init__(self, items):
        self.items = list(items)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, limit_count: int):
        self.items = self.items[:limit_count]
        return self

    def __aiter__(self):
        self._iter = iter(self.items)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


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
    COLLECTION_API_KEYS,
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
        COLLECTION_API_KEYS: FakeCollection(),
    }

    def _get_collection(name: str) -> FakeCollection:
        return collections[name]

    monkeypatch.setattr("src.database.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.triage_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.router_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.resolver_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.agents.escalator_agent.get_collection", _get_collection)
    monkeypatch.setattr("src.api.routes.get_collection", _get_collection)
    monkeypatch.setattr("src.api.ingest_routes.get_collection", _get_collection)
    monkeypatch.setattr("src.database.ticket_operations.get_collection", _get_collection)

    return collections


@pytest.fixture
def fake_openai_factory():
    def _factory(json_result=None, chat_result=None, raise_on=None):
        return FakeOpenAIClient(json_result=json_result, chat_result=chat_result, raise_on=raise_on)

    return _factory
