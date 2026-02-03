"""
Unit tests for AI Decision Metadata - Confidence Transparency Feature
"""
import pytest
from src.models.interaction import AIDecisionMetadata, InteractionBase, InteractionType


class TestAIDecisionMetadata:
    """Tests for AIDecisionMetadata model"""
    
    def test_ai_decision_metadata_creation(self):
        """Test creating AI decision metadata with all fields"""
        metadata = AIDecisionMetadata(
            confidence_score=0.85,
            reasoning="High priority due to cancellation threat and negative sentiment",
            decision_type="triage",
            factors=["Priority: P1", "Category: billing", "Sentiment: -0.7"]
        )
        
        assert metadata.confidence_score == 0.85
        assert "cancellation" in metadata.reasoning
        assert metadata.decision_type == "triage"
        assert len(metadata.factors) == 3
    
    def test_ai_decision_metadata_defaults(self):
        """Test AIDecisionMetadata with default values"""
        metadata = AIDecisionMetadata()
        
        assert metadata.confidence_score == 0.0
        assert metadata.reasoning is None
        assert metadata.decision_type is None
        assert metadata.factors == []
    
    def test_ai_decision_metadata_partial(self):
        """Test AIDecisionMetadata with partial values"""
        metadata = AIDecisionMetadata(
            confidence_score=0.6,
            decision_type="escalation"
        )
        
        assert metadata.confidence_score == 0.6
        assert metadata.reasoning is None
        assert metadata.decision_type == "escalation"
        assert metadata.factors == []


class TestInteractionWithAIMetadata:
    """Tests for Interaction model with AI metadata"""
    
    def test_interaction_with_ai_metadata(self):
        """Test interaction model with AI metadata attached"""
        ai_metadata = AIDecisionMetadata(
            confidence_score=0.75,
            reasoning="Routed to tech team based on technical keywords",
            decision_type="routing",
            factors=["Category: tech", "Keywords: bug, error"]
        )
        
        interaction = InteractionBase(
            ticket_id="test-ticket-123",
            type=InteractionType.AGENT_RESPONSE,
            content="Technical support response",
            ai_metadata=ai_metadata
        )
        
        assert interaction.ai_metadata is not None
        assert interaction.ai_metadata.confidence_score == 0.75
        assert interaction.ai_metadata.decision_type == "routing"
    
    def test_interaction_without_ai_metadata(self):
        """Test interaction model without AI metadata (backward compatibility)"""
        interaction = InteractionBase(
            ticket_id="test-ticket-456",
            type=InteractionType.CUSTOMER_MESSAGE,
            content="Customer question about billing"
        )
        
        assert interaction.ai_metadata is None
    
    def test_interaction_serialization_with_metadata(self):
        """Test that interaction with metadata can be serialized"""
        ai_metadata = AIDecisionMetadata(
            confidence_score=0.9,
            reasoning="Resolution successful",
            decision_type="resolution",
            factors=["Resolved within SLA", "Positive sentiment"]
        )
        
        interaction = InteractionBase(
            ticket_id="test-ticket-789",
            type=InteractionType.AGENT_RESPONSE,
            content="Issue resolved",
            ai_metadata=ai_metadata
        )
        
        # Serialize to dict
        data = interaction.model_dump()
        
        assert "ai_metadata" in data
        assert data["ai_metadata"]["confidence_score"] == 0.9
        assert data["ai_metadata"]["decision_type"] == "resolution"
        assert len(data["ai_metadata"]["factors"]) == 2


class TestDecisionTypes:
    """Tests for different decision types"""
    
    def test_triage_decision(self):
        """Test triage decision metadata"""
        metadata = AIDecisionMetadata(
            confidence_score=0.82,
            reasoning="P1 priority due to urgent keywords and cancellation mention",
            decision_type="triage",
            factors=["Priority: P1", "Category: billing", "Sentiment: -0.5"]
        )
        
        assert metadata.decision_type == "triage"
        assert "P1" in metadata.reasoning
    
    def test_routing_decision(self):
        """Test routing decision metadata"""
        metadata = AIDecisionMetadata(
            confidence_score=0.88,
            reasoning="Routed to billing team due to payment-related keywords",
            decision_type="routing",
            factors=["Category match", "Previous tickets with billing"]
        )
        
        assert metadata.decision_type == "routing"
        assert "billing" in metadata.reasoning
    
    def test_resolution_decision(self):
        """Test resolution decision metadata"""
        metadata = AIDecisionMetadata(
            confidence_score=0.72,
            reasoning="Ticket resolved within normal parameters using knowledge base",
            decision_type="resolution",
            factors=["KB article matched", "Positive customer response"]
        )
        
        assert metadata.decision_type == "resolution"
    
    def test_escalation_decision(self):
        """Test escalation decision metadata"""
        metadata = AIDecisionMetadata(
            confidence_score=0.45,
            reasoning="Escalation triggered due to: Negative sentiment (-0.8), SLA breach (25.5 hours)",
            decision_type="escalation",
            factors=["Negative sentiment: -0.80", "SLA breach: 25.5 hours"]
        )
        
        assert metadata.decision_type == "escalation"
        assert "SLA breach" in metadata.reasoning
        assert metadata.confidence_score < 0.5  # Low confidence for escalation
