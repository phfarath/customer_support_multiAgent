"""
Synchronous MongoDB connection for Streamlit Dashboard
Uses pymongo instead of motor for easier integration with Streamlit's sync nature.
"""
import streamlit as st
import pymongo
from pymongo.database import Database
from pymongo.collection import Collection
from src.config import settings

# Re-export collection names for convenience
from src.database import (
    COLLECTION_TICKETS,
    COLLECTION_INTERACTIONS,
    COLLECTION_CUSTOMERS,
    COLLECTION_BOT_SESSIONS,
    COLLECTION_COMPANY_CONFIGS,
    COLLECTION_AUDIT_LOGS,
    COLLECTION_AGENT_STATES,
    COLLECTION_ROUTING_DECISIONS
)

@st.cache_resource
def get_mongo_client() -> pymongo.MongoClient:
    """
    Get or create a cached MongoDB client.
    Using cache_resource ensures the connection persists across reruns.
    """
    return pymongo.MongoClient(settings.mongodb_uri)

def get_db() -> Database:
    """Get the database instance"""
    client = get_mongo_client()
    return client[settings.database_name]

def get_collection(collection_name: str) -> Collection:
    """Get a specific collection"""
    db = get_db()
    return db[collection_name]
