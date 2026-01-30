"""
Integration tests for tag filtering in API
"""
import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.fixture
def api_key_header():
    """Fixture for authenticated API key header"""
    return {"X-API-Key": "test_api_key"}


class TestTicketTagFiltering:
    """Integration tests for filtering tickets by tags"""

    @pytest.mark.asyncio
    async def test_list_tickets_filter_by_single_tag(self, fake_db, monkeypatch, api_key_header):
        """Test filtering tickets by a single tag"""
        from src.database import COLLECTION_TICKETS, COLLECTION_API_KEYS

        # Setup fake API key validation
        fake_db[COLLECTION_API_KEYS].find_one_result = {
            "api_key": "test_api_key",
            "company_id": "comp_001",
            "active": True,
            "permissions": ["read", "write"]
        }

        # Setup fake tickets with tags
        fake_db[COLLECTION_TICKETS].find_results = [
            {
                "_id": "1",
                "ticket_id": "T-1",
                "company_id": "comp_001",
                "subject": "Refund request",
                "tags": ["refund", "billing_issue"],
                "category": "billing"
            },
        ]

        monkeypatch.setattr("src.middleware.auth.get_collection", lambda name: fake_db[name])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/tickets",
                params={"tags": "refund"},
                headers=api_key_header
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_tickets_filter_by_multiple_tags(self, fake_db, monkeypatch, api_key_header):
        """Test filtering tickets by multiple tags (comma-separated)"""
        from src.database import COLLECTION_TICKETS, COLLECTION_API_KEYS

        # Setup fake API key validation
        fake_db[COLLECTION_API_KEYS].find_one_result = {
            "api_key": "test_api_key",
            "company_id": "comp_001",
            "active": True,
            "permissions": ["read", "write"]
        }

        fake_db[COLLECTION_TICKETS].find_results = [
            {
                "_id": "1",
                "ticket_id": "T-1",
                "company_id": "comp_001",
                "tags": ["refund"],
            },
            {
                "_id": "2",
                "ticket_id": "T-2",
                "company_id": "comp_001",
                "tags": ["login_issue"],
            },
        ]

        monkeypatch.setattr("src.middleware.auth.get_collection", lambda name: fake_db[name])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/tickets",
                params={"tags": "refund,login_issue"},
                headers=api_key_header
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_tickets_filter_by_category(self, fake_db, monkeypatch, api_key_header):
        """Test filtering tickets by category"""
        from src.database import COLLECTION_TICKETS, COLLECTION_API_KEYS

        # Setup fake API key validation
        fake_db[COLLECTION_API_KEYS].find_one_result = {
            "api_key": "test_api_key",
            "company_id": "comp_001",
            "active": True,
            "permissions": ["read", "write"]
        }

        fake_db[COLLECTION_TICKETS].find_results = [
            {
                "_id": "1",
                "ticket_id": "T-1",
                "company_id": "comp_001",
                "category": "billing",
            },
        ]

        monkeypatch.setattr("src.middleware.auth.get_collection", lambda name: fake_db[name])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/tickets",
                params={"category": "billing"},
                headers=api_key_header
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_list_tickets_combined_filters(self, fake_db, monkeypatch, api_key_header):
        """Test filtering tickets with combined category and tags"""
        from src.database import COLLECTION_TICKETS, COLLECTION_API_KEYS

        # Setup fake API key validation
        fake_db[COLLECTION_API_KEYS].find_one_result = {
            "api_key": "test_api_key",
            "company_id": "comp_001",
            "active": True,
            "permissions": ["read", "write"]
        }

        fake_db[COLLECTION_TICKETS].find_results = [
            {
                "_id": "1",
                "ticket_id": "T-1",
                "company_id": "comp_001",
                "category": "billing",
                "tags": ["refund"],
                "status": "open",
                "priority": "P2",
            },
        ]

        monkeypatch.setattr("src.middleware.auth.get_collection", lambda name: fake_db[name])

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/tickets",
                params={
                    "category": "billing",
                    "tags": "refund",
                    "status": "open",
                    "priority": "P2"
                },
                headers=api_key_header
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
