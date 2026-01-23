"""
Base Test Case class
"""
import sys
import os
import asyncio
from typing import Dict, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

class BaseTestCase:
    def __init__(self, name: str):
        self.name = name
    
    async def run(self):
        print(f"\n🏃 Running Test: {self.name}")
        try:
            await self._run_logic()
        except Exception as e:
            print(f"❌ FAIL: {e}")
            import traceback
            traceback.print_exc()

    async def _run_logic(self):
        raise NotImplementedError
