"""
Database connection and utilities
"""
from .connection import (
    get_client,
    get_database,
    get_collection,
    close_connection,
    ensure_indexes,
    COLLECTION_TICKETS,
    COLLECTION_AGENT_STATES,
    COLLECTION_INTERACTIONS,
    COLLECTION_ROUTING_DECISIONS,
    COLLECTION_AUDIT_LOGS,
)
from .transactions import with_transaction

__all__ = [
    "get_client",
    "get_database",
    "get_collection",
    "close_connection",
    "ensure_indexes",
    "with_transaction",
    "COLLECTION_TICKETS",
    "COLLECTION_AGENT_STATES",
    "COLLECTION_INTERACTIONS",
    "COLLECTION_ROUTING_DECISIONS",
    "COLLECTION_AUDIT_LOGS",
]
