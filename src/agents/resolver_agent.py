from typing import Dict, Any, Optional, List
from motor.motor_asyncio import AsyncIOMotorClientSession
from .base_agent import BaseAgent, AgentResult
from src.models import (
    TicketPhase,
    TicketStatus,
    InteractionCreate,
    InteractionType,
    AuditLogCreate,
    AuditOperation,
    AIDecisionMetadata,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_AUDIT_LOGS,
)
from src.config import settings
from datetime import datetime
from src.models.company_config import CompanyConfig, Team
from src.rag.knowledge_base import knowledge_base


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
        
        # Ensure company_config is a proper object if passed as dict
        company_config_data = context.get("company_config")
        company_config = None
        if company_config_data:
            if isinstance(company_config_data, dict):
                company_config = CompanyConfig(**company_config_data)
            else:
                company_config = company_config_data
        
        if not ticket:
            return AgentResult(
                success=False,
                confidence=0.0,
                decisions={},
                message="No ticket data provided"
            )
        
        # RAG Integration: Check Knowledge Base
        kb_context = ""
        if company_config and company_config.knowledge_base and company_config.knowledge_base.enabled:
            # Determine search query (use last user message or ticket description)
            query = ticket.get("description", "")
            if interactions:
                # Find last customer message
                for i in reversed(interactions):
                    i_type = i.get("type", "") if isinstance(i, dict) else getattr(i, "type", "")
                    if i_type == "customer_message":
                        query = i.get("content", "") if isinstance(i, dict) else getattr(i, "content", "")
                        break
            
            try:
                kb_results = await knowledge_base.search(
                    query=query,
                    company_id=company_config.company_id,
                    collection_name=company_config.knowledge_base.vector_db_collection or "company_knowledge"
                )
                
                if kb_results:
                    kb_context = "\n".join([f"- {res}" for res in kb_results])
            except Exception as e:
                print(f"RAG Search failed: {e}")

        # Context Persistence: Retrieve customer's past ticket summaries
        customer_context = ""
        customer_id = ticket.get("customer_id")
        company_id = ticket.get("company_id")
        if customer_id and company_id:
            try:
                query = ticket.get("description", "")
                if interactions:
                    for i in reversed(interactions):
                        i_type = i.get("type", "") if isinstance(i, dict) else getattr(i, "type", "")
                        if i_type == "customer_message":
                            query = i.get("content", "") if isinstance(i, dict) else getattr(i, "content", "")
                            break
                
                past_summaries = await knowledge_base.search_customer_context(
                    query=query,
                    customer_id=customer_id,
                    company_id=company_id
                )
                
                if past_summaries:
                    customer_context = "\n".join([f"- {s}" for s in past_summaries])
                    print(f"Found {len(past_summaries)} relevant past interactions for customer {customer_id}")
            except Exception as e:
                print(f"Customer context retrieval failed: {e}")

        # Generate response and determine resolution
        resolution = await self._generate_resolution(
            ticket,
            triage_result,
            routing_result,
            interactions,
            company_config,
            kb_context,
            customer_context
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
        
        # Context Persistence: Generate and index summary if resolved (not escalated)
        if not resolution.get("needs_escalation", False) and customer_id and company_id:
            summary = await self._generate_conversation_summary(
                ticket,
                interactions,
                resolution.get("response", "")
            )
            if summary:
                await self._index_ticket_summary(
                    ticket_id=ticket_id,
                    customer_id=customer_id,
                    company_id=company_id,
                    summary=summary
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
        interactions: list,
        company_config: Optional[CompanyConfig] = None,
        kb_context: str = "",
        customer_context: str = ""
    ) -> Dict[str, Any]:
        """
        Generate a response and determine if escalation is needed
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
            sentiment,
            company_config,
            is_first_response=len(interactions) <= 1,
            interactions=interactions,
            kb_context=kb_context,
            customer_context=customer_context
        )
        
        # Determine if escalation is needed
        needs_escalation, escalation_reasons, confidence, escalation_reasoning = self._check_escalation_needed(
            ticket,
            triage_result,
            interactions
        )
        
        # Build reasoning for decision
        if needs_escalation:
            reasoning = escalation_reasoning
            decision_type = "escalation"
        else:
            reasoning = "Ticket resolved within normal parameters. Response generated based on context and knowledge base."
            decision_type = "resolution"
        
        return {
            "response": response,
            "target_team": target_team,
            "confidence": confidence,
            "needs_escalation": needs_escalation,
            "escalation_reasons": escalation_reasons,
            "reasoning": reasoning,
            "decision_type": decision_type,
            "message": "Response generated" if not needs_escalation else "Escalation recommended"
        }
    
    async def _generate_response_text(
        self,
        ticket: Dict[str, Any],
        target_team_id: str,
        category: str,
        priority: str,
        sentiment: float,
        company_config: Optional[CompanyConfig] = None,
        is_first_response: bool = True,
        interactions: list = [],
        kb_context: str = "",
        customer_context: str = ""
    ) -> str:
        """
        Generate a draft response based on ticket context using OpenAI
        """
        from src.utils.openai_client import get_openai_client
        
        subject = ticket.get("subject", "")
        description = ticket.get("description", "")
        
        # Identify the team config
        current_team: Optional[Team] = None
        if company_config and company_config.teams:
            for team in company_config.teams:
                if team.team_id == target_team_id:
                    current_team = team
                    break

        # Determine tone based on sentiment/team
        if current_team and current_team.is_sales:
             tone = "enthusiastic, persuasive, and helpful"
        elif sentiment < -0.5:
            tone = "empathetic and apologetic"
        elif sentiment > 0.3:
            tone = "friendly and positive"
        else:
            tone = "professional and neutral"
        
        # Determine urgency
        urgency_note = ""
        if priority == "P1":
            urgency_note = "IMPORTANT: This is a high-priority ticket and should be addressed urgently."
        
        # Build company context
        company_context = ""
        sales_context = ""
        
        if company_config:
            company_name = company_config.company_name or "nossa empresa"
            
            # Basic info
            company_info = f"""
            Empresa: {company_name}
            Horário: {company_config.business_hours or 'Não especificado'}
            """

            # Specific context based on team type
            if current_team and current_team.is_sales:
                products_str = ""
                if company_config.products:
                    for p in company_config.products:
                         products_str += f"- {p.get('name')} (ID: {p.get('id')}): {p.get('price', 'Preço sob consulta')} - {p.get('details', '')}\n"
                
                sales_context = f"""
                === CONTEXTO DE VENDAS ===
                Você está agindo como um Vendedor Especialista.
                Objetivo: Tirar dúvidas, apresentar produtos e convencer o cliente a fechar negócio.
                
                Instruções do Time ({current_team.name}):
                {current_team.instructions or "Foque em apresentar os benefícios e fechar a venda."}
                
                Catálogo de Produtos/Serviços:
                {products_str}
                
                Se o cliente perguntar preço, consulte a lista acima.
                Se o produto não estiver na lista, peça para entrar em contato com um humano.
                === FIM CONTEXTO DE VENDAS ===
                """
            
            # General Support Policy Context
            policy_context = f"""
            === POLÍTICAS ===
            Reembolso: {company_config.refund_policy or 'Não especificada'}
            Cancelamento: {company_config.cancellation_policy or 'Não especificada'}
            Pagamento: {', '.join(company_config.payment_methods) if company_config.payment_methods else 'Não especificados'}
            === FIM POLÍTICAS ===
            """
            
            company_context = company_info + "\n" + sales_context + "\n" + policy_context
        
        # RAG Context
        rag_section = ""
        if kb_context:
            rag_section = f"""
            === RELEVANT KNOWLEDGE BASE ===
            Use this information to answer if applicable:
            {kb_context}
            === END KNOWLEDGE BASE ===
            """

        # Customer History Context
        customer_history_section = ""
        if customer_context:
            customer_history_section = f"""
            === CUSTOMER HISTORY ===
            This customer has interacted with us before. Here are relevant past interactions:
            {customer_context}
            
            Use this context to provide personalized support. Reference past issues if relevant.
            === END CUSTOMER HISTORY ===
            """

        # Dynamic instructions based on conversation state
        greeting_instruction = "- Start with a friendly greeting ONLY if this is the start of the conversation." if is_first_response else "- DO NOT use a greeting as we are already talking."
        closing_instruction = "- Only use a closing if you are resolving the issue or ending the chat."
        
        # System prompt
        system_prompt = f"""You are a customer support agent for the {current_team.name if current_team else target_team_id} team.
        
{company_context}

{rag_section}

{customer_history_section}

Important guidelines:
- Be {tone} and conversational.
{greeting_instruction}
- Address the customer's specific issue directly.
- Use natural, everyday Portuguese.
{closing_instruction}
- IF you used information from the Knowledge Base, explain it clearly to the user.
- IF you have customer history context, use it to provide personalized support.

{urgency_note}

Remember: You're having a conversation with a real person. Be warm and helpful."""

        # Build conversation history
        history_text = ""
        last_user_message = description 
        
        if interactions:
            history_lines = []
            for interaction in interactions:
                # Handle interaction object being either dict or object
                i_type = interaction.get("type", "") if isinstance(interaction, dict) else getattr(interaction, "type", "")
                i_content = interaction.get("content", "") if isinstance(interaction, dict) else getattr(interaction, "content", "")
                
                if i_type == "customer_message":
                    history_lines.append(f"Customer: {i_content}")
                    last_user_message = i_content
                elif i_type == "agent_response":
                    history_lines.append(f"You: {i_content}")
            
            history_text = "\n".join(history_lines[-10:])

        user_message = f"""Context:
Subject: {subject}
Category: {category}
Priority: {priority}
Sentiment: {sentiment:.2f}

Conversation History:
{history_text}

Latest Customer Message:
{last_user_message}
 
Generate a response."""

        try:
            client = get_openai_client()
            response = await client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.7,
                max_tokens=600
            )
            return response.strip()
        except Exception as e:
            print(f"OpenAI response generation failed: {str(e)}")
            return self._generate_response_text_fallback(ticket, target_team_id, category, priority, sentiment)
    
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
        """
        subject = ticket.get("subject", "")
        
        greeting = "Olá,"
        
        if category == "billing":
            response = f"{greeting}\n\nEntendi que você precisa de ajuda com faturamento sobre '{subject}'. Por favor, aguarde enquanto verifico."
        elif category == "tech":
             response = f"{greeting}\n\nVi que você está com um problema técnico sobre '{subject}'. Poderia me dar mais detalhes?"
        else:
             response = f"{greeting}\n\nComo posso te ajudar hoje com '{subject}'?"
             
        return response

    def _check_escalation_needed(
        self,
        ticket: Dict[str, Any],
        triage_result: Dict[str, Any],
        interactions: list
    ) -> tuple:
        """
        Check if the ticket needs to be escalated based on rules
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
        
        # Rule 3: Check SLA breach
        created_at = ticket.get("created_at")
        if created_at:
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at)
                except:
                    pass # Ignore parsing error
                    
            if isinstance(created_at, datetime):
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
        
        # Build reasoning string
        if needs_escalation:
            reasoning = f"Escalation triggered due to: {', '.join(reasons)}"
        else:
            reasoning = "Ticket resolved within normal parameters"
        
        return needs_escalation, reasons, confidence, reasoning
    
    async def _save_response(
        self,
        ticket_id: str,
        resolution: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Save the response as an interaction
        """
        interactions_collection = get_collection(COLLECTION_INTERACTIONS)
        
        # Build AI metadata for transparency
        decision_type = resolution.get("decision_type", "resolution")
        ai_metadata = AIDecisionMetadata(
            confidence_score=resolution.get("confidence", 0.7),
            reasoning=resolution.get("reasoning"),
            decision_type=decision_type,
            factors=resolution.get("escalation_reasons", [])
        )
        
        interaction = InteractionCreate(
            ticket_id=ticket_id,
            type=InteractionType.AGENT_RESPONSE,
            content=resolution["response"],
            sentiment_score=0.0,
            ai_metadata=ai_metadata
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

    async def _generate_conversation_summary(
        self,
        ticket: Dict[str, Any],
        interactions: list,
        resolution_response: str
    ) -> Optional[str]:
        """
        Generate an AI summary of the conversation for context persistence.
        
        Args:
            ticket: The ticket data
            interactions: List of conversation interactions
            resolution_response: The final resolution response
            
        Returns:
            A concise summary of the conversation, or None if failed
        """
        from src.utils.openai_client import get_openai_client
        
        # Build conversation text
        conversation_lines = []
        for interaction in interactions:
            i_type = interaction.get("type", "") if isinstance(interaction, dict) else getattr(interaction, "type", "")
            i_content = interaction.get("content", "") if isinstance(interaction, dict) else getattr(interaction, "content", "")
            
            if i_type == "customer_message":
                conversation_lines.append(f"Customer: {i_content}")
            elif i_type == "agent_response":
                conversation_lines.append(f"Agent: {i_content}")
        
        # Add final resolution
        conversation_lines.append(f"Agent (Final): {resolution_response}")
        
        conversation_text = "\n".join(conversation_lines[-15:])  # Last 15 messages
        
        system_prompt = """You are a summarization assistant. Create a concise summary of the following customer support conversation.

Focus on:
- The customer's main issue/request
- Key information shared (product names, order numbers, preferences)
- How the issue was resolved
- Any customer preferences or communication style noted

Keep the summary under 150 words. Use bullet points for key facts."""

        user_message = f"""Ticket Subject: {ticket.get('subject', 'N/A')}
Category: {ticket.get('category', 'general')}

Conversation:
{conversation_text}

Generate a concise summary for future reference."""

        try:
            client = get_openai_client()
            summary = await client.chat_completion(
                system_prompt=system_prompt,
                user_message=user_message,
                temperature=0.3,
                max_tokens=200
            )
            return summary.strip()
        except Exception as e:
            print(f"Conversation summarization failed: {e}")
            return None

    async def _index_ticket_summary(
        self,
        ticket_id: str,
        customer_id: str,
        company_id: str,
        summary: str
    ) -> bool:
        """
        Index the ticket summary in the knowledge base for cross-ticket retrieval.
        
        Args:
            ticket_id: The ticket identifier
            customer_id: The customer identifier
            company_id: The company identifier
            summary: The conversation summary
            
        Returns:
            True if successfully indexed
        """
        try:
            success = await knowledge_base.add_ticket_summary(
                summary=summary,
                ticket_id=ticket_id,
                customer_id=customer_id,
                company_id=company_id
            )
            if success:
                print(f"Indexed ticket summary for customer {customer_id}, ticket {ticket_id}")
            return success
        except Exception as e:
            print(f"Failed to index ticket summary: {e}")
            return False
