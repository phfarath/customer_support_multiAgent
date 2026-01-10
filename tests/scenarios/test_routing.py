from . import BaseTestCase
from src.agents.router_agent import RouterAgent
from datetime import datetime

class TestRouter(BaseTestCase):
    async def _run_logic(self):
        router = RouterAgent()
        
        # Case 1: Sales
        ticket_sales = {
            "ticket_id": "t_sales_1",
            "subject": "Interesse no produto",
            "description": "Quero comprar o plano.",
            "company_id": "techcorp_001"
        }
        res_sales = await router.execute("t_sales_1", {"ticket": ticket_sales})
        
        if res_sales.decisions.get("target_team") == "sales":
            print("   ✅ Routing to Sales: PASS")
        else:
            print(f"   ❌ Routing to Sales: FAIL (Got {res_sales.decisions.get('target_team')})")

        # Case 2: Tech
        ticket_tech = {
            "ticket_id": "t_tech_1",
            "subject": "Erro 500",
            "description": "Meu servidor está fora do ar.",
            "company_id": "techcorp_001"
        }
        res_tech = await router.execute("t_tech_1", {"ticket": ticket_tech})
        
        if res_tech.decisions.get("target_team") == "tech":
            print("   ✅ Routing to Tech: PASS")
        else:
            print(f"   ❌ Routing to Tech: FAIL (Got {res_tech.decisions.get('target_team')})")
