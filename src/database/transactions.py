"""
MongoDB transaction utilities for Motor (async)
"""
from typing import Callable, Any
from functools import wraps
from motor.motor_asyncio import AsyncIOMotorClientSession
from src.database.connection import get_client


def with_transaction(func: Callable) -> Callable:
    """
    Decorator to execute an async function within a MongoDB transaction
    
    Args:
        func: Async function to execute within transaction
        
    Returns:
        Wrapped async function that runs within a transaction
    """
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        client = get_client()
        session: AsyncIOMotorClientSession = client.start_session()
        
        try:
            async with session.start_transaction():
                # Execute the function with session
                result = await func(*args, session=session, **kwargs)
                return result
                
        except Exception as e:
            # Transaction is automatically aborted on exception
            raise RuntimeError(f"Transaction failed: {str(e)}") from e
            
        finally:
            await session.end_session()
    
    return wrapper
