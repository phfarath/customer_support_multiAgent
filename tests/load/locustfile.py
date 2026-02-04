"""
Load Testing for Customer Support MultiAgent API

This module provides load testing scenarios using Locust.

Usage:
    # Basic load test (50 users, 60 seconds)
    locust -f tests/load/locustfile.py --headless -u 50 -r 5 -t 60s --host http://localhost:8000

    # Stress test (100 users, 5 minutes)
    locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 5m --host http://localhost:8000

    # With HTML report
    locust -f tests/load/locustfile.py --headless -u 50 -r 5 -t 60s --html report.html

    # Interactive mode (web UI)
    locust -f tests/load/locustfile.py --host http://localhost:8000

Environment Variables:
    TEST_API_KEY: API key for authenticated endpoints (default: sk_test_loadtest123)
    LOAD_TEST_HOST: Target host (default: http://localhost:8000)
"""

import json
import os
import random
import string
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# Configuration
API_KEY = os.getenv("TEST_API_KEY", "sk_test_loadtest123")
DEFAULT_HEADERS = {"X-API-Key": API_KEY, "Content-Type": "application/json"}


def generate_random_string(length: int = 10) -> str:
    """Generate a random string for test data."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


class CustomerSupportUser(HttpUser):
    """
    Simulates a typical API user interacting with the customer support system.

    This user performs a mix of operations with realistic weights:
    - Health checks (most common, for monitoring)
    - List tickets (common read operation)
    - Create tickets (moderate write operation)
    - Run pipeline (rare, expensive operation)
    """

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Setup: Initialize headers and test data."""
        self.headers = DEFAULT_HEADERS.copy()
        self.created_tickets = []

    @task(10)
    def health_check(self):
        """
        Test health endpoint.
        Weight: 10 (most common operation)
        """
        with self.client.get("/api/health", catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    response.success()
                else:
                    response.failure(f"Unhealthy status: {data}")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(5)
    def list_tickets(self):
        """
        Test list tickets endpoint with various filters.
        Weight: 5 (common read operation)
        """
        # Randomize query parameters
        params = {"limit": random.choice([10, 20, 50])}

        if random.random() > 0.5:
            params["status"] = random.choice(["open", "in_progress", "escalated"])

        with self.client.get(
            "/api/tickets",
            params=params,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status: {response.status_code}")

    @task(3)
    def create_ticket(self):
        """
        Test ticket creation (ingestion endpoint).
        Weight: 3 (moderate write operation)
        """
        payload = {
            "external_user_id": f"loadtest_user_{generate_random_string(8)}",
            "channel": random.choice(["api", "telegram", "web"]),
            "subject": f"Load test ticket - {generate_random_string(6)}",
            "description": f"This is a load test ticket created at {generate_random_string(10)}. "
                          f"Testing system performance under load.",
            "metadata": {
                "source": "locust_load_test",
                "test_id": generate_random_string(12)
            }
        }

        with self.client.post(
            "/api/ingest",
            json=payload,
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                data = response.json()
                ticket_id = data.get("ticket_id")
                if ticket_id:
                    self.created_tickets.append(ticket_id)
                    # Keep only last 10 tickets to avoid memory issues
                    if len(self.created_tickets) > 10:
                        self.created_tickets.pop(0)
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status: {response.status_code}")

    @task(1)
    def run_pipeline(self):
        """
        Test full pipeline execution on a created ticket.
        Weight: 1 (rare, expensive operation)
        """
        if not self.created_tickets:
            # Create a ticket first
            self.create_ticket()
            return

        ticket_id = random.choice(self.created_tickets)

        with self.client.post(
            f"/api/pipeline/{ticket_id}",
            headers=self.headers,
            catch_response=True,
            timeout=30  # Pipeline can take longer
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # Ticket might have been cleaned up
                if ticket_id in self.created_tickets:
                    self.created_tickets.remove(ticket_id)
                response.success()  # Not a failure, just stale data
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status: {response.status_code}")

    @task(2)
    def get_ticket_details(self):
        """
        Test getting ticket details.
        Weight: 2 (occasional read operation)
        """
        if not self.created_tickets:
            return

        ticket_id = random.choice(self.created_tickets)

        with self.client.get(
            f"/api/tickets/{ticket_id}",
            headers=self.headers,
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            elif response.status_code == 429:
                response.failure("Rate limited")
            else:
                response.failure(f"Status: {response.status_code}")


class StressTestUser(HttpUser):
    """
    High-frequency user for stress testing and rate limit validation.

    This user makes rapid requests to test:
    - Rate limiting effectiveness
    - System behavior under high load
    - Circuit breaker activation
    """

    wait_time = between(0.1, 0.5)  # Very short wait for stress testing

    def on_start(self):
        """Setup headers."""
        self.headers = DEFAULT_HEADERS.copy()

    @task(5)
    def rapid_health_check(self):
        """Rapid health checks to test basic throughput."""
        self.client.get("/api/health")

    @task(3)
    def rapid_list_tickets(self):
        """Rapid list calls to test rate limiting."""
        self.client.get(
            "/api/tickets?limit=5",
            headers=self.headers
        )

    @task(1)
    def rapid_create_ticket(self):
        """Rapid ticket creation to test write rate limiting."""
        payload = {
            "external_user_id": f"stress_test_{generate_random_string(6)}",
            "channel": "api",
            "subject": "Stress test",
            "description": "Stress testing the system",
            "metadata": {"source": "stress_test"}
        }
        self.client.post(
            "/api/ingest",
            json=payload,
            headers=self.headers
        )


class ReadOnlyUser(HttpUser):
    """
    Read-only user for testing read performance.

    Useful for testing cache effectiveness and read throughput.
    """

    wait_time = between(0.5, 1.5)

    def on_start(self):
        """Setup headers."""
        self.headers = DEFAULT_HEADERS.copy()

    @task(10)
    def health_check(self):
        """Health check."""
        self.client.get("/api/health")

    @task(5)
    def list_tickets(self):
        """List tickets with various limits."""
        limit = random.choice([10, 25, 50, 100])
        self.client.get(
            f"/api/tickets?limit={limit}",
            headers=self.headers
        )

    @task(2)
    def list_with_filters(self):
        """List tickets with filters."""
        status = random.choice(["open", "in_progress", "escalated", "resolved"])
        self.client.get(
            f"/api/tickets?status={status}&limit=20",
            headers=self.headers
        )


# Event hooks for custom logging
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Log test start."""
    print("\n" + "=" * 60)
    print("LOAD TEST STARTED")
    print("=" * 60)
    print(f"Target Host: {environment.host}")
    print(f"User Classes: {[u.__name__ for u in environment.user_classes]}")
    print("=" * 60 + "\n")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Log test completion with summary."""
    print("\n" + "=" * 60)
    print("LOAD TEST COMPLETED")
    print("=" * 60)

    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio * 100:.2f}%")

    if stats.total.num_requests > 0:
        print(f"\nResponse Times:")
        print(f"  Average: {stats.total.avg_response_time:.2f}ms")
        print(f"  Min: {stats.total.min_response_time:.2f}ms")
        print(f"  Max: {stats.total.max_response_time:.2f}ms")
        print(f"  Median: {stats.total.median_response_time:.2f}ms")
        print(f"  95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        print(f"  99th percentile: {stats.total.get_response_time_percentile(0.99):.2f}ms")

    print("\n" + "=" * 60)


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Track rate limit responses."""
    if response and response.status_code == 429:
        print(f"[RATE LIMITED] {request_type} {name} - Response time: {response_time}ms")
