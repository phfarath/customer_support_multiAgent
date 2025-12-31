"""
Agent Pipeline - Orchestrates the execution of all agents
"""
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorClientSession
from src.agents import (
    TriageAgent,
    RouterAgent,
    ResolverAgent,
    EscalatorAgent,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_ROUTING_DECISIONS,
)
from src.database.transactions import with_transaction


class AgentPipeline:
    """
    Orchestrates the execution of all agents in sequence
    """
    
    def __init__(self):
        self.triage_agent = TriageAgent()
        self.router_agent = RouterAgent()
        self.resolver_agent = ResolverAgent()
        self.escalator_agent = EscalatorAgent()
    
    @with_transaction
    async def run_pipeline(
        self,
        ticket_id: str,
        session: AsyncIOMotorClientSession
    ) -> Dict[str, Any]:
        """
        Run the complete agent pipeline for a ticket
        
        Args:
            ticket_id: ID of the ticket to process
            session: MongoDB session for transactions
            
        Returns:
            Dict with results from all agents
        """
        # Get ticket data
        ticket = await self._get_ticket(ticket_id, session)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Get interactions
        interactions = await self._get_interactions(ticket_id, session)
        
        # Build context
        context = {
            "ticket": ticket,
            "interactions": interactions,
            "customer_history": await self._get_customer_history(
                ticket.get("customer_id"),
                session
            )
        }
        
        # Execute agents in sequence
        
        # 1. Triage Agent
        triage_result = await self.triage_agent.execute(
            ticket_id,
            context,
            session
        )
        context["triage_result"] = triage_result.decisions
        
        # 2. Router Agent
        routing_result = await self.router_agent.execute(
            ticket_id,
            context,
            session
        )
        context["routing_result"] = routing_result.decisions
        
        # 3. Resolver Agent
        resolver_result = await self.resolver_agent.execute(
            ticket_id,
            context,
            session
        )
        context["resolver_result"] = resolver_result.decisions
        
        # 4. Escalator Agent
        escalator_result = await self.escalator_agent.execute(
            ticket_id,
            context,
            session
        )
        
        # Return pipeline results
        return {
            "ticket_id": ticket_id,
            "triage": {
                "success": triage_result.success,
                "confidence": triage_result.confidence,
                "decisions": triage_result.decisions,
                "message": triage_result.message
            },
            "routing": {
                "success": routing_result.success,
                "confidence": routing_result.confidence,
                "decisions": routing_result.decisions,
                "message": routing_result.message
            },
            "resolution": {
                "success": resolver_result.success,
                "confidence": resolver_result.confidence,
                "decisions": resolver_result.decisions,
                "message": resolver_result.message
            },
            "escalation": {
                "success": escalator_result.success,
                "escalate_to_human": escalator_result.needs_escalation,
                "decisions": escalator_result.decisions,
                "message": escalator_result.message
            },
            "final_status": "escalated" if escalator_result.needs_escalation else "in_progress"
        }
    
    async def _get_ticket(
        self,
        ticket_id: str,
        session: AsyncIOMotorClientSession
    ) -> Dict[str, Any]:
        """
        Get ticket data from database
        
        Args:
            ticket_id: ID of the ticket
            session: MongoDB session
            
        Returns:
            Ticket data or None
        """
        collection = await get_collection(COLLECTION_TICKETS)
        ticket = await collection.find_one(
            {"ticket_id": ticket_id},
            session=session
        )
        return ticket
    
    async def _get_interactions(
        self,
        ticket_id: str,
        session: AsyncIOMotorClientSession
    ) -> List[Dict[str, Any]]:
        """
        Get interactions for a ticket
        
        Args:
            ticket_id: ID of the ticket
            session: MongoDB session
            
        Returns:
            List of interactions
        """
        collection = await get_collection(COLLECTION_INTERACTIONS)
        cursor = collection.find(
            {"ticket_id": ticket_id},
            session=session
        ).sort("created_at", 1)
        
        interactions = []
        async for interaction in cursor:
            interactions.append(interaction)
        
        return interactions
    
    async def _get_customer_history(
        self,
        customer_id: str,
        session: AsyncIOMotorClientSession
    ) -> List[Dict[str, Any]]:
        """
        Get customer's previous tickets (simulated)
        
        Args:
            customer_id: ID of the customer
            session: MongoDB session
            
        Returns:
            List of previous tickets
        """
        collection = await get_collection(COLLECTION_TICKETS)
        cursor = collection.find(
            {"customer_id": customer_id},
            session=session
        ).sort("created_at", -1).limit(5)
        
        history = []
        async for ticket in cursor:
            # Get routing decision for this ticket
            routing_collection = await get_collection(COLLECTION_ROUTING_DECISIONS)
            routing = await routing_collection.find_one(
                {"ticket_id": ticket.get("ticket_id")},
                session=session
            )
            
            history.append({
                "ticket_id": ticket.get("ticket_id"),
                "priority": ticket.get("priority"),
                "status": ticket.get("status"),
                "target_team": routing.get("target_team") if routing else "general"
            })
        
        return history
