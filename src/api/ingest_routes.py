"""
FastAPI routes for channel-agnostic message ingestion
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any
from datetime import datetime

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
)
from src.database.ticket_operations import (
    find_or_create_ticket,
    add_interaction,
    update_ticket_interactions_count,
    update_ticket_status,
)
from src.utils import AgentPipeline
from src.models.interaction import InteractionType


router = APIRouter(prefix="/api", tags=["ingest"])


@router.post("/ingest-message", response_model=IngestMessageResponse)
async def ingest_message(request: IngestMessageRequest) -> IngestMessageResponse:
    """
    Channel-agnostic endpoint for ingesting messages from any channel
    
    This endpoint handles incoming messages from Telegram, WhatsApp, or any other channel.
    It will:
    1. Find or create a ticket for the user on the specified channel
    2. Add the message as a customer interaction
    3. Run the agent pipeline to generate a response
    4. Return the response text and escalation status
    
    Args:
        request: Message ingestion request with channel, external_user_id, and text
        
    Returns:
        Response with reply_text, escalation status, and ticket information
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Received ingest message request: {request}")
    
    pipeline = AgentPipeline()
    
    try:
        # Convert IngestChannel to TicketChannel
        logger.info(f"Converting channel: {request.channel} to TicketChannel")
        ticket_channel = TicketChannel(request.channel.value)
        logger.info(f"TicketChannel: {ticket_channel}")
        
        # Find or create ticket
        logger.info("Finding or creating ticket...")
        ticket, is_new_ticket = await find_or_create_ticket(
            external_user_id=request.external_user_id,
            channel=ticket_channel,
            text=request.text,
            company_id=request.company_id
        )
        logger.info(f"Ticket found/created: ticket_id={ticket.get('ticket_id')}, is_new={is_new_ticket}")
        
        ticket_id = ticket["ticket_id"]
        
        # Add customer interaction
        await add_interaction(
            ticket_id=ticket_id,
            interaction_type=InteractionType.CUSTOMER_MESSAGE,
            content=request.text,
            channel=request.channel.value
        )
        
        # Update ticket interactions count
        await update_ticket_interactions_count(ticket_id)
        
        # Create audit log for message ingestion
        audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
        await audit_collection.insert_one({
            "ticket_id": ticket_id,
            "agent_name": "system",
            "operation": "INGEST_MESSAGE",
            "before": {},
            "after": {
                "channel": request.channel.value,
                "external_user_id": request.external_user_id,
                "text": request.text,
                "is_new_ticket": is_new_ticket
            },
            "timestamp": datetime.utcnow()
        })
        
        # Run agent pipeline
        logger.info(f"Running agent pipeline for ticket_id: {ticket_id}")
        results = await pipeline.run_pipeline(ticket_id)
        logger.info(f"Pipeline results: {results}")
        
        # Extract the resolver's response
        resolver_response = results.get("resolution", {}).get("decisions", {})
        reply_text = resolver_response.get("response", "Thank you for your message. We're processing your request.")
        
        # Check if escalated
        escalated = results.get("escalation", {}).get("escalate_to_human", False)
        
        # Update ticket status based on escalation
        if escalated:
            await update_ticket_status(ticket_id, TicketStatus.ESCALATED)
        else:
            await update_ticket_status(ticket_id, TicketStatus.IN_PROGRESS)
        
        # Add agent response as interaction
        await add_interaction(
            ticket_id=ticket_id,
            interaction_type=InteractionType.AGENT_RESPONSE,
            content=reply_text,
            channel=request.channel.value
        )
        
        # Update ticket interactions count again
        await update_ticket_interactions_count(ticket_id)
        
        return IngestMessageResponse(
            success=True,
            ticket_id=ticket_id,
            reply_text=reply_text,
            escalated=escalated,
            message="Message processed successfully",
            ticket_status=ticket.get("status")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid request: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )
