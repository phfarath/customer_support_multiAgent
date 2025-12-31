"""
Escalator Agent - Decides when to escalate tickets to human agents
"""
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClientSession
from .base_agent import BaseAgent, AgentResult
from src.models import (
    TicketPhase,
    TicketStatus,
    AuditLogCreate,
    AuditOperation,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_AUDIT_LOGS,
)
from src.config import settings
from datetime import datetime


class EscalatorAgent(BaseAgent):
    """
    Escalator Agent evaluates if a ticket needs human intervention:
    - Reviews resolver's confidence and escalation recommendations
    - Checks SLA compliance
    - Makes final escalation decision
    """
    
    def __init__(self):
        super().__init__("escalator")
    
    def get_phase_name(self) -> str:
        return TicketPhase.ESCALATION
    
    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> AgentResult:
        """
        Execute escalation evaluation for a ticket
        
        Args:
            ticket_id: ID of the ticket
            context: Contains ticket data, triage, routing, resolver results
            session: Optional MongoDB session for transactions
            
        Returns:
            AgentResult with escalation decision
        """
        ticket = context.get("ticket")
        triage_result = context.get("triage_result", {})
        routing_result = context.get("routing_result", {})
        resolver_result = context.get("resolver_result", {})
        interactions = context.get("interactions", [])
        
        if not ticket:
            return AgentResult(
                success=False,
                confidence=0.0,
                decisions={},
                message="No ticket data provided"
            )
        
        # Make escalation decision
        escalation = await self._make_escalation_decision(
            ticket,
            triage_result,
            routing_result,
            resolver_result,
            interactions
        )
        
        # Apply escalation decision
        await self._apply_escalation(
            ticket_id,
            escalation,
            session
        )
        
        # Save agent state
        await self.save_agent_state(
            ticket_id,
            escalation,
            session
        )
        
        return AgentResult(
            success=True,
            confidence=1.0,
            decisions=escalation,
            message=escalation["message"],
            needs_escalation=escalation["escalate_to_human"]
        )
    
    async def _make_escalation_decision(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        routing_result: Dict[str, Any],
        resolver_result: Dict[str, Any],
        interactions: list
    ) -> Dict[str, Any]:
        """
        Make the final escalation decision
        
        Args:
            ticket: Ticket data
            triage_result: Results from triage agent
            routing_result: Results from router agent
            resolver_result: Results from resolver agent
            interactions: List of interactions
            
        Returns:
            Dict with escalation decision and reasons
        """
        escalate_to_human = False
        reasons = []
        
        # Get resolver's recommendation
        resolver_needs_escalation = resolver_result.get("needs_escalation", False)
        resolver_escalation_reasons = resolver_result.get("escalation_reasons", [])
        resolver_confidence = resolver_result.get("confidence", 0.8)
        
        # Priority and interactions
        priority = ticket.get("priority", "P3")
        interactions_count = len(interactions)
        
        # Sentiment
        sentiment = triage_result.get("sentiment", 0.0)
        
        # SLA check
        created_at = ticket.get("created_at")
        sla_hours = 0.0
        if created_at:
            time_diff = datetime.utcnow() - created_at
            sla_hours = time_diff.total_seconds() / 3600
        
        # Escalation rules (hardcoded as specified)
        
        # Rule 1: P1 with too many interactions
        if priority == "P1" and interactions_count > settings.escalation_max_interactions:
            escalate_to_human = True
            reasons.append(f"P1 ticket with {interactions_count} interactions exceeds threshold")
        
        # Rule 2: Very negative sentiment
        if sentiment < settings.escalation_min_sentiment:
            escalate_to_human = True
            reasons.append(f"Customer sentiment {sentiment:.2f} below threshold {settings.escalation_min_sentiment}")
        
        # Rule 3: Low resolver confidence
        if resolver_confidence < settings.escalation_min_confidence:
            escalate_to_human = True
            reasons.append(f"Resolver confidence {resolver_confidence:.2f} below threshold {settings.escalation_min_confidence}")
        
        # Rule 4: SLA breach
        if sla_hours > settings.escalation_sla_hours:
            escalate_to_human = True
            reasons.append(f"SLA breach: {sla_hours:.1f} hours exceeds threshold {settings.escalation_sla_hours}h")
        
        # Add resolver's escalation reasons if any
        if resolver_needs_escalation:
            for reason in resolver_escalation_reasons:
                if reason not in reasons:
                    reasons.append(reason)
        
        # Determine message
        if escalate_to_human:
            message = f"Ticket escalated to human. Reasons: {', '.join(reasons)}"
        else:
            message = "Ticket can be resolved automatically"
        
        return {
            "escalate_to_human": escalate_to_human,
            "reasons": reasons,
            "priority": priority,
            "sentiment": sentiment,
            "resolver_confidence": resolver_confidence,
            "sla_hours": sla_hours,
            "interactions_count": interactions_count,
            "message": message
        }
    
    async def _apply_escalation(
        self,
        ticket_id: str,
        escalation: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Apply the escalation decision to the ticket
        
        Args:
            ticket_id: ID of the ticket
            escalation: Escalation decision data
            session: Optional MongoDB session
        """
        tickets_collection = await get_collection(COLLECTION_TICKETS)
        
        if escalation["escalate_to_human"]:
            # Update ticket to escalated status
            update_data = {
                "status": TicketStatus.ESCALATED,
                "current_phase": TicketPhase.ESCALATION,
                "updated_at": datetime.utcnow()
            }
        else:
            # Update ticket to in_progress (will be resolved)
            update_data = {
                "status": TicketStatus.IN_PROGRESS,
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
        
        # Create audit log
        audit_collection = await get_collection(COLLECTION_AUDIT_LOGS)
        
        audit_log = AuditLogCreate(
            ticket_id=ticket_id,
            agent_name=self.name,
            operation=AuditOperation.ESCALATE,
            before={},
            after={
                "escalate_to_human": escalation["escalate_to_human"],
                "reasons": escalation["reasons"]
            }
        )
        
        audit_data = audit_log.model_dump()
        audit_data["timestamp"] = datetime.utcnow()
        
        if session:
            await audit_collection.insert_one(audit_data, session=session)
        else:
            await audit_collection.insert_one(audit_data)
