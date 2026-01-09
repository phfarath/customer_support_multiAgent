"""
Script para executar o bot Telegram em modo polling

Uso:
    python run_telegram_bot.py
"""
import asyncio
import logging
from src.bots import TelegramBot
from src.database import ensure_indexes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    try:
        # Garantir conexão e índices
        print("🔌 Conectando ao banco de dados...")
        await ensure_indexes()
        print("✅ Banco de dados conectado e índices verificados")
        
        bot = TelegramBot()
        print("\n🤖 Bot Telegram iniciado!")
        print("====================================")
        print("📱 Registro de telefone: OBRIGATÓRIO")
        print("🏢 Saudação: Personalizada por empresa")
        print("⏰ Rate limit: Ativo")
        print("🌙 Fora de horário: Aviso + processamento normal")
        print("====================================")
        print("\nPressione Ctrl+C para parar")
        
        await bot.start_polling()
        
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
