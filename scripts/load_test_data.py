"""
Script to load test data into MongoDB
"""
import asyncio
import json
from datetime import datetime
from pathlib import Path
from src.database import (
    get_collection,
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
)
from src.models import (
    TicketCreate,
    TicketChannel,
    TicketStatus,
    TicketPriority,
    TicketPhase,
    InteractionCreate,
    InteractionType,
)


async def load_tickets():
    """Load test tickets from JSON file"""
    
    # Read tickets from JSON
    tickets_file = Path("test_data/tickets.json")
    with open(tickets_file, "r", encoding="utf-8") as f:
        tickets_data = json.load(f)
    
    tickets_collection = await get_collection(COLLECTION_TICKETS)
    interactions_collection = await get_collection(COLLECTION_INTERACTIONS)
    
    for ticket_data in tickets_data:
        ticket_id = ticket_data["ticket_id"]
        
        # Check if ticket already exists
        existing = await tickets_collection.find_one({"ticket_id": ticket_id})
        if existing:
            print(f"Ticket {ticket_id} already exists, skipping...")
            continue
        
        # Create ticket document
        ticket_dict = {
            "ticket_id": ticket_id,
            "customer_id": ticket_data["customer_id"],
            "channel": ticket_data["channel"],
            "subject": ticket_data["subject"],
            "description": ticket_data["description"],
            "priority": ticket_data["priority"],
            "status": ticket_data["status"],
            "current_phase": ticket_data["current_phase"],
            "interactions_count": ticket_data["interactions_count"],
            "created_at": datetime.fromisoformat(ticket_data["created_at"]) if ticket_data.get("created_at") else datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "lock_version": 0
        }
        
        # Insert ticket
        await tickets_collection.insert_one(ticket_dict)
        print(f"Created ticket: {ticket_id}")
        
        # Create initial customer message interaction
        interaction = {
            "ticket_id": ticket_id,
            "type": InteractionType.CUSTOMER_MESSAGE,
            "content": ticket_data["description"],
            "sentiment_score": 0.0,
            "created_at": ticket_dict["created_at"]
        }
        
        await interactions_collection.insert_one(interaction)
        print(f"Created initial interaction for: {ticket_id}")
    
    print("\nAll test tickets loaded successfully!")


if __name__ == "__main__":
    asyncio.run(load_tickets())
