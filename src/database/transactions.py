"""
MongoDB transaction utilities for Motor (async)
"""
import logging
from typing import Callable, Any
from functools import wraps
from motor.motor_asyncio import AsyncIOMotorClientSession
from src.database.connection import get_client

logger = logging.getLogger(__name__)


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
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Starting transaction for {func.__name__}")
        client = get_client()
        session: AsyncIOMotorClientSession = await client.start_session()
        
        try:
            async with session.start_transaction():
                # Execute the function with session
                logger.info(f"Executing {func.__name__} within transaction")
                result = await func(*args, session=session, **kwargs)
                logger.info(f"{func.__name__} completed successfully")
                return result
                
        except Exception as e:
            # Transaction is automatically aborted on exception
            logger.error(f"Transaction failed for {func.__name__}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Transaction failed: {str(e)}") from e
            
        finally:
            await session.end_session()
            logger.info(f"Transaction session ended for {func.__name__}")
    
    return wrapper
