"""
Unit tests for Context Persistence feature

Tests the KnowledgeBase customer context methods and ResolverAgent summarization.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestKnowledgeBaseContextPersistence:
    """Tests for add_ticket_summary and search_customer_context"""

    @pytest.fixture
    def mock_collection(self):
        """Create a mock ChromaDB collection"""
        collection = MagicMock()
        collection.add = MagicMock()
        collection.query = MagicMock(return_value={
            "documents": [["Summary 1", "Summary 2"]],
            "metadatas": [[{"ticket_id": "T-1"}, {"ticket_id": "T-2"}]],
            "ids": [["id1", "id2"]]
        })
        return collection

    @pytest.fixture
    def knowledge_base(self, mock_collection):
        """Create KnowledgeBase with mocked collection"""
        with patch("src.rag.knowledge_base.KnowledgeBase._initialize"):
            from src.rag.knowledge_base import KnowledgeBase
            kb = KnowledgeBase.__new__(KnowledgeBase)
            kb.get_collection = MagicMock(return_value=mock_collection)
            return kb

    @pytest.mark.asyncio
    async def test_add_ticket_summary_success(self, knowledge_base, mock_collection):
        """Test successful ticket summary indexing"""
        result = await knowledge_base.add_ticket_summary(
            summary="Customer asked about billing, resolved with refund.",
            ticket_id="T-123",
            customer_id="C-456",
            company_id="comp_001"
        )
        
        assert result is True
        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args
        assert call_args.kwargs["documents"] == ["Customer asked about billing, resolved with refund."]
        assert call_args.kwargs["metadatas"][0]["customer_id"] == "C-456"
        assert call_args.kwargs["metadatas"][0]["ticket_id"] == "T-123"

    @pytest.mark.asyncio
    async def test_add_ticket_summary_failure(self, knowledge_base, mock_collection):
        """Test ticket summary indexing failure handling"""
        mock_collection.add.side_effect = Exception("ChromaDB error")
        
        result = await knowledge_base.add_ticket_summary(
            summary="Test summary",
            ticket_id="T-123",
            customer_id="C-456",
            company_id="comp_001"
        )
        
        assert result is False

    @pytest.mark.asyncio
    async def test_search_customer_context_returns_summaries(self, knowledge_base, mock_collection):
        """Test retrieving customer context summaries"""
        results = await knowledge_base.search_customer_context(
            query="billing issue",
            customer_id="C-456",
            company_id="comp_001"
        )
        
        assert len(results) == 2
        assert "Summary 1" in results
        mock_collection.query.assert_called_once()
        
        # Verify the where clause includes customer_id filter
        call_args = mock_collection.query.call_args
        where_clause = call_args.kwargs["where"]
        assert "$and" in where_clause

    @pytest.mark.asyncio
    async def test_search_customer_context_empty_results(self, knowledge_base, mock_collection):
        """Test empty results handling"""
        mock_collection.query.return_value = {"documents": [], "metadatas": [], "ids": []}
        
        results = await knowledge_base.search_customer_context(
            query="unknown topic",
            customer_id="C-789",
            company_id="comp_001"
        )
        
        assert results == []


class TestResolverAgentSummarization:
    """Tests for conversation summarization in ResolverAgent"""

    @pytest.fixture
    def resolver_agent(self, monkeypatch):
        """Create ResolverAgent instance with mocked knowledge_base"""
        # Mock knowledge_base before importing
        from unittest.mock import MagicMock
        mock_kb = MagicMock()
        monkeypatch.setattr("src.rag.knowledge_base.knowledge_base", mock_kb)
        
        from src.agents.resolver_agent import ResolverAgent
        return ResolverAgent()

    @pytest.mark.asyncio
    async def test_generate_conversation_summary_success(self, resolver_agent, fake_openai_factory, monkeypatch):
        """Test successful conversation summary generation"""
        fake_client = fake_openai_factory(chat_result="• Customer had billing issue\n• Resolved with refund")
        monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)
        
        ticket = {"subject": "Billing Problem", "category": "billing"}
        interactions = [
            {"type": "customer_message", "content": "I was charged twice"},
            {"type": "agent_response", "content": "I'll check that for you"},
            {"type": "customer_message", "content": "Please fix it"}
        ]
        
        summary = await resolver_agent._generate_conversation_summary(
            ticket=ticket,
            interactions=interactions,
            resolution_response="I've processed your refund."
        )
        
        assert summary is not None
        assert "billing" in summary.lower() or "refund" in summary.lower()

    @pytest.mark.asyncio
    async def test_generate_conversation_summary_failure(self, resolver_agent, fake_openai_factory, monkeypatch):
        """Test summarization failure handling"""
        fake_client = fake_openai_factory(raise_on="chat")
        monkeypatch.setattr("src.utils.openai_client.get_openai_client", lambda: fake_client)
        
        ticket = {"subject": "Test", "category": "general"}
        
        summary = await resolver_agent._generate_conversation_summary(
            ticket=ticket,
            interactions=[],
            resolution_response="Response"
        )
        
        assert summary is None

    @pytest.mark.asyncio
    async def test_index_ticket_summary_calls_knowledge_base(self, resolver_agent, monkeypatch):
        """Test that indexing calls knowledge_base correctly"""
        mock_add = AsyncMock(return_value=True)
        monkeypatch.setattr("src.agents.resolver_agent.knowledge_base.add_ticket_summary", mock_add)
        
        result = await resolver_agent._index_ticket_summary(
            ticket_id="T-123",
            customer_id="C-456",
            company_id="comp_001",
            summary="Test summary"
        )
        
        assert result is True
        mock_add.assert_called_once_with(
            summary="Test summary",
            ticket_id="T-123",
            customer_id="C-456",
            company_id="comp_001"
        )
