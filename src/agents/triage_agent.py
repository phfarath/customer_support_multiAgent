"""
Triage Agent - Analyzes tickets and determines priority, category, and sentiment
"""
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClientSession
from .base_agent import BaseAgent, AgentResult
from src.models import (
    TicketPriority,
    TicketPhase,
    InteractionCreate,
    InteractionType,
    AuditLogCreate,
    AuditOperation,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_AUDIT_LOGS,
)
from src.config import settings
from datetime import datetime


class TriageAgent(BaseAgent):
    """
    Triage Agent analyzes ticket content and determines:
    - Priority level (P1, P2, P3)
    - Initial category
    - Sentiment score
    """
    
    def __init__(self):
        super().__init__("triage")
    
    def get_phase_name(self) -> str:
        return TicketPhase.TRIAGE
    
    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> AgentResult:
        """
        Execute triage analysis on a ticket
        
        Args:
            ticket_id: ID of the ticket
            context: Contains ticket data and interactions
            session: Optional MongoDB session for transactions
            
        Returns:
            AgentResult with priority, category, and sentiment
        """
        ticket = context.get("ticket")
        interactions = context.get("interactions", [])
        
        if not ticket:
            return AgentResult(
                success=False,
                confidence=0.0,
                decisions={},
                message="No ticket data provided"
            )
        
        # Analyze the ticket
        analysis = await self._analyze_ticket(ticket, interactions)
        
        # Save results to database
        await self._save_triage_results(
            ticket_id,
            analysis,
            session
        )
        
        # Save agent state
        await self.save_agent_state(
            ticket_id,
            analysis,
            session
        )
        
        return AgentResult(
            success=True,
            confidence=analysis.get("confidence", 0.85),
            decisions=analysis,
            message=f"Triage complete: Priority {analysis['priority']}, Category {analysis['category']}"
        )
    
    async def _analyze_ticket(
        self,
        ticket: Dict[str, Any],
        interactions: list
    ) -> Dict[str, Any]:
        """
        Analyze ticket to determine priority, category, and sentiment using OpenAI
        
        Args:
            ticket: Ticket data
            interactions: List of previous interactions
            
        Returns:
            Dict with priority, category, sentiment, and confidence
        """
        from src.utils.openai_client import get_openai_client
        
        description = ticket.get("description", "")
        subject = ticket.get("subject", "")
        channel = ticket.get("channel", "")
        
        # Build interaction context
        interaction_context = ""
        if interactions:
            interaction_context = "\nPrevious interactions:\n" + "\n".join([
                f"- {i.get('content', '')[:100]}" for i in interactions[-3:]
            ])
        
        # System prompt for triage analysis
        system_prompt = """You are a customer support triage specialist. Analyze the ticket and determine:
1. Priority (P1, P2, or P3):
   - P1: Urgent/critical issues (system down, security breach, immediate financial impact, cancellation threats)
   - P2: Important but not urgent (billing issues, bugs, functional problems)
   - P3: General inquiries, how-to questions, low urgency

2. Category (billing, tech, or general):
   - billing: Payment, refund, invoice, pricing issues
   - tech: Technical problems, bugs, app/website issues, login problems
   - general: General inquiries, account questions, how-to

3. Sentiment (-1.0 to 1.0):
   - -1.0 to -0.3: Very negative to negative
   - -0.3 to 0.3: Neutral
   - 0.3 to 1.0: Positive to very positive

4. Confidence (0.0 to 1.0): How confident are you in this analysis?

Return your response as a JSON object with these fields: priority, category, sentiment, confidence"""

        user_message = f"""Ticket Information:
Subject: {subject}
Description: {description}
Channel: {channel}
{interaction_context}

Analyze this ticket and provide the triage assessment."""

        try:
            client = get_openai_client()
            result = await client.json_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=300
            )
            
            # Validate and normalize the results
            priority = self._validate_priority(result.get("priority", "P3"))
            category = self._validate_category(result.get("category", "general"))
            sentiment = self._validate_sentiment(result.get("sentiment", 0.0))
            confidence = self._validate_confidence(result.get("confidence", 0.7))
            
            return {
                "priority": priority,
                "category": category,
                "sentiment": sentiment,
                "confidence": confidence,
                "decisions": [
                    f"Priority set to {priority}",
                    f"Category: {category}",
                    f"Sentiment: {sentiment:.2f}"
                ]
            }
        except Exception as e:
            # Fallback to rule-based analysis if OpenAI fails
            print(f"OpenAI analysis failed, falling back to rule-based: {str(e)}")
            return self._analyze_ticket_fallback(ticket, interactions)
    
    def _validate_priority(self, priority: str) -> str:
        """Validate and normalize priority value"""
        priority = str(priority).upper().strip()
        if priority in ["P1", "P2", "P3"]:
            return priority
        return "P3"
    
    def _validate_category(self, category: str) -> str:
        """Validate and normalize category value"""
        category = str(category).lower().strip()
        if category in ["billing", "tech", "general"]:
            return category
        return "general"
    
    def _validate_sentiment(self, sentiment: Any) -> float:
        """Validate and normalize sentiment value"""
        try:
            sentiment = float(sentiment)
            return max(-1.0, min(1.0, sentiment))
        except (ValueError, TypeError):
            return 0.0
    
    def _validate_confidence(self, confidence: Any) -> float:
        """Validate and normalize confidence value"""
        try:
            confidence = float(confidence)
            return max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            return 0.7
    
    def _analyze_ticket_fallback(
        self,
        ticket: Dict[str, Any],
        interactions: list
    ) -> Dict[str, Any]:
        """
        Fallback rule-based analysis when OpenAI is unavailable
        
        Args:
            ticket: Ticket data
            interactions: List of previous interactions
            
        Returns:
            Dict with priority, category, sentiment, and confidence
        """
        description = ticket.get("description", "").lower()
        subject = ticket.get("subject", "").lower()
        text = f"{subject} {description}"
        
        # Priority analysis (keyword-based)
        priority = self._determine_priority(text)
        
        # Category analysis
        category = self._determine_category(text)
        
        # Sentiment analysis (simple keyword-based)
        sentiment = self._analyze_sentiment(text)
        
        # Confidence based on clarity of the issue
        confidence = self._calculate_confidence(text, priority, sentiment)
        
        return {
            "priority": priority,
            "category": category,
            "sentiment": sentiment,
            "confidence": confidence,
            "decisions": [
                f"Priority set to {priority} (fallback)",
                f"Category: {category} (fallback)",
                f"Sentiment: {sentiment:.2f} (fallback)"
            ]
        }
    
    def _determine_priority(self, text: str) -> str:
        """
        Determine ticket priority based on keywords
        
        Args:
            text: Ticket text to analyze
            
        Returns:
            Priority level (P1, P2, P3)
        """
        p1_keywords = [
            "urgente", "emergency", "critical", "crash", "down", "perdi",
            "cancelar", "cancellation", "refund", "reembolso", "perdido",
            "hack", "security", "breach", "bloqueado", "blocked"
        ]
        
        p2_keywords = [
            "bug", "erro", "error", "problem", "issue", "não funciona",
            "not working", "lento", "slow", "cobrança", "charge",
            "duplicate", "duplicado", "fatura", "invoice"
        ]
        
        for keyword in p1_keywords:
            if keyword in text:
                return TicketPriority.P1
        
        for keyword in p2_keywords:
            if keyword in text:
                return TicketPriority.P2
        
        return TicketPriority.P3
    
    def _determine_category(self, text: str) -> str:
        """
        Determine ticket category based on keywords
        
        Args:
            text: Ticket text to analyze
            
        Returns:
            Category string
        """
        billing_keywords = [
            "cobrança", "charge", "payment", "pagamento", "fatura",
            "invoice", "refund", "reembolso", "price", "preço",
            "duplicate", "duplicado", "cartão", "card"
        ]
        
        tech_keywords = [
            "crash", "erro", "error", "bug", "app", "website",
            "login", "senha", "password", "não funciona", "not working",
            "lento", "slow", "instalação", "install"
        ]
        
        for keyword in billing_keywords:
            if keyword in text:
                return "billing"
        
        for keyword in tech_keywords:
            if keyword in text:
                return "tech"
        
        return "general"
    
    def _analyze_sentiment(self, text: str) -> float:
        """
        Analyze sentiment of the ticket text
        
        Args:
            text: Ticket text to analyze
            
        Returns:
            Sentiment score between -1.0 (negative) and 1.0 (positive)
        """
        negative_words = [
            "bravo", "angry", "frustrado", "frustrated", "insatisfeito",
            "dissatisfied", "péssimo", "terrible", "horrível", "horrible",
            "ruim", "bad", "odiei", "hated", "nunca mais", "never again",
            "cancelar", "cancel", "vou processar", "sue", "escândalo",
            "scandal", "inaceitável", "unacceptable", "irresponsável",
            "irresponsible", "roubo", "steal", "golpe", "scam"
        ]
        
        positive_words = [
            "obrigado", "thanks", "excelente", "excellent", "ótimo",
            "great", "bom", "good", "ajudou", "helped", "rápido",
            "fast", "resolvido", "solved", "feliz", "happy", "satisfeito",
            "satisfied", "recomendo", "recommend"
        ]
        
        negative_count = sum(1 for word in negative_words if word in text)
        positive_count = sum(1 for word in positive_words if word in text)
        
        if negative_count == 0 and positive_count == 0:
            return 0.0
        
        total = negative_count + positive_count
        return (positive_count - negative_count) / total
    
    def _calculate_confidence(
        self,
        text: str,
        priority: str,
        sentiment: float
    ) -> float:
        """
        Calculate confidence score for the triage decision
        
        Args:
            text: Ticket text
            priority: Determined priority
            sentiment: Determined sentiment
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        base_confidence = 0.75
        
        # Higher confidence for clear issues (longer, more detailed)
        if len(text) > 100:
            base_confidence += 0.1
        
        # Higher confidence for extreme priorities
        if priority == TicketPriority.P1:
            base_confidence += 0.1
        
        # Higher confidence for strong sentiment (positive or negative)
        if abs(sentiment) > 0.5:
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)
    
    async def _save_triage_results(
        self,
        ticket_id: str,
        analysis: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Save triage results to database
        
        Args:
            ticket_id: ID of the ticket
            analysis: Analysis results
            session: Optional MongoDB session
        """
        # Update ticket with priority
        tickets_collection = get_collection(COLLECTION_TICKETS)
        
        update_data = {
            "priority": analysis["priority"],
            "current_phase": TicketPhase.ROUTING,
            "updated_at": datetime.utcnow()
        }
        
        if session:
            await tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data},
                session=session
            )
        else:
            await tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": update_data}
            )
        
        # Create interaction record
        interactions_collection = get_collection(COLLECTION_INTERACTIONS)
        
        interaction = InteractionCreate(
            ticket_id=ticket_id,
            type=InteractionType.AGENT_RESPONSE,
            content=f"Ticket triaged as {analysis['priority']} priority, category: {analysis['category']}",
            sentiment_score=analysis["sentiment"]
        )
        
        interaction_data = interaction.model_dump()
        interaction_data["created_at"] = datetime.utcnow()
        
        if session:
            await interactions_collection.insert_one(interaction_data, session=session)
        else:
            await interactions_collection.insert_one(interaction_data)
        
        # Create audit log
        audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
        
        audit_log = AuditLogCreate(
            ticket_id=ticket_id,
            agent_name=self.name,
            operation=AuditOperation.UPDATE_PRIORITY,
            before={"priority": "P3"},
            after={"priority": analysis["priority"]}
        )
        
        audit_data = audit_log.model_dump()
        audit_data["timestamp"] = datetime.utcnow()
        
        if session:
            await audit_collection.insert_one(audit_data, session=session)
        else:
            await audit_collection.insert_one(audit_data)
