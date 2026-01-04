"""
Resolver Agent - Generates responses and attempts to resolve tickets
"""
from typing import Dict, Any, Optional
from motor.motor_asyncio import AsyncIOMotorClientSession
from .base_agent import BaseAgent, AgentResult
from src.models import (
    TicketPhase,
    TicketStatus,
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


class ResolverAgent(BaseAgent):
    """
    Resolver Agent attempts to resolve tickets by:
    - Analyzing the full context (ticket, triage, routing, interactions)
    - Generating a draft response
    - Determining if the issue can be resolved or needs escalation
    """
    
    def __init__(self):
        super().__init__("resolver")
    
    def get_phase_name(self) -> str:
        return TicketPhase.RESOLUTION
    
    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> AgentResult:
        """
        Execute resolution attempt for a ticket
        
        Args:
            ticket_id: ID of the ticket
            context: Contains ticket data, triage, routing, and interactions
            session: Optional MongoDB session for transactions
            
        Returns:
            AgentResult with draft response and resolution status
        """
        ticket = context.get("ticket")
        triage_result = context.get("triage_result", {})
        routing_result = context.get("routing_result", {})
        interactions = context.get("interactions", [])
        
        if not ticket:
            return AgentResult(
                success=False,
                confidence=0.0,
                decisions={},
                message="No ticket data provided"
            )
        
        # Generate response and determine resolution
        resolution = await self._generate_resolution(
            ticket,
            triage_result,
            routing_result,
            interactions
        )
        
        # Save response interaction
        await self._save_response(
            ticket_id,
            resolution,
            session
        )
        
        # Save agent state
        await self.save_agent_state(
            ticket_id,
            resolution,
            session
        )
        
        return AgentResult(
            success=True,
            confidence=resolution.get("confidence", 0.7),
            decisions=resolution,
            message=resolution.get("message", "Response generated"),
            needs_escalation=resolution.get("needs_escalation", False),
            escalation_reasons=resolution.get("escalation_reasons", [])
        )
    
    async def _generate_resolution(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        routing_result: Dict[str, Any],
        interactions: list
    ) -> Dict[str, Any]:
        """
        Generate a response and determine if escalation is needed
        
        Args:
            ticket: Ticket data
            triage_result: Results from triage agent
            routing_result: Results from router agent
            interactions: List of previous interactions
            
        Returns:
            Dict with response, confidence, and escalation decision
        """
        target_team = routing_result.get("target_team", "general")
        priority = ticket.get("priority", "P3")
        category = triage_result.get("category", "general")
        sentiment = triage_result.get("sentiment", 0.0)
        
        # Generate response based on team and category
        response = await self._generate_response_text(
            ticket,
            target_team,
            category,
            priority,
            sentiment
        )
        
        # Determine if escalation is needed
        needs_escalation, escalation_reasons, confidence = self._check_escalation_needed(
            ticket,
            triage_result,
            interactions
        )
        
        return {
            "response": response,
            "target_team": target_team,
            "confidence": confidence,
            "needs_escalation": needs_escalation,
            "escalation_reasons": escalation_reasons,
            "message": "Response generated" if not needs_escalation else "Escalation recommended"
        }
    
    async def _generate_response_text(
        self,
        ticket: Dict[str, Any],
        target_team: str,
        category: str,
        priority: str,
        sentiment: float
    ) -> str:
        """
        Generate a draft response based on ticket context using OpenAI
        
        Args:
            ticket: Ticket data
            target_team: Team assigned to handle
            category: Ticket category
            priority: Ticket priority
            sentiment: Customer sentiment score
            
        Returns:
            Draft response text
        """
        from src.utils.openai_client import get_openai_client
        
        subject = ticket.get("subject", "")
        description = ticket.get("description", "")
        channel = ticket.get("channel", "")
        
        # Determine tone based on sentiment
        if sentiment < -0.5:
            tone = "empathetic and apologetic"
        elif sentiment > 0.3:
            tone = "friendly and positive"
        else:
            tone = "professional and neutral"
        
        # Determine urgency based on priority
        urgency_note = ""
        if priority == "P1":
            urgency_note = "IMPORTANT: This is a high-priority ticket and should be addressed urgently."
        
        # System prompt for response generation
        system_prompt = f"""You are a customer support agent for the {target_team} team. Generate a helpful, professional response to the customer's inquiry.

Guidelines:
- Be {tone} in your tone
- Address the customer's specific issue
- Provide helpful next steps or information
- Keep the response concise but comprehensive
- Use Portuguese language
- Sign off appropriately as the {target_team} team

{urgency_note}"""

        user_message = f"""Customer Inquiry:
Subject: {subject}
Description: {description}
Channel: {channel}
Category: {category}
Priority: {priority}
Sentiment: {sentiment:.2f}

Generate a helpful response to this customer."""

        try:
            client = get_openai_client()
            response = await client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                max_tokens=500
            )
            return response.strip()
        except Exception as e:
            # Fallback to template-based response if OpenAI fails
            print(f"OpenAI response generation failed, falling back to template: {str(e)}")
            return self._generate_response_text_fallback(ticket, target_team, category, priority, sentiment)
    
    def _generate_response_text_fallback(
        self,
        ticket: Dict[str, Any],
        target_team: str,
        category: str,
        priority: str,
        sentiment: float
    ) -> str:
        """
        Fallback template-based response when OpenAI is unavailable
        
        Args:
            ticket: Ticket data
            target_team: Team assigned to handle
            category: Ticket category
            priority: Ticket priority
            sentiment: Customer sentiment score
            
        Returns:
            Draft response text
        """
        subject = ticket.get("subject", "")
        description = ticket.get("description", "")
        
        # Adjust tone based on sentiment
        if sentiment < -0.5:
            greeting = "Prezado(a) cliente,"
            apology = "Lamentamos muito pela experiência negativa."
        elif sentiment > 0.3:
            greeting = "Olá,"
            apology = ""
        else:
            greeting = "Prezado(a) cliente,"
            apology = ""
        
        # Generate response based on category
        if category == "billing":
            response = f"""{greeting}

Obrigado por entrar em contato conosco. {apology}

Recebemos sua solicitação sobre: {subject}

Nossa equipe de cobranças está analisando o seu caso. Para prosseguirmos, precisamos de algumas informações adicionais:
- Número do pedido ou transação
- Data da cobrança
- Comprovante de pagamento (se aplicável)

Estamos trabalhando para resolver isso o mais rápido possível.

Atenciosamente,
Equipe de Cobranças"""
        
        elif category == "tech":
            response = f"""{greeting}

Obrigado por reportar este problema. {apology}

Recebemos sua solicitação sobre: {subject}

Nossa equipe técnica está analisando o seu caso. Para nos ajudar a diagnosticar o problema:
- Qual dispositivo/sistema você está usando?
- Quando o problema começou?
- Você já tentou alguma solução?

Estamos trabalhando para resolver isso o mais rápido possível.

Atenciosamente,
Equipe Técnica"""
        
        else:  # general
            response = f"""{greeting}

Obrigado por entrar em contato conosco. {apology}

Recebemos sua solicitação sobre: {subject}

Nossa equipe está analisando sua solicitação e retornaremos em breve com uma resposta.

Atenciosamente,
Equipe de Atendimento"""
        
        # Add priority note for P1 tickets
        if priority == "P1":
            response += f"""

NOTA: Sua solicitação foi marcada como PRIORIDADE ALTA e está sendo tratada com urgência."""
        
        return response
    
    def _check_escalation_needed(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        interactions: list
    ) -> tuple:
        """
        Check if the ticket needs to be escalated based on rules
        
        Args:
            ticket: Ticket data
            triage_result: Results from triage agent
            interactions: List of previous interactions
            
        Returns:
            Tuple of (needs_escalation, reasons, confidence)
        """
        needs_escalation = False
        reasons = []
        confidence = 0.8
        
        priority = ticket.get("priority", "P3")
        sentiment = triage_result.get("sentiment", 0.0)
        interactions_count = len(interactions)
        
        # Rule 1: P1 with too many interactions
        if priority == "P1" and interactions_count > settings.escalation_max_interactions:
            needs_escalation = True
            reasons.append(f"P1 ticket with {interactions_count} interactions")
            confidence = min(confidence - 0.2, 0.5)
        
        # Rule 2: Very negative sentiment
        if sentiment < settings.escalation_min_sentiment:
            needs_escalation = True
            reasons.append(f"Negative sentiment: {sentiment:.2f}")
            confidence = min(confidence - 0.15, 0.5)
        
        # Rule 3: Check SLA breach (time since creation)
        created_at = ticket.get("created_at")
        if created_at:
            time_diff = datetime.utcnow() - created_at
            hours_diff = time_diff.total_seconds() / 3600
            if hours_diff > settings.escalation_sla_hours:
                needs_escalation = True
                reasons.append(f"SLA breach: {hours_diff:.1f} hours")
                confidence = min(confidence - 0.1, 0.6)
        
        # Rule 4: Low confidence from triage
        triage_confidence = triage_result.get("confidence", 0.8)
        if triage_confidence < settings.escalation_min_confidence:
            needs_escalation = True
            reasons.append(f"Low triage confidence: {triage_confidence:.2f}")
            confidence = min(confidence - 0.1, 0.6)
        
        return needs_escalation, reasons, confidence
    
    async def _save_response(
        self,
        ticket_id: str,
        resolution: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Save the response as an interaction
        
        Args:
            ticket_id: ID of the ticket
            resolution: Resolution data with response
            session: Optional MongoDB session
        """
        interactions_collection = await get_collection(COLLECTION_INTERACTIONS)
        
        interaction = InteractionCreate(
            ticket_id=ticket_id,
            type=InteractionType.AGENT_RESPONSE,
            content=resolution["response"],
            sentiment_score=0.0
        )
        
        interaction_data = interaction.model_dump()
        interaction_data["created_at"] = datetime.utcnow()
        
        if session:
            await interactions_collection.insert_one(interaction_data, session=session)
        else:
            await interactions_collection.insert_one(interaction_data)
        
        # Create audit log
        audit_collection = await get_collection(COLLECTION_AUDIT_LOGS)
        
        audit_log = AuditLogCreate(
            ticket_id=ticket_id,
            agent_name=self.name,
            operation=AuditOperation.AGENT_EXECUTION,
            before={},
            after={
                "response_generated": True,
                "needs_escalation": resolution.get("needs_escalation", False),
                "confidence": resolution.get("confidence", 0.0)
            }
        )
        
        audit_data = audit_log.model_dump()
        audit_data["timestamp"] = datetime.utcnow()
        
        if session:
            await audit_collection.insert_one(audit_data, session=session)
        else:
            await audit_collection.insert_one(audit_data)
