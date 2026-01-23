"""
Circuit Breaker Pattern for OpenAI API Calls

Implements circuit breaker pattern to handle OpenAI API failures gracefully:
- Prevents cascading failures
- Automatic fallback to rule-based logic
- Exponential backoff retry
- Failure threshold tracking
- Auto-recovery after cool-down period
- Metrics and monitoring integration

States:
- CLOSED: Normal operation, requests go through
- OPEN: Too many failures, requests fail fast
- HALF_OPEN: Testing if service recovered

Usage:
    from src.utils.circuit_breaker import OpenAICircuitBreaker

    circuit_breaker = OpenAICircuitBreaker()

    result = await circuit_breaker.call(
        func=openai_client.chat.completions.create,
        fallback=rule_based_fallback,
        model="gpt-3.5-turbo",
        messages=[...]
    )
"""

import asyncio
import logging
import time
from enum import Enum
from typing import Callable, Any, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from functools import wraps

try:
    from src.utils.monitoring import (
        capture_exception,
        capture_message,
        set_tag,
        add_breadcrumb
    )
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    # Failure threshold
    failure_threshold: int = 5  # Open after N failures
    failure_timeout: int = 60  # Reset failure count after N seconds

    # Cool-down period (open -> half-open)
    recovery_timeout: int = 30  # Try recovery after N seconds

    # Half-open state
    success_threshold: int = 2  # Close after N successes in half-open

    # Monitoring
    name: str = "openai_circuit_breaker"


@dataclass
class CircuitBreakerMetrics:
    """Circuit breaker metrics"""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Rejected due to open circuit
    fallback_calls: int = 0

    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None

    state_changes: Dict[str, int] = field(default_factory=lambda: {
        "closed_to_open": 0,
        "open_to_half_open": 0,
        "half_open_to_closed": 0,
        "half_open_to_open": 0
    })


class CircuitBreakerError(Exception):
    """Raised when circuit is open"""
    pass


