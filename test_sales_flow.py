"""
Script to test the Sales Flow logic in Resolver Agent
"""
import asyncio
from datetime import datetime
from src.agents.resolver_agent import ResolverAgent
from src.agents.router_agent import RouterAgent
from src.models.company_config import CompanyConfig, Team
from unittest.mock import MagicMock

async def test_sales_flow():
    # Mock Company Config
    sales_team = Team(
        team_id="sales",
        name="Vendas",
        description="Focado em vendas",
        instructions="Seja um vendedor agressivo.",
        is_sales=True
    )
    
    company_config = CompanyConfig(
        company_id="techcorp_001",
        company_name="TechSolutions",
        products=[
            {"name": "Produto Super", "id": "p1", "price": "R$ 1000", "details": "O melhor do mercado"}
        ],
        teams=[sales_team]
    )
    
    # Mock Ticket Context
    context = {
        "ticket": {
            "ticket_id": "test_ticket_001",
            "subject": "Preço do Produto Super",
            "description": "Quanto custa o Produto Super?",
            "priority": "P3",
            "channel": "telegram",
            "created_at": datetime.utcnow().isoformat() 
        },
        "triage_result": {
            "category": "sales",
            "sentiment": 0.5,
            "confidence": 0.9
        },
        "routing_result": {
            "target_team": "sales" # Router would have output this
        },
        "interactions": [],
        "company_config": company_config.model_dump()
    }
    
    print("🚀 Initializing Resolver Agent...")
    resolver = ResolverAgent()
    
    # We want to intercept the internal call to OpenAI to see the prompt
    # BUT since we can't easily mock the internal import without dependency injection,
    # we will rely on observing the output if we run it for real, OR we can mock the openai client if possible.
    # For this check, let's just run it and see if it doesn't crash, and print the response.
    # Note: This requires OPENAI_API_KEY to be set in environment.
    
    try:
        print("🤖 Executing Resolver Agent...")
        result = await resolver.execute("test_ticket_001", context)
        
        if result.success:
            print("\n✅ Sucesso!")
            print(f"🎯 Decisões: {result.decisions.keys()}")
            print(f"🗣️ Response:\n{result.decisions.get('response')}")
            
            response_text = result.decisions.get('response', '')
            if "R$ 1000" in response_text or "Produto Super" in response_text:
                print("\n✅ TEST PASSED: Product info found in response!")
            else:
                print("\n⚠️ TEST WARNING: Product info NOT found. Check if LLM used the context.")
        else:
            print(f"\n❌ Falha: {result.message}")
            
    except Exception as e:
        print(f"\n❌ Erro de execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_sales_flow())
