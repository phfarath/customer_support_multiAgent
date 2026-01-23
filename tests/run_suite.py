"""
Master Test Runner
"""
import asyncio
import os
import sys
import time
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.seeds.reset_db import reset_database
from tests.seeds.seed_companies import seed_companies
from tests.scenarios.test_routing import TestRouter
from tests.scenarios.test_sales import TestSales
from tests.scenarios.test_rag import TestRAG
from tests.scenarios.test_escalation import TestEscalation

async def run_suite():
    load_dotenv()
    
    start_time = time.time()
    print("🧪 Starting Test Suite...")
    
    # 1. Setup
    print("\n--- [SETUP] ---")
    await reset_database()
    await seed_companies()
    
    # 2. Scenarios
    print("\n--- [SCENARIOS] ---")
    scenarios = [
        TestRouter("Routing Logic"),
        TestSales("Sales Persona & Products"),
        TestRAG("RAG Knowledge Retrieval"),
        TestEscalation("Escalation Logic")
    ]
    
    for scenario in scenarios:
        await scenario.run()
        
    duration = time.time() - start_time
    print(f"\n🏁 Suite Completed in {duration:.2f}s")

if __name__ == "__main__":
    asyncio.run(run_suite())
