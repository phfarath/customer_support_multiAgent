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
        company_config = context.get("company_config")
        
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
        
        # Build company context for the prompt
        company_context = ""
        if company_config:
            company_name = company_config.company_name or "nossa empresa"
            company_context = f"""
            
            === CONTEXTO DA EMPRESA ===
            Empresa: {company_name}
            
            Políticas:
            - Política de Reembolso: {company_config.refund_policy or 'Não especificada'}
            - Política de Cancelamento: {company_config.cancellation_policy or 'Não especificada'}
            
            Métodos de Pagamento: {', '.join(company_config.payment_methods) if company_config.payment_methods else 'Não especificados'}
            
            Produtos/Serviços: {', '.join([p.get('name', 'Produto não especificado') for p in (company_config.products or [])])}
            
            Horário de Atendimento: {company_config.business_hours or 'Não especificado'}
            
            === FIM DO CONTEXTO ===
            """
        
        # System prompt for response generation
        system_prompt = f"""You are a friendly customer support bot for the {target_team} team. Your goal is to help customers in a natural, conversational way.

Important guidelines:
- Be {tone} and conversational - write like a real person would speak
- Start with a friendly greeting (Olá, Oi, Bom dia, etc.)
- Address the customer's specific issue directly
- Provide helpful next steps or information clearly
- Keep responses concise but comprehensive
- Use natural, everyday Portuguese - avoid overly formal language
- Don't use phrases like "Prezado(a) cliente" - be more personal
- Sign off naturally (Até logo, Um abraço, etc.)
- Present yourself as a helpful support assistant, not a robot

{company_context}

{urgency_note}

Remember: You're having a conversation with a real person. Be warm, understanding, and helpful."""

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
            greeting = "Oi,"
            apology = "Sinto muito que você teve uma experiência ruim."
        elif sentiment > 0.3:
            greeting = "Olá,"
            apology = ""
        else:
            greeting = "Oi,"
            apology = ""
        
        # Generate response based on category
        if category == "billing":
            response = f"""{greeting}
 
Entendi que você precisa de ajuda com faturamento. {apology}
 
Sobre: {subject}
 
Para te ajudar melhor, me conta um pouco mais sobre o que aconteceu? Preciso de:
- Número do pedido ou transação
- Quando foi a cobrança
- Se tem algum comprovante
 
Assim que eu consiga te ajudar da melhor forma!
 
Um abraço"""
        
        elif category == "tech":
            response = f"""{greeting}
 
Vi que você está com um problema técnico. {apology}
 
Sobre: {subject}
 
Vamos resolver isso juntos! Para eu entender melhor:
- Qual dispositivo ou sistema você está usando?
- Quando o problema começou?
- Já tentou alguma solução?
 
Me avisa se precisar de mais alguma coisa, tá?
 
Um abraço"""
        
        else:  # general
            response = f"""{greeting}
 
Obrigado por entrar em contato! {apology}
 
Sobre: {subject}
 
Como posso te ajudar hoje? Me conta mais detalhes sobre o que precisa.
 
Fico aguardando sua resposta para te dar o melhor suporte possível.
 
Um abraço"""
        
        # Add priority note for P1 tickets
        if priority == "P1":
            response += f"""
 
⚠️ Sua solicitação é prioridade alta, então vou te ajudar com urgência!"""
        
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
        interactions_collection = get_collection(COLLECTION_INTERACTIONS)
        
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
        audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
        
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
