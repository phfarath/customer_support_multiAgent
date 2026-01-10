"""
Script to reset the database (drop all collections)
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.database import (
    get_database,
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_CUSTOMERS,
    COLLECTION_AGENT_STATES,
    COLLECTION_ROUTING_DECISIONS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_COMPANY_CONFIGS,
    COLLECTION_BOT_SESSIONS
)

async def reset_database():
    print("🗑️  Clearing database...")
    db = get_database()
    
    collections = [
        COLLECTION_TICKETS,
        COLLECTION_INTERACTIONS,
        COLLECTION_CUSTOMERS,
        COLLECTION_AGENT_STATES,
        COLLECTION_ROUTING_DECISIONS,
        COLLECTION_AUDIT_LOGS,
        COLLECTION_COMPANY_CONFIGS,
        COLLECTION_BOT_SESSIONS
    ]
    
    for col_name in collections:
        await db[col_name].drop()
        print(f"   - Dropped {col_name}")
        
    print("✨ Database cleared.")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(reset_database())
