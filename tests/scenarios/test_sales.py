from . import BaseTestCase
from src.agents.resolver_agent import ResolverAgent
from src.database import get_collection, COLLECTION_COMPANY_CONFIGS
from src.models.company_config import CompanyConfig

class TestSales(BaseTestCase):
    async def _run_logic(self):
        # Fetch seeded config
        col = get_collection(COLLECTION_COMPANY_CONFIGS)
        config_data = await col.find_one({"company_id": "techcorp_001"})
        config = CompanyConfig(**config_data)

        context = {
            "ticket": {
                "ticket_id": "t_sales_check",
                "subject": "Preço",
                "description": "Quanto custa o Produto Teste?",
                "company_id": "techcorp_001"
            },
            "routing_result": {"target_team": "sales"},
            "triage_result": {"sentiment": 0.0, "category": "sales"},
            "interactions": [],
            "company_config": config
        }

        resolver = ResolverAgent()
        result = await resolver.execute("t_sales_check", context)
        
        response = result.decisions.get("response", "")
        if "999" in response or "R$ 999" in response:
             print("   ✅ Sales Product Injection: PASS")
        else:
             print(f"   ❌ Sales Product Injection: FAIL (Response: {response})")
