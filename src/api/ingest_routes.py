"""
FastAPI routes for channel-agnostic message ingestion
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from typing import Dict, Any
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.models import (
    IngestMessageRequest,
    IngestMessageResponse,
    TicketChannel,
    TicketStatus,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_INTERACTIONS,
    COLLECTION_COMPANY_CONFIGS,
)
from src.database.ticket_operations import (
    find_or_create_ticket,
    add_interaction,
    update_ticket_interactions_count,
    update_ticket_status,
)
from src.utils import AgentPipeline
from src.utils.email_notifier import send_escalation_email
from src.utils.ticket_lifecycle import (
    cancel_pending_events,
    schedule_lifecycle_events_for_escalated_ticket,
)
from src.models.interaction import InteractionType
from src.models import CompanyConfig, TicketLifecycleConfig
from src.middleware.auth import verify_api_key
from src.utils.sanitization import (
    sanitize_text,
    sanitize_text_with_pii_detection,
    sanitize_identifier,
    sanitize_company_id
)
from src.security.error_handler import SecureError

import logging
logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api", tags=["ingest"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


async def _get_company_config(company_id: str) -> CompanyConfig | None:
    if not company_id:
        return None
    collection = get_collection(COLLECTION_COMPANY_CONFIGS)
    config = await collection.find_one({"company_id": company_id})
    if not config:
        return None
    config["_id"] = str(config.get("_id"))
    return CompanyConfig(**config)


async def _get_last_interactions(ticket_id: str, limit: int = 3) -> list[Dict[str, Any]]:
    collection = get_collection(COLLECTION_INTERACTIONS)
    cursor = collection.find({"ticket_id": ticket_id}).sort("created_at", -1).limit(limit)
    interactions = []
    async for interaction in cursor:
        interactions.append(interaction)
    return list(reversed(interactions))


def _generate_warning_message(
    reasons: list[str], 
    company_config: CompanyConfig | None = None
) -> str:
    """
    Generate warning message before escalation explaining why.
    
    Args:
        reasons: List of escalation reasons
        company_config: Optional company configuration
    
    Returns:
        Formatted warning message for the customer
    """
    # Build default message
    default_message = (
        "⚠️ Para melhor atendê-lo, sua solicitação será transferida "
        "para um de nossos especialistas."
    )
    
    if reasons:
        if len(reasons) == 1:
            reason_summary = reasons[0]
        else:
            reason_summary = f"{reasons[0]} e {reasons[1]}"
        default_message += f" Motivo: {reason_summary}."
    
    default_message += " Aguarde um momento, por favor."
    
    # Check for custom template
    if company_config and company_config.handoff_warning_message:
        try:
            return company_config.handoff_warning_message.format(
                reason=reasons[0] if reasons else "necessidade de especialista",
                reasons=", ".join(reasons) if reasons else "necessidade de especialista"
            )
        except Exception:
            return company_config.handoff_warning_message
    
    return default_message


@router.post("/ingest-message", response_model=IngestMessageResponse)
@limiter.limit("20/minute")  # Rate limit: 20 messages per minute
async def ingest_message(
    request: Request,  # Required by slowapi
    payload: IngestMessageRequest,
    api_key: dict = Depends(verify_api_key)
) -> IngestMessageResponse:
    """
    Channel-agnostic endpoint for ingesting messages from any channel

    Requires: X-API-Key header

    This endpoint handles incoming messages from Telegram, WhatsApp, or any other channel.
    It will:
    1. Find or create a ticket for the user on the specified channel
    2. Add the message as a customer interaction
    3. Run the agent pipeline to generate a response
    4. Return the response text and escalation status

    Args:
        request: Message ingestion request with channel, external_user_id, and text
        api_key: Authenticated API key (auto-injected)

    Returns:
        Response with reply_text, escalation status, and ticket information
    """
    # request is required by slowapi decorator, even when not directly used here.
    _ = request
    return await process_ingest_message(
        payload=payload,
        authenticated_company_id=api_key["company_id"],
    )


async def process_ingest_message(
    payload: IngestMessageRequest,
    authenticated_company_id: str | None = None,
) -> IngestMessageResponse:
    """
    Core ingestion workflow reusable by HTTP routes and internal callers.

    Args:
        payload: Message ingestion payload
        authenticated_company_id: Company ID asserted by auth context (if any)
    """
    logger.info(f"Received ingest message request: {payload}")

    # Enforce company isolation
    if authenticated_company_id and payload.company_id and payload.company_id != authenticated_company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot ingest message for different company"
        )

    # Set company_id from authenticated context if not provided
    if not payload.company_id and authenticated_company_id:
        payload.company_id = authenticated_company_id

    # SANITIZE ALL INPUTS
    try:
        company_id = sanitize_company_id(payload.company_id)
        external_user_id = sanitize_identifier(payload.external_user_id)

        # Sanitize text WITH PII detection for LGPD/GDPR compliance
        text, pii_detected, pii_types = sanitize_text_with_pii_detection(
            payload.text, max_length=4000
        )

    except ValueError as e:
        logger.warning(f"Input validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )
    
    # Log PII detection for audit purposes
    if pii_detected:
        logger.info(f"PII detected in message for company {company_id}: types={pii_types}")

    pipeline = AgentPipeline()
    tickets_collection = get_collection(COLLECTION_TICKETS)
    now = datetime.utcnow()
    company_config = await _get_company_config(company_id)
    lifecycle_cfg = company_config.lifecycle_config if company_config else TicketLifecycleConfig()
    company_config_dict = company_config.model_dump() if company_config else None

    try:
        # Convert IngestChannel to TicketChannel
        logger.info(f"Converting channel: {payload.channel} to TicketChannel")
        ticket_channel = TicketChannel(payload.channel.value)
        logger.info(f"TicketChannel: {ticket_channel}")
        
        # Find or create ticket (using sanitized values)
        logger.info("Finding or creating ticket...")
        ticket, is_new_ticket = await find_or_create_ticket(
            external_user_id=external_user_id,
            channel=ticket_channel,
            text=text,
            company_id=company_id
        )
        logger.info(f"Ticket found/created: ticket_id={ticket.get('ticket_id')}, is_new={is_new_ticket}")

        ticket_id = ticket["ticket_id"]
        was_escalated = ticket.get("status") == TicketStatus.ESCALATED
        was_auto_resolved = ticket.get("status") == TicketStatus.AUTO_RESOLVED

        # Reopen auto-closed tickets on customer reply when enabled.
        if was_auto_resolved and lifecycle_cfg.reopen_on_customer_reply:
            await tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {
                    "$set": {
                        "status": TicketStatus.ESCALATED,
                        "lifecycle_stage": None,
                        "reopened_at": now,
                        "updated_at": now,
                    },
                    "$inc": {"reopen_count": 1},
                },
            )
            await cancel_pending_events(ticket_id)
            was_escalated = True
            ticket["status"] = TicketStatus.ESCALATED

        # Cold escalated tickets should not block new requests forever.
        if was_escalated:
            reference_time = ticket.get("last_customer_message_at") or ticket.get("updated_at") or ticket.get("created_at")
            if reference_time:
                age_hours = (now - reference_time).total_seconds() / 3600
                if age_hours >= lifecycle_cfg.auto_close_hours:
                    await tickets_collection.update_one(
                        {"ticket_id": ticket_id},
                        {
                            "$set": {
                                "status": TicketStatus.AUTO_RESOLVED,
                                "lifecycle_stage": "auto_closed_cold_start",
                                "auto_closed_at": now,
                                "updated_at": now,
                            }
                        },
                    )
                    await cancel_pending_events(ticket_id)

                    ticket, is_new_ticket = await find_or_create_ticket(
                        external_user_id=external_user_id,
                        channel=ticket_channel,
                        text=text,
                        company_id=company_id,
                        include_escalated=False,
                    )
                    ticket_id = ticket["ticket_id"]
                    was_escalated = False
                    logger.info(
                        "Created new ticket for stale escalated conversation: old_age_hours=%.1f new_ticket_id=%s",
                        age_hours,
                        ticket_id,
                    )

        await tickets_collection.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"last_customer_message_at": now, "updated_at": now}},
        )

        # Add customer interaction (using sanitized text with PII info)
        await add_interaction(
            ticket_id=ticket_id,
            interaction_type=InteractionType.CUSTOMER_MESSAGE,
            content=text,
            channel=payload.channel.value,
            pii_detected=pii_detected,
            pii_types=pii_types
        )
        
        # Update ticket interactions count
        await update_ticket_interactions_count(ticket_id)

        # Create audit log for message ingestion (using sanitized values)
        audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
        await audit_collection.insert_one({
            "ticket_id": ticket_id,
            "agent_name": "system",
            "operation": "INGEST_MESSAGE",
            "before": {},
            "after": {
                "channel": payload.channel.value,
                "external_user_id": external_user_id,
                "text": text,
                "is_new_ticket": is_new_ticket,
                "pii_detected": pii_detected,
                "pii_types": pii_types
            },
            "timestamp": datetime.utcnow()
        })

        if was_escalated:
            await cancel_pending_events(ticket_id)
            await schedule_lifecycle_events_for_escalated_ticket(
                ticket=ticket,
                company_config=company_config_dict,
                now=now,
            )
            return IngestMessageResponse(
                success=True,
                ticket_id=ticket_id,
                reply_text=None,
                escalated=True,
                message="Ticket already escalated to human agent",
                ticket_status=ticket.get("status")
            )
        
        # Run agent pipeline
        logger.info(f"Running agent pipeline for ticket_id: {ticket_id}")
        results = await pipeline.run_pipeline(ticket_id)
        logger.info(f"Pipeline results: {results}")
        
        # Extract the resolver's response
        resolver_response = results.get("resolution", {}).get("decisions", {})
        reply_text = resolver_response.get("response", "Thank you for your message. We're processing your request.")
        
        # Check if escalated
        escalated = results.get("escalation", {}).get("escalate_to_human", False)
        escalation_reasons = results.get("escalation", {}).get("decisions", {}).get("reasons", [])
        
        # Update ticket status based on escalation
        if escalated:
            await update_ticket_status(ticket_id, TicketStatus.ESCALATED)
        else:
            await update_ticket_status(ticket_id, TicketStatus.IN_PROGRESS)
        
        if escalated and not was_escalated:
            from src.config import settings
            
            # 1. Generate warning message (BEFORE escalation confirmation)
            warning_message = _generate_warning_message(
                reasons=escalation_reasons,
                company_config=company_config
            )
            
            # 2. Generate handoff message (confirmation)
            handoff_message = settings.escalation_handoff_message
            if company_config and company_config.bot_handoff_message:
                handoff_message = company_config.bot_handoff_message
            try:
                handoff_message = handoff_message.format(ticket_id=ticket_id)
            except Exception:
                pass
            
            # 3. Combine: Warning + Handoff
            reply_text = f"{warning_message}\n\n{handoff_message}"
        elif escalated:
            reply_text = None

        if reply_text:
            # Add agent response as interaction
            await add_interaction(
                ticket_id=ticket_id,
                interaction_type=InteractionType.AGENT_RESPONSE,
                content=reply_text,
                channel=payload.channel.value
            )

            await tickets_collection.update_one(
                {"ticket_id": ticket_id},
                {"$set": {"last_agent_message_at": datetime.utcnow(), "updated_at": datetime.utcnow()}},
            )

            # Update ticket interactions count again
            await update_ticket_interactions_count(ticket_id)

        if escalated and not was_escalated:
            await schedule_lifecycle_events_for_escalated_ticket(
                ticket=ticket,
                company_config=company_config_dict,
                now=datetime.utcnow(),
            )
            escalation_email = None
            company_name = None
            if company_config:
                escalation_email = company_config.escalation_email
                company_name = company_config.company_name
            if not escalation_email:
                from src.config import settings
                escalation_email = settings.escalation_default_email
            recent_interactions = await _get_last_interactions(ticket_id, limit=3)
            await send_escalation_email(
                ticket=ticket,
                interactions=recent_interactions,
                escalation_reasons=escalation_reasons,
                company_name=company_name,
                to_email=escalation_email
            )
        elif not escalated:
            await cancel_pending_events(ticket_id)
        
        return IngestMessageResponse(
            success=True,
            ticket_id=ticket_id,
            reply_text=reply_text,
            escalated=escalated,
            message="Message processed successfully",
            ticket_status=ticket.get("status")
        )
        
    except ValueError as e:
        logger.warning(f"Ingest validation error: {e}")
        raise SecureError(
            "E009",
            message="Invalid message format. Please check your input.",
            internal_message=str(e),
        )
    except Exception as e:
        logger.error("Failed to process ingest message", exc_info=True)
        raise SecureError(
            "E001",
            message="Failed to process message. Please try again later.",
            internal_message=str(e),
            context={"channel": payload.channel.value if hasattr(payload, 'channel') else None},
        )
