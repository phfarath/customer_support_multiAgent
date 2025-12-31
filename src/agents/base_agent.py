"""
Base agent class for all agents in the system
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClientSession


class AgentResult(BaseModel):
    """Result of an agent execution"""
    success: bool
    confidence: float
    decisions: Dict[str, Any]
    message: str
    needs_escalation: bool = False
    escalation_reasons: list = []


class BaseAgent(ABC):
    """
    Abstract base class for all agents
    
    Each agent must implement the execute method which processes a ticket
    and returns an AgentResult.
    """
    
    def __init__(self, name: str):
        """
        Initialize the agent
        
        Args:
            name: Name of the agent (e.g., "triage", "router", "resolver", "escalator")
        """
        self.name = name
    
    @abstractmethod
    async def execute(
        self,
        ticket_id: str,
        context: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ) -> AgentResult:
        """
        Execute the agent's logic for a ticket
        
        Args:
            ticket_id: ID of the ticket to process
            context: Context data including ticket info, interactions, etc.
            session: Optional MongoDB session for transactions
            
        Returns:
            AgentResult with the agent's decisions and confidence
        """
        pass
    
    @abstractmethod
    def get_phase_name(self) -> str:
        """
        Get the phase name this agent operates in
        
        Returns:
            Phase name (e.g., "triage", "routing", "resolution", "escalation")
        """
        pass
    
    async def save_agent_state(
        self,
        ticket_id: str,
        state: Dict[str, Any],
        session: Optional[AsyncIOMotorClientSession] = None
    ):
        """
        Save the agent's state for a ticket
        
        Args:
            ticket_id: ID of the ticket
            state: State data to save
            session: Optional MongoDB session
        """
        from src.database import get_collection, COLLECTION_AGENT_STATES
        from datetime import datetime
        
        collection = await get_collection(COLLECTION_AGENT_STATES)
        
        agent_state = {
            "ticket_id": ticket_id,
            "agent_name": self.name,
            "phase": self.get_phase_name(),
            "state": state,
            "lock_version": 0,
            "updated_at": datetime.utcnow()
        }
        
        # Upsert the agent state
        if session:
            await collection.update_one(
                {"ticket_id": ticket_id, "agent_name": self.name},
                {"$set": agent_state, "$inc": {"lock_version": 1}},
                upsert=True,
                session=session
            )
        else:
            await collection.update_one(
                {"ticket_id": ticket_id, "agent_name": self.name},
                {"$set": agent_state, "$inc": {"lock_version": 1}},
                upsert=True
            )
