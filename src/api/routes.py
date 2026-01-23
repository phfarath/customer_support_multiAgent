"""
FastAPI routes for the customer support system
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any
from datetime import datetime

from src.models import (
    TicketCreate,
    Ticket,
    TicketStatus,
    TicketPriority,
    TicketChannel,
)
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_AGENT_STATES,
    COLLECTION_INTERACTIONS,
    COLLECTION_ROUTING_DECISIONS,
)
from src.utils import AgentPipeline
from src.config import settings
from src.middleware.auth import verify_api_key


router = APIRouter(prefix="/api", tags=["tickets"])


@router.post("/tickets", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_ticket(
    ticket_data: TicketCreate,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Create a new ticket

    Requires: X-API-Key header

    Args:
        ticket_data: Ticket data to create
        api_key: Authenticated API key (auto-injected)

    Returns:
        Created ticket data
    """
    # Enforce company isolation
    if ticket_data.company_id and ticket_data.company_id != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create ticket for different company"
        )

    # Set company_id from API key if not provided
    if not ticket_data.company_id:
        ticket_data.company_id = api_key["company_id"]

    collection = get_collection(COLLECTION_TICKETS)

    # Check if ticket_id already exists
    existing = await collection.find_one({"ticket_id": ticket_data.ticket_id})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ticket with ID {ticket_data.ticket_id} already exists"
        )
    
    # Create ticket document
    ticket_dict = ticket_data.model_dump()
    ticket_dict["created_at"] = datetime.utcnow()
    ticket_dict["updated_at"] = datetime.utcnow()
    ticket_dict["lock_version"] = 0
    
    # Insert ticket
    result = await collection.insert_one(ticket_dict)
    ticket_dict["_id"] = str(result.inserted_id)
    
    # Create audit log
    audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
    await audit_collection.insert_one({
        "ticket_id": ticket_data.ticket_id,
        "agent_name": "system",
        "operation": "CREATE_TICKET",
        "before": {},
        "after": ticket_dict,
        "timestamp": datetime.utcnow()
    })
    
    return {
        "success": True,
        "ticket_id": ticket_data.ticket_id,
        "message": "Ticket created successfully",
        "ticket": ticket_dict
    }


@router.post("/run_pipeline/{ticket_id}", response_model=Dict[str, Any])
async def run_pipeline(
    ticket_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Run the complete agent pipeline for a ticket

    Requires: X-API-Key header

    Args:
        ticket_id: ID of the ticket to process
        api_key: Authenticated API key (auto-injected)

    Returns:
        Pipeline execution results
    """
    # Verify ticket belongs to company
    collection = get_collection(COLLECTION_TICKETS)
    ticket = await collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    if ticket.get("company_id") != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    pipeline = AgentPipeline()

    try:
        results = await pipeline.run_pipeline(ticket_id)
        return {
            "success": True,
            "ticket_id": ticket_id,
            "results": results
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}"
        )


@router.get("/tickets/{ticket_id}", response_model=Dict[str, Any])
async def get_ticket(
    ticket_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get ticket details by ID

    Requires: X-API-Key header

    Args:
        ticket_id: ID of the ticket
        api_key: Authenticated API key (auto-injected)

    Returns:
        Ticket data
    """
    collection = get_collection(COLLECTION_TICKETS)
    ticket = await collection.find_one({"ticket_id": ticket_id})

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    # Enforce company isolation
    if ticket.get("company_id") != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    ticket["_id"] = str(ticket["_id"])
    
    return {
        "success": True,
        "ticket": ticket
    }


@router.get("/tickets/{ticket_id}/audit", response_model=Dict[str, Any])
async def get_ticket_audit(
    ticket_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get complete audit trail for a ticket

    Requires: X-API-Key header

    Args:
        ticket_id: ID of the ticket
        api_key: Authenticated API key (auto-injected)

    Returns:
        Audit log entries
    """
    # Verify ticket belongs to company
    tickets_collection = get_collection(COLLECTION_TICKETS)
    ticket = await tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket or ticket.get("company_id") != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    audit_collection = get_collection(COLLECTION_AUDIT_LOGS)
    
    cursor = audit_collection.find({"ticket_id": ticket_id}).sort("timestamp", 1)
    
    audit_logs = []
    async for log in cursor:
        log["_id"] = str(log["_id"])
        audit_logs.append(log)
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "audit_logs": audit_logs,
        "count": len(audit_logs)
    }


@router.get("/tickets/{ticket_id}/interactions", response_model=Dict[str, Any])
async def get_ticket_interactions(
    ticket_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get all interactions for a ticket

    Requires: X-API-Key header

    Args:
        ticket_id: ID of the ticket
        api_key: Authenticated API key (auto-injected)

    Returns:
        List of interactions
    """
    # Verify ticket belongs to company
    tickets_collection = get_collection(COLLECTION_TICKETS)
    ticket = await tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket or ticket.get("company_id") != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    interactions_collection = get_collection(COLLECTION_INTERACTIONS)
    
    cursor = interactions_collection.find({"ticket_id": ticket_id}).sort("created_at", 1)
    
    interactions = []
    async for interaction in cursor:
        interaction["_id"] = str(interaction["_id"])
        interactions.append(interaction)
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "interactions": interactions,
        "count": len(interactions)
    }


@router.get("/tickets/{ticket_id}/agent_states", response_model=Dict[str, Any])
async def get_ticket_agent_states(
    ticket_id: str,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get agent states for a ticket

    Requires: X-API-Key header

    Args:
        ticket_id: ID of the ticket
        api_key: Authenticated API key (auto-injected)

    Returns:
        List of agent states
    """
    # Verify ticket belongs to company
    tickets_collection = get_collection(COLLECTION_TICKETS)
    ticket = await tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket or ticket.get("company_id") != api_key["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket {ticket_id} not found"
        )

    agent_states_collection = get_collection(COLLECTION_AGENT_STATES)
    
    cursor = agent_states_collection.find({"ticket_id": ticket_id})
    
    agent_states = []
    async for state in cursor:
        state["_id"] = str(state["_id"])
        agent_states.append(state)
    
    return {
        "success": True,
        "ticket_id": ticket_id,
        "agent_states": agent_states,
        "count": len(agent_states)
    }


@router.get("/tickets", response_model=Dict[str, Any])
async def list_tickets(
    status: TicketStatus = None,
    priority: TicketPriority = None,
    limit: int = 50,
    api_key: dict = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    List tickets with optional filters

    Requires: X-API-Key header

    Args:
        status: Filter by status
        priority: Filter by priority
        limit: Maximum number of tickets to return
        api_key: Authenticated API key (auto-injected)

    Returns:
        List of tickets
    """
    collection = get_collection(COLLECTION_TICKETS)

    # Build filter with company isolation
    filter_dict = {"company_id": api_key["company_id"]}
    if status:
        filter_dict["status"] = status
    if priority:
        filter_dict["priority"] = priority
    
    cursor = collection.find(filter_dict).sort("created_at", -1).limit(limit)
    
    tickets = []
    async for ticket in cursor:
        ticket["_id"] = str(ticket["_id"])
        tickets.append(ticket)
    
    return {
        "success": True,
        "tickets": tickets,
        "count": len(tickets)
    }


@router.get("/health", response_model=Dict[str, Any])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint
    
    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "service": "MultiAgent Customer Support",
        "version": "0.1.0"
    }
