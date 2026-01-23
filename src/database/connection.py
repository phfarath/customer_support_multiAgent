"""
MongoDB connection management using Motor (async)
Criamos o motor como assincrono para que possamos os agentes possam registrar sem bloquear a thread principal
"""
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from typing import Optional
from src.config import settings


# Global async client instance
_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    """
    Get or create async MongoDB client instance
    
    Returns:
        AsyncIOMotorClient: Async MongoDB client
    """
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(settings.mongodb_uri)
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """
    Get the customer support database
    
    Returns:
        AsyncIOMotorDatabase: Async MongoDB database instance
    """
    client = get_client()
    return client[settings.database_name]


def get_collection(collection_name: str) -> AsyncIOMotorCollection:
    """
    Get a specific collection from the database
    
    Args:
        collection_name: Name of the collection
        
    Returns:
        AsyncIOMotorCollection: Async MongoDB collection instance
    """
    db = get_database()
    return db[collection_name]


async def close_connection():
    """Close the async MongoDB connection"""
    global _client
    if _client is not None:
        _client.close()
        _client = None


# Collection names
COLLECTION_TICKETS = "tickets"
COLLECTION_AGENT_STATES = "agent_states"
COLLECTION_INTERACTIONS = "interactions"
COLLECTION_ROUTING_DECISIONS = "routing_decisions"
COLLECTION_AUDIT_LOGS = "audit_logs"
COLLECTION_COMPANY_CONFIGS = "company_configs"
COLLECTION_CUSTOMERS = "customers"
COLLECTION_BOT_SESSIONS = "bot_sessions"
COLLECTION_API_KEYS = "api_keys"
COLLECTION_USERS = "users"


async def ensure_indexes():
    """
    Create all required indexes for the database
    """
    db = get_database()
    
    # Tickets indexes
    await db[COLLECTION_TICKETS].create_index([("ticket_id", 1)], unique=True)
    await db[COLLECTION_TICKETS].create_index([("current_phase", 1), ("status", 1)])
    
    # Agent states indexes - drop incorrect index if exists and create correct composite index
    try:
        await db[COLLECTION_AGENT_STATES].drop_index("agent_name_1")
    except:
        pass  # Index doesn't exist, ignore
    await db[COLLECTION_AGENT_STATES].create_index([("ticket_id", 1), ("agent_name", 1)], unique=True)
    
    # Audit logs indexes
    await db[COLLECTION_AUDIT_LOGS].create_index([("ticket_id", 1), ("timestamp", -1)])
    
    # Interactions indexes
    await db[COLLECTION_INTERACTIONS].create_index([("ticket_id", 1), ("created_at", -1)])
    
    # Routing decisions indexes
    await db[COLLECTION_ROUTING_DECISIONS].create_index([("ticket_id", 1)])
    
    # Customers indexes
    await db[COLLECTION_CUSTOMERS].create_index([("customer_id", 1)], unique=True)
    await db[COLLECTION_CUSTOMERS].create_index([("phone_number", 1)], unique=True, sparse=True)
    await db[COLLECTION_CUSTOMERS].create_index([("telegram_chat_id", 1)], sparse=True)
    await db[COLLECTION_CUSTOMERS].create_index([("company_id", 1)])
    
    # Bot sessions indexes
    await db[COLLECTION_BOT_SESSIONS].create_index([("chat_id", 1)], unique=True)
    await db[COLLECTION_BOT_SESSIONS].create_index([("phone_number", 1)], sparse=True)
    await db[COLLECTION_BOT_SESSIONS].create_index([("customer_id", 1)], sparse=True)
    await db[COLLECTION_BOT_SESSIONS].create_index([("state", 1)])
    
    # Company configs indexes
    await db[COLLECTION_COMPANY_CONFIGS].create_index([("company_id", 1)], unique=True)

    # API Keys indexes
    await db[COLLECTION_API_KEYS].create_index([("api_key", 1)], unique=True)
    await db[COLLECTION_API_KEYS].create_index([("company_id", 1)])
    await db[COLLECTION_API_KEYS].create_index([("active", 1)])

    # Users indexes
    await db[COLLECTION_USERS].create_index([("email", 1)], unique=True)
    await db[COLLECTION_USERS].create_index([("company_id", 1)])