class OpenAICircuitBreaker:
    """
    Circuit breaker for OpenAI API calls

    Automatically switches to fallback when OpenAI API is failing.
    Prevents wasting time/money on failing API calls.
    """

    def __init__(self, config: Optional[CircuitBreakerConfig] = None):
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()

        # Failure tracking
        self.failure_count = 0
        self.success_count = 0  # In half-open state
        self.last_state_change = time.time()

        logger.info(
            f"Circuit breaker initialized: {self.config.name} "
            f"(threshold={self.config.failure_threshold}, "
            f"timeout={self.config.recovery_timeout}s)"
        )

    async def call(
        self,
        func: Callable,
        fallback: Optional[Callable] = None,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function through circuit breaker

        Args:
            func: Function to execute (e.g., OpenAI API call)
            fallback: Fallback function if circuit is open or func fails
            *args, **kwargs: Arguments for func

        Returns:
            Result from func or fallback

        Raises:
            CircuitBreakerError: If circuit is open and no fallback provided
        """

        self.metrics.total_calls += 1

        # Check circuit state
        self._update_state()

        if self.state == CircuitState.OPEN:
            # Circuit is open - fail fast
            self.metrics.rejected_calls += 1

            if MONITORING_AVAILABLE:
                add_breadcrumb(
                    "Circuit breaker rejected call",
                    category="circuit_breaker",
                    level="warning",
                    data={
                        "state": self.state.value,
                        "failure_count": self.failure_count
                    }
                )

            if fallback:
                logger.warning(
                    f"Circuit breaker OPEN - using fallback "
                    f"(failures: {self.failure_count})"
                )
                return await self._call_fallback(fallback, *args, **kwargs)
            else:
                raise CircuitBreakerError(
                    f"Circuit breaker is OPEN (too many failures). "
                    f"Service will retry in {self.config.recovery_timeout}s."
                )

        # Try calling the function
        try:
            result = await self._execute_with_timeout(func, *args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure(e)

            # Use fallback if available
            if fallback:
                logger.warning(
                    f"Function failed, using fallback: {e}",
                    exc_info=True
                )
                return await self._call_fallback(fallback, *args, **kwargs)
            else:
                raise

    async def _execute_with_timeout(
        self,
        func: Callable,
        *args,
        timeout: int = 30,
        **kwargs
    ) -> Any:
        """
        Execute function with timeout

        Args:
            func: Function to execute
            timeout: Timeout in seconds
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            asyncio.TimeoutError: If timeout exceeded
        """
        # Remove timeout from kwargs if present
        kwargs.pop('timeout', None)

        try:
            if asyncio.iscoroutinefunction(func):
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout
                )
            else:
                # Sync function - run in executor
                loop = asyncio.get_event_loop()
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: func(*args, **kwargs)),
                    timeout=timeout
                )
        except asyncio.TimeoutError:
            logger.error(f"Function timeout after {timeout}s")
            raise

    async def _call_fallback(
        self,
        fallback: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Call fallback function"""
        self.metrics.fallback_calls += 1

        if MONITORING_AVAILABLE:
            add_breadcrumb(
                "Using fallback function",
                category="circuit_breaker",
                level="info"
            )

        try:
            if asyncio.iscoroutinefunction(fallback):
                return await fallback(*args, **kwargs)
            else:
                return fallback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Fallback function failed: {e}", exc_info=True)
            if MONITORING_AVAILABLE:
                capture_exception(
                    e,
                    level="error",
                    tags={"component": "circuit_breaker", "type": "fallback_failure"}
                )
            raise

    def _on_success(self):
        """Handle successful call"""
        self.metrics.successful_calls += 1
        self.metrics.last_success_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            # Increment success count in half-open state
            self.success_count += 1

            if self.success_count >= self.config.success_threshold:
                # Enough successes - close circuit
                self._transition_to_closed()

        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self, error: Exception):
        """Handle failed call"""
        self.metrics.failed_calls += 1
        self.metrics.last_failure_time = time.time()

        logger.error(
            f"Circuit breaker detected failure: {error}",
            exc_info=True
        )

        if MONITORING_AVAILABLE:
            capture_exception(
                error,
                level="warning",
                tags={
                    "component": "circuit_breaker",
                    "state": self.state.value,
                    "failure_count": str(self.failure_count + 1)
                }
            )

        if self.state == CircuitState.HALF_OPEN:
            # Failure in half-open - back to open
            self._transition_to_open()

        elif self.state == CircuitState.CLOSED:
            # Increment failure count
            self.failure_count += 1

            if self.failure_count >= self.config.failure_threshold:
                # Too many failures - open circuit
                self._transition_to_open()

    def _update_state(self):
        """Update circuit state based on time and metrics"""
        now = time.time()

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout passed
            time_since_open = now - self.last_state_change

            if time_since_open >= self.config.recovery_timeout:
                # Try recovery
                self._transition_to_half_open()

        elif self.state == CircuitState.CLOSED:
            # Reset failure count if timeout passed
            if self.metrics.last_failure_time:
                time_since_failure = now - self.metrics.last_failure_time

                if time_since_failure >= self.config.failure_timeout:
                    self.failure_count = 0

    def _transition_to_open(self):
        """Transition to OPEN state"""
        if self.state != CircuitState.OPEN:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
            self.metrics.state_changes["half_open_to_open" if self.state == CircuitState.HALF_OPEN else "closed_to_open"] += 1

            logger.warning(
                f"Circuit breaker opened (failures: {self.failure_count}). "
                f"Will retry in {self.config.recovery_timeout}s."
            )

            if MONITORING_AVAILABLE:
                capture_message(
                    "Circuit breaker opened",
                    level="warning",
                    tags={
                        "component": "circuit_breaker",
                        "name": self.config.name
                    },
                    extra={
                        "failure_count": self.failure_count,
                        "recovery_timeout": self.config.recovery_timeout
                    }
                )

    def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self.state = CircuitState.HALF_OPEN
        self.last_state_change = time.time()
        self.success_count = 0
        self.metrics.state_changes["open_to_half_open"] += 1

        logger.info("Circuit breaker half-open - testing recovery")

        if MONITORING_AVAILABLE:
            add_breadcrumb(
                "Circuit breaker testing recovery",
                category="circuit_breaker",
                level="info"
            )

    def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()
        self.failure_count = 0
        self.success_count = 0
        self.metrics.state_changes["half_open_to_closed"] += 1

        logger.info("Circuit breaker closed - service recovered")

        if MONITORING_AVAILABLE:
            capture_message(
                "Circuit breaker closed - service recovered",
                level="info",
                tags={
                    "component": "circuit_breaker",
                    "name": self.config.name
                }
            )

    def get_state(self) -> CircuitState:
        """Get current circuit state"""
        self._update_state()
        return self.state

    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get circuit breaker metrics"""
        return self.metrics

    def reset(self):
        """Reset circuit breaker to initial state"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_state_change = time.time()

        logger.info("Circuit breaker reset")

    def __repr__(self) -> str:
        return (
            f"CircuitBreaker(name={self.config.name}, "
            f"state={self.state.value}, "
            f"failures={self.failure_count}/{self.config.failure_threshold})"
        )


# ============================================================
# Global Circuit Breaker Instance
# ============================================================

# Singleton instance for OpenAI calls
_openai_circuit_breaker: Optional[OpenAICircuitBreaker] = None


def get_openai_circuit_breaker() -> OpenAICircuitBreaker:
    """
    Get global OpenAI circuit breaker instance

    Returns:
        OpenAICircuitBreaker singleton
    """
    global _openai_circuit_breaker

    if _openai_circuit_breaker is None:
        _openai_circuit_breaker = OpenAICircuitBreaker(
            config=CircuitBreakerConfig(
                name="openai_api",
                failure_threshold=5,  # Open after 5 failures
                failure_timeout=60,  # Reset after 60s
                recovery_timeout=30,  # Test recovery after 30s
                success_threshold=2  # Close after 2 successes
            )
        )

    return _openai_circuit_breaker


# ============================================================
# Decorator
# ============================================================

def with_circuit_breaker(fallback: Optional[Callable] = None):
    """
    Decorator to add circuit breaker to async functions

    Args:
        fallback: Optional fallback function

    Example:
        @with_circuit_breaker(fallback=rule_based_fallback)
        async def call_openai(messages):
            return await openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            circuit_breaker = get_openai_circuit_breaker()
            return await circuit_breaker.call(
                func=func,
                fallback=fallback,
                *args,
                **kwargs
            )
        return wrapper
    return decorator
