"""
Database operations for ticket management with channel-agnostic support
"""
from typing import Dict, Any, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClientSession
from src.database import get_collection, COLLECTION_TICKETS, COLLECTION_INTERACTIONS
from src.models import TicketChannel, TicketStatus, TicketPhase, TicketPriority


async def find_or_create_ticket(
    external_user_id: str,
    channel: TicketChannel,
    text: str,
    company_id: Optional[str] = None,
    session: Optional[AsyncIOMotorClientSession] = None
) -> tuple[Dict[str, Any], bool]:
    """
    Find an existing ticket or create a new one for the given external_user_id and channel
    
    Args:
        external_user_id: External user ID from the channel
        channel: Channel where the message originated
        text: Message text (used for subject/description if creating new ticket)
        company_id: Optional Company ID to associate with the ticket
        session: Optional MongoDB session for transactions
        
    Returns:
        Tuple of (ticket_dict, is_new_ticket)
    """
    collection = get_collection(COLLECTION_TICKETS)
    
    # Try to find an existing open ticket for this user and channel
    # Include ESCALATED to prevent creating new ticket when user sends follow-up
    filter_query = {
        "external_user_id": external_user_id,
        "channel": channel,
        "status": {"$in": [TicketStatus.OPEN, TicketStatus.IN_PROGRESS, TicketStatus.ESCALATED]}
    }
    
    ticket = await collection.find_one(filter_query, session=session)
    
    if ticket:
        # Update company_id if provided and not present
        if company_id and not ticket.get("company_id"):
            await collection.update_one(
                {"ticket_id": ticket["ticket_id"]},
                {"$set": {"company_id": company_id}},
                session=session
            )
            ticket["company_id"] = company_id
            
        # Return existing ticket
        return ticket, False
    
    # Create new ticket
    ticket_id = f"{channel.value}_{external_user_id}_{datetime.utcnow().timestamp()}"
    
    # Generate subject from first 50 chars of text
    subject = text[:50] + "..." if len(text) > 50 else text
    
    ticket_dict = {
        "ticket_id": ticket_id,
        "customer_id": external_user_id,  # Use external_user_id as customer_id for now
        "company_id": company_id,
        "channel": channel,
        "external_user_id": external_user_id,
        "subject": subject,
        "description": text,
        "priority": TicketPriority.P3,
        "status": TicketStatus.OPEN,
        "current_phase": TicketPhase.TRIAGE,
        "interactions_count": 0,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "lock_version": 0
    }
    
    result = await collection.insert_one(ticket_dict, session=session)
    ticket_dict["_id"] = str(result.inserted_id)
    
    return ticket_dict, True


async def add_interaction(
    ticket_id: str,
    interaction_type: str,
    content: str,
    channel: str,
    pii_detected: bool = False,
    pii_types: Optional[list] = None,
    session: Optional[AsyncIOMotorClientSession] = None
) -> Dict[str, Any]:
    """
    Add an interaction to a ticket
    
    Args:
        ticket_id: ID of the ticket
        interaction_type: Type of interaction (customer_message, agent_response, system_update)
        content: Interaction content
        channel: Channel where the interaction occurred
        pii_detected: Whether PII was detected and redacted
        pii_types: List of PII types detected (e.g., ["cpf", "email"])
        session: Optional MongoDB session for transactions
        
    Returns:
        Created interaction document
    """
    collection = get_collection(COLLECTION_INTERACTIONS)
    
    interaction_dict = {
        "ticket_id": ticket_id,
        "type": interaction_type,
        "content": content,
        "channel": channel,
        "sentiment_score": 0.0,
        "pii_detected": pii_detected,
        "pii_types": pii_types or [],
        "created_at": datetime.utcnow()
    }
    
    result = await collection.insert_one(interaction_dict, session=session)
    interaction_dict["_id"] = str(result.inserted_id)
    
    return interaction_dict


async def update_ticket_interactions_count(
    ticket_id: str,
    session: Optional[AsyncIOMotorClientSession] = None
) -> None:
    """
    Increment the interactions count for a ticket
    
    Args:
        ticket_id: ID of the ticket
        session: Optional MongoDB session for transactions
    """
    collection = get_collection(COLLECTION_TICKETS)
    
    await collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$inc": {"interactions_count": 1},
            "$set": {"updated_at": datetime.utcnow()}
        },
        session=session
    )


async def update_ticket_status(
    ticket_id: str,
    status: TicketStatus,
    session: Optional[AsyncIOMotorClientSession] = None
) -> None:
    """
    Update the status of a ticket
    
    Args:
        ticket_id: ID of the ticket
        status: New status
        session: Optional MongoDB session for transactions
    """
    collection = get_collection(COLLECTION_TICKETS)
    
    await collection.update_one(
        {"ticket_id": ticket_id},
        {
            "$set": {
                "status": status,
                "updated_at": datetime.utcnow()
            }
        },
        session=session
    )
