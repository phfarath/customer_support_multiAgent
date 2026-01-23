from . import BaseTestCase
from src.agents.resolver_agent import ResolverAgent
from src.database import get_collection, COLLECTION_COMPANY_CONFIGS
from src.models.company_config import CompanyConfig

class TestRAG(BaseTestCase):
    async def _run_logic(self):
        # Fetch seeded config
        col = get_collection(COLLECTION_COMPANY_CONFIGS)
        config_data = await col.find_one({"company_id": "techcorp_001"})
        config = CompanyConfig(**config_data)

        context = {
            "ticket": {
                "ticket_id": "t_rag_check",
                "subject": "DB Info",
                "description": "Qual a porta do MySQL?",
                "company_id": "techcorp_001"
            },
            "routing_result": {"target_team": "tech"},
            "triage_result": {"sentiment": 0.0, "category": "tech"},
            "interactions": [],
            "company_config": config
        }

        resolver = ResolverAgent()
        result = await resolver.execute("t_rag_check", context)
        
        response = result.decisions.get("response", "")
        if "3306" in response:
             print("   ✅ RAG Retrieval: PASS")
        else:
             print(f"   ❌ RAG Retrieval: FAIL (Response: {response})")
