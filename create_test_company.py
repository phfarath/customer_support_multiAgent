"""
Script para criar uma empresa de teste no banco de dados
"""
import asyncio
from datetime import datetime
from src.database import get_collection, COLLECTION_COMPANY_CONFIGS
from src.models.company_config import CompanyConfig

async def create_test_company():
    # Dados da empresa fictícia
    company_data = {
        "company_id": "techcorp_001",
        "company_name": "TechSolutions Integradora",
        "support_email": "suporte@techsolutions.com.br",
        "support_phone": "+5511999999999",
        "business_hours": {
            "mon-fri": "09:00-18:00",
            "sat": "09:00-13:00"
        },
        "bot_name": "TechBot",
        "bot_welcome_message": """
👋 Olá! Bem-vindo à TechSolutions. 

Sou o TechBot e vou te ajudar com:
- Suporte Técnico
- Consultas Financeiras
- Status de Pedidos

Como posso ser útil hoje?
""",
        "bot_outside_hours_message": """
🌙 Olá! No momento estamos fora do nosso horário de atendimento (Seg-Sex 9h-18h).

Você pode deixar sua mensagem e nossa equipe responderá assim que retomarmos as atividades!
""",
        "products": [
            {"name": "Cloud Server Pro", "id": "prod_001"},
            {"name": "Consultoria DevOps", "id": "serv_002"}
        ],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    try:
        # Validar com o modelo Pydantic
        company = CompanyConfig(**company_data)
        
        # Inserir no banco
        collection = get_collection(COLLECTION_COMPANY_CONFIGS)
        
        # Usar update_one com upsert para evitar erro se já existir
        result = await collection.update_one(
            {"company_id": company.company_id},
            {"$set": company.dict(by_alias=True)},
            upsert=True
        )
        
        if result.upserted_id:
            print(f"✅ Empresa de teste criada com sucesso! ID: {result.upserted_id}")
        else:
            print(f"✅ Empresa de teste atualizada com sucesso!")
            
        print(f"🆔 Company ID: {company.company_id}")
        print(f"🏢 Nome: {company.company_name}")
        
    except Exception as e:
        print(f"❌ Erro ao criar empresa: {e}")

if __name__ == "__main__":
    # Importar aqui para garantir que variáveis de ambiente carreguem se necessário
    from dotenv import load_dotenv
    load_dotenv()
    
    # Executar loop
    asyncio.run(create_test_company())
