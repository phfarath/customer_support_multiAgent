"""
Script to test the RAG Flow logic in Resolver Agent
"""
import asyncio
import os
from datetime import datetime
from src.agents.resolver_agent import ResolverAgent
from src.models.company_config import CompanyConfig, KnowledgeBaseConfig

async def test_rag_flow():
    # Mock Company Config with KB enabled
    kb_config = KnowledgeBaseConfig(
        enabled=True,
        vector_db_collection="company_knowledge"
    )
    
    company_config = CompanyConfig(
        company_id="techcorp_001",
        company_name="TechSolutions",
        knowledge_base=kb_config
    )
    
    # Mock Ticket Asking about Technical Manual Info
    context = {
        "ticket": {
            "ticket_id": "test_ticket_rag_001",
            "subject": "Dúvida sobre Banco de Dados",
            "description": "Qual a porta padrão para conectar no MySQL?",
            "priority": "P3",
            "channel": "telegram",
            "created_at": datetime.utcnow().isoformat() 
        },
        "triage_result": {
            "category": "tech",
            "sentiment": 0.0,
            "confidence": 0.9
        },
        "routing_result": {
            "target_team": "tech" 
        },
        "interactions": [],
        "company_config": company_config.model_dump()
    }
    
    print("🚀 Initializing Resolver Agent for RAG Test...")
    resolver = ResolverAgent()
    
    try:
        print("🤖 Executing Resolver Agent...")
        result = await resolver.execute("test_ticket_rag_001", context)
        
        if result.success:
            print("\n✅ Sucesso!")
            response_text = result.decisions.get('response', '')
            print(f"🗣️ Response:\n{response_text}")
            
            if "3306" in response_text:
                print("\n✅ TEST PASSED: '3306' found in response! RAG is working.")
            else:
                print("\n⚠️ TEST WARNING: '3306' NOT found. RAG might have failed to retrieve context.")
        else:
            print(f"\n❌ Falha: {result.message}")
            
    except Exception as e:
        print(f"\n❌ Erro de execução: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    asyncio.run(test_rag_flow())
