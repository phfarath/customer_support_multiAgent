"""
Unit tests for automated ticket tagging feature
"""
import pytest
from src.agents.triage_agent import TriageAgent
from src.database import COLLECTION_TICKETS, COLLECTION_INTERACTIONS, COLLECTION_AUDIT_LOGS


class TestTagValidation:
    """Tests for tag validation in TriageAgent"""

    def test_validate_tags_with_valid_list(self):
        """Test that valid tags are accepted"""
        agent = TriageAgent()
        tags = ["refund", "billing_issue", "urgent"]
        result = agent._validate_tags(tags)
        assert result == ["refund", "billing_issue", "urgent"]

    def test_validate_tags_sanitizes_input(self):
        """Test that tags are sanitized (lowercase, alphanumeric only)"""
        agent = TriageAgent()
        tags = ["REFUND", "Billing Issue", "test@123", "valid_tag"]
        result = agent._validate_tags(tags)
        assert "refund" in result
        assert "billing_issue" in result
        assert "test123" in result
        assert "valid_tag" in result

    def test_validate_tags_limits_to_five(self):
        """Test that only max 5 tags are returned"""
        agent = TriageAgent()
        tags = ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7"]
        result = agent._validate_tags(tags)
        assert len(result) == 5

    def test_validate_tags_with_empty_list(self):
        """Test that empty list returns empty list"""
        agent = TriageAgent()
        result = agent._validate_tags([])
        assert result == []

    def test_validate_tags_with_non_list(self):
        """Test that non-list input returns empty list"""
        agent = TriageAgent()
        assert agent._validate_tags(None) == []
        assert agent._validate_tags("string") == []
        assert agent._validate_tags(123) == []

    def test_validate_tags_removes_empty_strings(self):
        """Test that empty strings are removed"""
        agent = TriageAgent()
        tags = ["valid", "", "  ", "another"]
        result = agent._validate_tags(tags)
        assert "" not in result
        assert len(result) == 2


class TestTagGeneration:
    """Tests for rule-based tag generation"""

    def test_generate_tags_billing_keywords(self):
        """Test that billing keywords generate correct tags"""
        agent = TriageAgent()
        text = "preciso de reembolso da minha fatura duplicada"
        tags = agent._generate_tags(text, "billing")
        assert "refund" in tags
        assert "invoice" in tags
        assert "duplicate_charge" in tags

    def test_generate_tags_tech_keywords(self):
        """Test that tech keywords generate correct tags"""
        agent = TriageAgent()
        text = "app crashed with error message when trying to login"
        tags = agent._generate_tags(text, "tech")
        assert "app_crash" in tags or "mobile_app" in tags
        assert "error_message" in tags
        assert "login_issue" in tags

    def test_generate_tags_general_keywords(self):
        """Test that general keywords generate correct tags"""
        agent = TriageAgent()
        text = "como faço para configurar minha conta com uma sugestão de feature"
        tags = agent._generate_tags(text, "general")
        assert "how_to" in tags
        assert "account_issue" in tags
        assert "feature_request" in tags

    def test_generate_tags_fallback_to_category(self):
        """Test that category is used as fallback when no keywords match"""
        agent = TriageAgent()
        text = "xyz abc 123"  # No matching keywords
        tags = agent._generate_tags(text, "general")
        assert "general_general" in tags

    def test_generate_tags_max_five(self):
        """Test that max 5 tags are generated"""
        agent = TriageAgent()
        # Text with many keywords
        text = "refund payment invoice error login crash app slow"
        tags = agent._generate_tags(text, "billing")
        assert len(tags) <= 5


class TestTriageWithTags:
    """Integration tests for triage with tag generation"""

    @pytest.mark.asyncio
    async def test_triage_fallback_generates_tags(self, fake_db, fake_openai_factory, monkeypatch):
        """Test that fallback triage generates tags and saves to ticket"""
        fake_client = fake_openai_factory(raise_on="json")
        monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

        agent = TriageAgent()
        ticket = {
            "ticket_id": "T-TAG-1",
            "subject": "Quero reembolso",
            "description": "Preciso cancelar e receber reembolso da cobrança duplicada",
            "channel": "telegram",
        }
        context = {"ticket": ticket, "interactions": []}

        result = await agent.execute("T-TAG-1", context)

        assert result.success is True
        assert "tags" in result.decisions
        assert len(result.decisions["tags"]) > 0
        assert "refund" in result.decisions["tags"]
        assert result.decisions["category"] == "billing"

    @pytest.mark.asyncio
    async def test_triage_ai_generates_tags(self, fake_db, fake_openai_factory, monkeypatch):
        """Test that AI triage generates tags from OpenAI response"""
        fake_client = fake_openai_factory(json_result={
            "priority": "P2",
            "category": "billing",
            "tags": ["refund", "payment_issue"],
            "sentiment": -0.3,
            "confidence": 0.85,
            "reasoning": "Customer requesting refund"
        })
        monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

        agent = TriageAgent()
        ticket = {
            "ticket_id": "T-TAG-2",
            "subject": "Refund request",
            "description": "I need a refund",
            "channel": "email",
        }
        context = {"ticket": ticket, "interactions": []}

        result = await agent.execute("T-TAG-2", context)

        assert result.success is True
        assert "tags" in result.decisions
        assert "refund" in result.decisions["tags"]
        assert "payment_issue" in result.decisions["tags"]

    @pytest.mark.asyncio
    async def test_triage_saves_tags_to_ticket(self, fake_db, fake_openai_factory, monkeypatch):
        """Test that tags are saved to the ticket in database"""
        fake_client = fake_openai_factory(raise_on="json")
        monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)

        agent = TriageAgent()
        ticket = {
            "ticket_id": "T-TAG-3",
            "subject": "Bug no app",
            "description": "O app está lento e travando",
            "channel": "telegram",
        }
        context = {"ticket": ticket, "interactions": []}

        await agent.execute("T-TAG-3", context)

        # Check that the update contained tags
        assert fake_db[COLLECTION_TICKETS].updated
        update_data = fake_db[COLLECTION_TICKETS].last_update_data
        assert "tags" in update_data.get("$set", {})
        assert "category" in update_data.get("$set", {})


class TestCategoryValidation:
    """Tests for category validation"""

    def test_validate_category_valid_values(self):
        """Test that valid categories are accepted"""
        agent = TriageAgent()
        assert agent._validate_category("billing") == "billing"
        assert agent._validate_category("tech") == "tech"
        assert agent._validate_category("general") == "general"

    def test_validate_category_normalizes_case(self):
        """Test that category is normalized to lowercase"""
        agent = TriageAgent()
        assert agent._validate_category("BILLING") == "billing"
        assert agent._validate_category("Tech") == "tech"
        assert agent._validate_category("GENERAL") == "general"

    def test_validate_category_fallback_to_general(self):
        """Test that invalid category falls back to general"""
        agent = TriageAgent()
        assert agent._validate_category("invalid") == "general"
        assert agent._validate_category("") == "general"
        assert agent._validate_category("sales") == "general"
