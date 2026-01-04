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
        Make final escalation decision using OpenAI
        
        Args:
            ticket: Ticket data
            triage_result: Results from triage agent
            routing_result: Results from router agent
            resolver_result: Results from resolver agent
            interactions: List of interactions
            
        Returns:
            Dict with escalation decision and reasons
        """
        from src.utils.openai_client import get_openai_client
        
        subject = ticket.get("subject", "")
        description = ticket.get("description", "")
        priority = ticket.get("priority", "P3")
        interactions_count = len(interactions)
        sentiment = triage_result.get("sentiment", 0.0)
        resolver_confidence = resolver_result.get("confidence", 0.8)
        resolver_needs_escalation = resolver_result.get("needs_escalation", False)
        resolver_escalation_reasons = resolver_result.get("escalation_reasons", [])
        target_team = routing_result.get("target_team", "general")
        
        # SLA check
        created_at = ticket.get("created_at")
        sla_hours = 0.0
        if created_at:
            time_diff = datetime.utcnow() - created_at
            sla_hours = time_diff.total_seconds() / 3600
        
        # Build interaction context
        interaction_context = ""
        if interactions:
            interaction_context = "\nRecent interactions:\n" + "\n".join([
                f"- {i.get('content', '')[:100]}" for i in interactions[-3:]
            ])
        
        # Get resolver's generated response (if available)
        resolver_response = resolver_result.get("response", "N/A")
        
        # System prompt for escalation decision
        system_prompt = f"""You are a customer support escalation specialist. Decide whether this ticket should be escalated to a human agent or can be resolved automatically.

Escalation Thresholds (MUST respect these):
- Max interactions before escalation: {settings.escalation_max_interactions}
- Minimum sentiment threshold: {settings.escalation_min_sentiment}
- Minimum resolver confidence: {settings.escalation_min_confidence}
- SLA breach threshold: {settings.escalation_sla_hours} hours

Consider these factors:
1. Ticket priority (P1 = critical, P2 = important, P3 = normal)
2. Number of interactions (too many back-and-forth = escalate)
3. Customer sentiment (very negative = escalate)
4. Resolver's confidence (low confidence = escalate)
5. SLA compliance (breach = escalate)
6. The resolver's generated response quality
7. Overall complexity of issue

Return your response as a JSON object with these fields:
- escalate_to_human: true or false
- reasons: array of strings explaining your decision
- confidence: number between 0.0 and 1.0"""

        user_message = f"""Ticket Information:
Subject: {subject}
Description: {description}
Priority: {priority}
Target Team: {target_team}
Sentiment: {sentiment:.2f}
Interactions Count: {interactions_count}
SLA Hours: {sla_hours:.2f}h
Resolver Confidence: {resolver_confidence:.2f}
Resolver Recommended Escalation: {resolver_needs_escalation}
Resolver Escalation Reasons: {resolver_escalation_reasons}
{interaction_context}

Resolver's Generated Response:
{resolver_response[:500]}

Should this ticket be escalated to a human agent?"""

        try:
            client = get_openai_client()
            result = await client.json_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.2,
                max_tokens=400
            )
            
            # Validate and normalize results
            escalate_to_human = self._validate_escalation(result.get("escalate_to_human", False))
            reasons = self._validate_reasons(result.get("reasons", []))
            confidence = self._validate_confidence(result.get("confidence", 0.9))
            
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
        except Exception as e:
            # Fallback to rule-based escalation if OpenAI fails
            print(f"OpenAI escalation decision failed, falling back to rule-based: {str(e)}")
            return self._make_escalation_decision_fallback(
                ticket, triage_result, routing_result, resolver_result, interactions
            )
    
    def _validate_escalation(self, escalate: Any) -> bool:
        """Validate and normalize escalation value"""
        if isinstance(escalate, bool):
            return escalate
        return str(escalate).lower() in ["true", "1", "yes"]
    
    def _validate_reasons(self, reasons: Any) -> list:
        """Validate and normalize reasons value"""
        if isinstance(reasons, list):
            return [str(r) for r in reasons if r]
        return [str(reasons)] if reasons else []
    
    def _validate_confidence(self, confidence: Any) -> float:
        """Validate and normalize confidence value"""
        try:
            confidence = float(confidence)
            return max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            return 0.9
    
    def _make_escalation_decision_fallback(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        routing_result: Dict[str, Any],
        resolver_result: Dict[str, Any],
        interactions: list
    ) -> Dict[str, Any]:
        """
        Fallback rule-based escalation when OpenAI is unavailable
        
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
            reasons.append(f"P1 ticket with {interactions_count} interactions exceeds threshold (fallback)")
        
        # Rule 2: Very negative sentiment
        if sentiment < settings.escalation_min_sentiment:
            escalate_to_human = True
            reasons.append(f"Customer sentiment {sentiment:.2f} below threshold {settings.escalation_min_sentiment} (fallback)")
        
        # Rule 3: Low resolver confidence
        if resolver_confidence < settings.escalation_min_confidence:
            escalate_to_human = True
            reasons.append(f"Resolver confidence {resolver_confidence:.2f} below threshold {settings.escalation_min_confidence} (fallback)")
        
        # Rule 4: SLA breach
        if sla_hours > settings.escalation_sla_hours:
            escalate_to_human = True
            reasons.append(f"SLA breach: {sla_hours:.1f} hours exceeds threshold {settings.escalation_sla_hours}h (fallback)")
        
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
        Apply escalation decision to ticket
        
        Args:
            ticket_id: ID of ticket
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
