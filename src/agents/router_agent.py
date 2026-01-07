"""
Router Agent - Routes tickets to appropriate teams based on triage analysis
"""
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClientSession
from .base_agent import BaseAgent, AgentResult
from src.models import (
    TicketPhase,
    RoutingDecisionCreate,
    AuditLogCreate,
    AuditOperation,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_ROUTING_DECISIONS,
    COLLECTION_AUDIT_LOGS,
)
from datetime import datetime


class RouterAgent(BaseAgent):
    """
    Router Agent determines which team should handle a ticket:
    - billing: Payment, refund, invoice issues
    - tech: Technical problems, bugs, app issues
    - general: General inquiries, how-to questions
    """
    
    def __init__(self):
        super().__init__("router")
    
    def get_phase_name(self) -> str:
        return TicketPhase.ROUTING
    
    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> AgentResult:
        """
        Execute routing decision for a ticket
        
        Args:
            ticket_id: ID of the ticket
            context: Contains ticket data, triage results, and customer history
            session: Optional MongoDB session for transactions
            
        Returns:
            AgentResult with target team and confidence
        """
        ticket = context.get("ticket")
        triage_result = context.get("triage_result", {})
        customer_history = context.get("customer_history", [])
        
        if not ticket:
            return AgentResult(
                success=False,
                confidence=0.0,
                decisions={},
                message="No ticket data provided"
            )
        
        # Make routing decision
        routing = await self._make_routing_decision(
            ticket,
            triage_result,
            customer_history
        )
        
        # Save routing decision
        await self._save_routing_decision(
            ticket_id,
            routing,
            session
        )
        
        # Update ticket phase
        await self._update_ticket_phase(
            ticket_id,
            session
        )
        
        # Save agent state
        await self.save_agent_state(
            ticket_id,
            routing,
            session
        )
        
        return AgentResult(
            success=True,
            confidence=routing.get("confidence", 0.85),
            decisions=routing,
            message=f"Ticket routed to {routing['target_team']} team"
        )
    
    async def _make_routing_decision(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        customer_history: list
    ) -> Dict[str, Any]:
        """
        Determine which team should handle the ticket using OpenAI
        
        Args:
            ticket: Ticket data
            triage_result: Results from triage agent
            customer_history: Customer's previous tickets
            
        Returns:
            Dict with target_team, confidence, and reasons
        """
        from src.utils.openai_client import get_openai_client
        
        subject = ticket.get("subject", "")
        description = ticket.get("description", "")
        priority = triage_result.get("priority", "P3")
        category = triage_result.get("category", "general")
        sentiment = triage_result.get("sentiment", 0.0)
        
        # Build customer history context
        history_context = ""
        if customer_history:
            history_context = "\nCustomer History (recent tickets):\n" + "\n".join([
                f"- {t.get('ticket_id', 'N/A')}: {t.get('priority', 'N/A')} -> {t.get('target_team', 'N/A')}"
                for t in customer_history[-5:]
            ])
        
        # System prompt for routing decision
        system_prompt = """You are a customer support routing specialist. Determine which team should handle this ticket.

Available teams:
1. billing: Payment, refund, invoice, pricing, subscription issues
2. tech: Technical problems, bugs, app/website issues, login problems, installation
3. general: General inquiries, account questions, how-to, feature requests

Consider:
- The ticket category from triage
- The priority level
- Customer sentiment
- Customer's previous ticket patterns (if they have repeated issues with a specific team)

Return your response as a JSON object with these fields:
- target_team: One of "billing", "tech", or "general"
- confidence: A number between 0.0 and 1.0
- reasons: An array of strings explaining your decision"""

        user_message = f"""Ticket Information:
Subject: {subject}
Description: {description}
Priority: {priority}
Category (from triage): {category}
Sentiment: {sentiment:.2f}
{history_context}

Which team should handle this ticket?"""

        try:
            client = get_openai_client()
            result = await client.json_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=300
            )
            
            # Validate and normalize the results
            target_team = self._validate_target_team(result.get("target_team", "general"))
            confidence = self._validate_confidence(result.get("confidence", 0.8))
            reasons = self._validate_reasons(result.get("reasons", []))
            
            return {
                "target_team": target_team,
                "confidence": confidence,
                "reasons": reasons,
                "decisions": reasons
            }
        except Exception as e:
            # Fallback to rule-based routing if OpenAI fails
            print(f"OpenAI routing failed, falling back to rule-based: {str(e)}")
            return self._make_routing_decision_fallback(ticket, triage_result, customer_history)
    
    def _validate_target_team(self, target_team: str) -> str:
        """Validate and normalize target_team value"""
        target_team = str(target_team).lower().strip()
        if target_team in ["billing", "tech", "general"]:
            return target_team
        return "general"
    
    def _validate_confidence(self, confidence: Any) -> float:
        """Validate and normalize confidence value"""
        try:
            confidence = float(confidence)
            return max(0.0, min(1.0, confidence))
        except (ValueError, TypeError):
            return 0.8
    
    def _validate_reasons(self, reasons: Any) -> list:
        """Validate and normalize reasons value"""
        if isinstance(reasons, list):
            return [str(r) for r in reasons if r]
        return [str(reasons)] if reasons else []
    
    def _make_routing_decision_fallback(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        customer_history: list
    ) -> Dict[str, Any]:
        """
        Fallback rule-based routing when OpenAI is unavailable
        
        Args:
            ticket: Ticket data
            triage_result: Results from triage agent
            customer_history: Customer's previous tickets
            
        Returns:
            Dict with target_team, confidence, and reasons
        """
        # Start with triage category
        target_team = triage_result.get("category", "general")
        reasons = [f"Based on triage category: {target_team} (fallback)"]
        confidence = 0.8
        
        # Analyze customer history for patterns
        if customer_history:
            recent_teams = [t.get("target_team") for t in customer_history[-3:]]
            if recent_teams.count("billing") >= 2:
                target_team = "billing"
                reasons.append("Customer has recent billing-related tickets")
                confidence = 0.9
            elif recent_teams.count("tech") >= 2:
                target_team = "tech"
                reasons.append("Customer has recent technical issues")
                confidence = 0.9
        
        # Priority-based routing adjustment
        priority = ticket.get("priority")
        if priority == "P1":
            reasons.append("P1 priority - routing to specialized team")
            confidence = min(confidence + 0.1, 1.0)
        
        return {
            "target_team": target_team,
            "confidence": confidence,
            "reasons": reasons,
            "decisions": reasons
        }
    
    async def _save_routing_decision(
        self,
        ticket_id: str,
        routing: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Save routing decision to database
        
        Args:
            ticket_id: ID of the ticket
            routing: Routing decision data
            session: Optional MongoDB session
        """
        routing_collection = get_collection(COLLECTION_ROUTING_DECISIONS)
        
        routing_decision = RoutingDecisionCreate(
            ticket_id=ticket_id,
            target_team=routing["target_team"],
            confidence=routing["confidence"],
            reasons=routing["reasons"]
        )
        
        routing_data = routing_decision.model_dump()
        routing_data["created_at"] = datetime.utcnow()
        
        if session:
            await routing_collection.insert_one(routing_data, session=session)
        else:
            await routing_collection.insert_one(routing_data)
        
        # Create audit log
        audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
        
        audit_log = AuditLogCreate(
            ticket_id=ticket_id,
            agent_name=self.name,
            operation=AuditOperation.ROUTE_TO_TEAM,
            before={},
            after={"target_team": routing["target_team"]}
        )
        
        audit_data = audit_log.model_dump()
        audit_data["timestamp"] = datetime.utcnow()
        
        if session:
            await audit_collection.insert_one(audit_data, session=session)
        else:
            await audit_collection.insert_one(audit_data)
    
    async def _update_ticket_phase(
        self,
        ticket_id: str,
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Update ticket phase to resolution
        
        Args:
            ticket_id: ID of the ticket
            session: Optional MongoDB session
        """
        tickets_collection = get_collection(COLLECTION_TICKETS)
        
        update_data = {
            "current_phase": TicketPhase.RESOLUTION,
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
