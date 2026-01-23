"""
API routes for human agent responses to escalated tickets
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_AUDIT_LOGS,
)
from src.models import TicketStatus
from src.models.interaction import InteractionType
from src.middleware.auth import verify_api_key
from src.utils.sanitization import sanitize_text, sanitize_identifier


router = APIRouter(prefix="/api/human", tags=["human-agent"])

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


class HumanReplyRequest(BaseModel):
    ticket_id: str = Field(..., description="ID do ticket a responder")
    reply_text: str = Field(..., description="Texto da resposta do atendente")
    close_ticket: bool = Field(False, description="Se True, marca o ticket como resolvido")


class HumanReplyResponse(BaseModel):
    success: bool
    message: str
    ticket_id: str
    new_status: Optional[str] = None


@router.post("/reply", response_model=HumanReplyResponse)
@limiter.limit("30/minute")  # Human replies (write operation)
async def human_reply(
    http_request: Request,  # Required by slowapi
    request: HumanReplyRequest,
    api_key: dict = Depends(verify_api_key)
) -> HumanReplyResponse:
    """
    Endpoint for human agents to reply to escalated tickets.

    Requires: X-API-Key header

    This endpoint:
    1. Validates the ticket exists and is in ESCALATED status
    2. Adds the human's reply as an interaction
    3. Optionally closes the ticket if close_ticket=True

    Args:
        request: Human reply request
        api_key: Authenticated API key (auto-injected)

    Returns:
        Reply confirmation with new ticket status
    """
    tickets_col = get_collection(COLLECTION_TICKETS)
    interactions_col = get_collection(COLLECTION_INTERACTIONS)
    audit_col = get_collection(COLLECTION_AUDIT_LOGS)

    # 1. Find ticket
    ticket = await tickets_col.find_one({"ticket_id": request.ticket_id})

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {request.ticket_id} not found"
        )

    # Enforce company isolation
    if ticket.get("company_id") != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {request.ticket_id} not found"
        )

    # SANITIZE INPUTS
    try:
        ticket_id = sanitize_identifier(request.ticket_id)
        reply_text = sanitize_text(request.reply_text, max_length=4000)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid input: {str(e)}"
        )

    # 2. Validate status
    current_status = ticket.get("status")
    if current_status != TicketStatus.ESCALATED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ticket is not escalated (current status: {current_status})"
        )
    
    # 3. Add human reply as interaction
    interaction_data = {
        "ticket_id": ticket_id,
        "type": InteractionType.AGENT_RESPONSE,
        "content": reply_text,
        "source": "human",
        "created_at": datetime.utcnow()
    }
    await interactions_col.insert_one(interaction_data)
    
    # 4. Update ticket status if closing
    new_status = current_status
    if request.close_ticket:
        new_status = TicketStatus.RESOLVED
        await tickets_col.update_one(
            {"ticket_id": ticket_id},
            {"$set": {
                "status": TicketStatus.RESOLVED,
                "resolved_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }}
        )
    else:
        # Keep as escalated but update timestamp
        await tickets_col.update_one(
            {"ticket_id": ticket_id},
            {"$set": {"updated_at": datetime.utcnow()}}
        )

    # 5. Audit log
    await audit_col.insert_one({
        "ticket_id": ticket_id,
        "agent_name": "human",
        "operation": "HUMAN_REPLY",
        "before": {"status": current_status},
        "after": {
            "status": new_status,
            "reply_sent": True,
            "closed": request.close_ticket
        },
        "timestamp": datetime.utcnow()
    })

    return HumanReplyResponse(
        success=True,
        message="Reply sent successfully" + (" and ticket closed" if request.close_ticket else ""),
        ticket_id=ticket_id,
        new_status=new_status
    )


@router.get("/escalated")
@limiter.limit("200/minute")  # Read operation
async def list_escalated_tickets(
    http_request: Request,  # Required by slowapi
    api_key: dict = Depends(verify_api_key)
):
    """
    List all tickets with ESCALATED status

    Requires: X-API-Key header
    Note: Returns only escalated tickets from own company

    Args:
        api_key: Authenticated API key (auto-injected)

    Returns:
        List of escalated tickets
    """
    tickets_col = get_collection(COLLECTION_TICKETS)

    # Filter by status AND company_id for isolation
    cursor = tickets_col.find({
        "status": TicketStatus.ESCALATED,
        "company_id": api_key["company_id"]
    }).sort("created_at", -1).limit(50)
    
    tickets = []
    async for ticket in cursor:
        tickets.append({
            "ticket_id": ticket.get("ticket_id"),
            "subject": ticket.get("subject"),
            "description": ticket.get("description", "")[:100],
            "priority": ticket.get("priority"),
            "channel": ticket.get("channel"),
            "company_id": ticket.get("company_id"),
            "created_at": ticket.get("created_at"),
            "external_user_id": ticket.get("external_user_id")
        })
    
    return {"tickets": tickets, "count": len(tickets)}
