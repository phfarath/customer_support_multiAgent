"""
Bot Telegram Independente com Lógica de Negócio

Features:
- Modo polling (sem webhook)
- Registro obrigatório de telefone
- Identificação de cliente por telefone
- Saudação personalizada por empresa
- Rate limiting
- Aviso fora de horário comercial
"""
import asyncio
import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.config import settings
from src.adapters.telegram_adapter import TelegramAdapter
from src.database import get_collection, COLLECTION_CUSTOMERS, COLLECTION_BOT_SESSIONS, COLLECTION_COMPANY_CONFIGS
from src.models import TicketChannel
from src.models.bot_session import BotSession, SessionState
from src.models.customer import Customer
from src.models.company_config import CompanyConfig
from src.api.ingest_routes import ingest_message
from src.models import IngestMessageRequest, IngestChannel
from src.utils.business_hours import check_business_hours

logger = logging.getLogger(__name__)


# Mensagens padrão (fallback)
DEFAULT_MESSAGES = {
    "welcome": """
👋 Olá{name}! Bem-vindo ao suporte.

Para começar, preciso do seu telefone para identificação.
Clique no botão abaixo ou digite seu número (ex: +55 11 99999-9999):
""",
    
    "phone_registered": """
✅ Telefone registrado com sucesso!

Agora você pode me enviar sua dúvida ou problema.
Como posso ajudar?
""",
    
    "phone_registered_existing": """
✅ Encontrei seu cadastro!

Olá, {name}! Como posso ajudar você hoje?
""",
    
    "invalid_phone": """
❌ Não consegui identificar o número de telefone.

Por favor, envie no formato internacional, ex:
• +55 11 99999-9999
• +1 555 123-4567

Ou use o botão abaixo para compartilhar:
""",
    
    "select_company": """
📋 Não encontrei seu cadastro.

Por favor, selecione a empresa com a qual você deseja falar:
""",
    
    "rate_limited": """
⏳ Você enviou muitas mensagens!

Por favor, aguarde {minutes} minutos antes de enviar novas mensagens.
""",
    
    "outside_hours": """
🌙 Estamos fora do horário de atendimento.

Horário: {business_hours}

Sua mensagem será processada normalmente, mas a resposta pode demorar um pouco mais.
""",
    
    "help": """
🆘 **Ajuda**

Comandos disponíveis:
• /start - Reiniciar conversa
• /help - Esta mensagem
• /status - Ver seu status

Basta me enviar sua dúvida que irei te ajudar!
""",
    
    "status": """
📊 **Seu Status**

📱 Telefone: {phone}
🏢 Empresa: {company}
💬 Mensagens: {message_count}
📅 Desde: {created_at}
"""
}


class TelegramBot:
    """Bot Telegram com lógica de negócio"""
    
    def __init__(self):
        self.adapter = TelegramAdapter()
        self.rate_limit_window = settings.bot_rate_limit_window  # segundos
        self.rate_limit_max = settings.bot_rate_limit_messages
        self.rate_limit_block = settings.bot_rate_limit_block_time  # segundos
        self._shutdown = False
        
    async def start_polling(self, timeout: int = None):
        """Inicia o bot em modo polling"""
        timeout = timeout or settings.telegram_polling_timeout
        offset = 0
        
        logger.info("🤖 Bot started in polling mode")
        
        # Limpar webhook anterior se existir para evitar conflito
        try:
            await self.adapter.delete_webhook()
            logger.info("Webhook deleted successfully")
        except Exception as e:
            logger.warning(f"Could not delete webhook: {e}")
            
        while not self._shutdown:
            try:
                # Polling loop
                updates = await self._get_updates(offset, timeout)
                
                for update in updates:
                    update_id = update.get("update_id")
                    if update_id:
                        offset = update_id + 1
                        await self.handle_update(update)
                
                # Pequena pausa para não floodar em caso de erro
                if not updates:
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    async def _get_updates(self, offset: int, timeout: int) -> List[Dict[str, Any]]:
        """Busca updates do Telegram via adapter (necessário implementar método getUpdates no adapter)"""
        # Nota: O adapter atual usa httpx direto, vamos adicionar getUpdates aqui mesmo se não tiver no adapter
        # Idealmente mover para o adapter, mas para não modificar muito arquivos, faremos aqui
        url = f"{self.adapter.api_url}/getUpdates"
        payload = {
            "offset": offset,
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"]
        }
        
        # Importar httpx e usar um novo client
        import httpx
        async with httpx.AsyncClient(timeout=timeout + 5) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                if data.get("ok"):
                    return data.get("result", [])
                return []
            except Exception as e:
                logger.error(f"Error getting updates: {e}")
                return []

    async def handle_update(self, update: Dict[str, Any]):
        """Processa um update do Telegram"""
        try:
            # Parse usando o adapter existente
            parsed = self.adapter.parse_webhook_update(update)
            
            # Se for uma mensagem de texto simples ou comando
            if parsed:
                chat_id = parsed["metadata"].get("chat_id")
                external_user_id = parsed["external_user_id"]
                text = parsed["text"]
                user_info = parsed["metadata"]
                
                # Obter sessão
                session = await self.get_or_create_session(chat_id, user_info)
                
                # Verificar rate limit
                if await self.check_rate_limit(session):
                    await self.send_message(chat_id, DEFAULT_MESSAGES["rate_limited"].format(
                        minutes=self.rate_limit_block // 60
                    ))
                    return

                # Comandos
                if text.startswith("/"):
                    await self.handle_command(chat_id, text, session)
                    return
                
                # Fluxo de Registro de Telefone
                if session.state == SessionState.AWAITING_PHONE:
                    await self.handle_phone_input(chat_id, text, session)
                    return
                
                # Fluxo de Seleção de Empresa (se implementado via texto ou botões)
                # ...
                
                # Fluxo Normal (Sessão Registrada)
                if session.state == SessionState.REGISTERED:
                    await self.process_message(chat_id, text, session)
                    return
                
                # Fallback para estados novos
                if session.state == SessionState.NEW:
                     await self.handle_new_user(chat_id, session)
                     
            # Se for contato (telefone via botão), o parse_webhook_update pode não pegar direto se não foi feito para isso
            # Vamos checar manualmente se tem contact
            message = update.get("message", {})
            if message.get("contact"):
                chat_id = message["chat"]["id"]
                phone = message["contact"]["phone_number"]
                user_info = {
                     "username": message.get("from", {}).get("username"),
                     "first_name": message.get("from", {}).get("first_name"),
                     "last_name": message.get("from", {}).get("last_name")
                }
                session = await self.get_or_create_session(chat_id, user_info)
                await self.handle_phone_input(chat_id, phone, session)
                
        except Exception as e:
            logger.error(f"Error handling update: {e}", exc_info=True)

    async def get_or_create_session(self, chat_id: int, user_info: Dict) -> BotSession:
        """Obtém ou cria sessão do usuário no MongoDB"""
        collection = get_collection(COLLECTION_BOT_SESSIONS)
        data = await collection.find_one({"chat_id": chat_id})
        
        if data:
            # Atualizar info do usuário se mudou
            session = BotSession(**data)
            # update logic if needed
            return session
        else:
            # Criar nova sessão
            session = BotSession(
                chat_id=chat_id,
                username=user_info.get("username"),
                first_name=user_info.get("first_name"),
                last_name=user_info.get("last_name"),
                state=SessionState.NEW
            )
            await collection.insert_one(session.dict(by_alias=True))
            return session

    async def update_session_state(self, session: BotSession, new_state: SessionState, **kwargs):
        """Atualiza estado da sessão"""
        collection = get_collection(COLLECTION_BOT_SESSIONS)
        
        updates = {"state": new_state, "updated_at": datetime.utcnow()}
        updates.update(kwargs)
        
        session.state = new_state
        for k, v in kwargs.items():
            setattr(session, k, v)
            
        await collection.update_one(
            {"chat_id": session.chat_id},
            {"$set": updates}
        )

    async def check_rate_limit(self, session: BotSession) -> bool:
        """Verifica rate limit. Retorna True se bloqueado."""
        now = datetime.utcnow()
        
        # Se já está bloqueado
        if session.rate_limit_until and session.rate_limit_until > now:
            return True
            
        # Se estava bloqueado e passou o tempo, libera
        if session.rate_limit_until and session.rate_limit_until <= now:
            await self.update_session_state(session, session.state, rate_limit_until=None)
            
        # Contagem de mensagens (simplificado: limpa a cada minuto da window)
        # Uma implementação mais robusta usaria sliding window
        # Aqui vamos usar o timestamp da última mensagem para resetar se passou muito tempo
        if session.last_message_at:
             time_diff = (now - session.last_message_at).total_seconds()
             if time_diff > self.rate_limit_window:
                 # Reset count
                 await self.update_session_state(session, session.state, message_count=0)
                 session.message_count = 0
        
        # Incrementa
        new_count = session.message_count + 1
        updates = {"message_count": new_count, "last_message_at": now}
        
        if new_count > self.rate_limit_max:
            # Bloqueia
            block_until = now + timedelta(seconds=self.rate_limit_block)
            updates["rate_limit_until"] = block_until
            await self.update_session_state(session, session.state, **updates)
            return True
        
        await self.update_session_state(session, session.state, **updates)
        return False

    async def handle_command(self, chat_id: int, text: str, session: BotSession):
        """Processa comandos"""
        command = text.split()[0].lower()
        
        if command == "/start":
            # Se já registrado, mostra boas-vindas da empresa
            if session.state == SessionState.REGISTERED and session.company_id:
                welcome = await self.get_welcome_message(session.company_id, session.first_name)
                await self.send_message(chat_id, "ℹ️ Conversa reiniciada.\n\n" + welcome)
            else:
                 await self.handle_new_user(chat_id, session)
                 
        elif command == "/help":
            await self.send_message(chat_id, DEFAULT_MESSAGES["help"])
            
        elif command == "/status":
            status_msg = DEFAULT_MESSAGES["status"].format(
                phone=session.phone_number or "Não registrado",
                company=session.company_id or "Nenhuma",
                message_count=session.message_count,
                created_at=session.created_at.strftime("%d/%m/%Y %H:%M")
            )
            await self.send_message(chat_id, status_msg)

    async def handle_new_user(self, chat_id: int, session: BotSession):
        """Fluxo inicial"""
        await self.update_session_state(session, SessionState.AWAITING_PHONE)
        
        # Enviar pedido de telefone com botão
        name_str = f", {session.first_name}" if session.first_name else ""
        msg = DEFAULT_MESSAGES["welcome"].format(name=name_str)
        
        # Enviar via payload específico do Telegram para botão de contato (usando requests direto pois adapter pode n ter suporte a keyboard)
        # Vamos assumir texto simples primeiro, depois melhoramos os botoes se o adapter permitir
        # O adapter simples só envia texto. Vamos enviar texto pedindo input.
        await self.send_message(chat_id, msg)

    async def handle_phone_input(self, chat_id: int, text: str, session: BotSession):
        """Processa input de telefone"""
        # Limpar e validar
        phone = "".join(filter(str.isdigit, text))
        
        # Validação básica
        if len(phone) < 10 or len(phone) > 15:
            await self.send_message(chat_id, DEFAULT_MESSAGES["invalid_phone"])
            return

        # Adicionar + se faltar (assumindo internacional se não tiver DDI claro, mas vamos simplificar)
        if not text.startswith("+") and not text.startswith("00"):
             # Se parece BR...
             if len(phone) >= 10 and len(phone) <= 11 and phone.startswith("1") or phone.startswith("2") or phone.startswith("3") or phone.startswith("4") or phone.startswith("5") or phone.startswith("6") or phone.startswith("7") or phone.startswith("8") or phone.startswith("9"):
                  phone = "55" + phone
        
        formatted_phone = "+" + phone
        
        # Buscar cliente existente
        customer = await self.lookup_customer_by_phone(formatted_phone)
        
        if customer:
            # Cliente existe -> Vincular
            company_id = customer["company_id"]
            await self.update_session_state(
                session, 
                SessionState.REGISTERED, 
                phone_number=formatted_phone,
                customer_id=customer["customer_id"],
                company_id=company_id
            )
            
            # Enviar Welcome
            welcome = await self.get_welcome_message(company_id, session.first_name)
            await self.send_message(chat_id, DEFAULT_MESSAGES["phone_registered_existing"].format(
                name=session.first_name or "Cliente"
            ))
            await self.send_message(chat_id, welcome)
            
        else:
            # Cliente NÃO existe -> Fluxo de escolher empresa
            # Simplificação: Como não temos UI de botões complexa no adapter,
            # vamos atribuir à empresa padrão ou pedir para digitar ID da empresa
            # Se houver config de default_company_id, usa ela
            default_company = settings.bot_default_company_id
            
            if default_company:
                # Criar Customer
                customer_id = f"CUST-{formatted_phone.replace('+', '')}"
                new_customer = Customer(
                    customer_id=customer_id,
                    phone_number=formatted_phone,
                    company_id=default_company,
                    name=f"{session.first_name} {session.last_name or ''}".strip(),
                    telegram_chat_id=chat_id
                )
                
                await get_collection(COLLECTION_CUSTOMERS).insert_one(new_customer.dict(by_alias=True))
                
                # Atualizar Sessão
                await self.update_session_state(
                    session,
                    SessionState.REGISTERED,
                    phone_number=formatted_phone,
                    customer_id=customer_id,
                    company_id=default_company
                )
                
                welcome = await self.get_welcome_message(default_company, session.first_name)
                await self.send_message(chat_id, DEFAULT_MESSAGES["phone_registered"])
                await self.send_message(chat_id, welcome)
                
            else:
                 # Se não tiver default, lista empresas (simplificado)
                 # Em produção ideal, usaria InlineKeyboard
                 companies_cursor = get_collection(COLLECTION_COMPANY_CONFIGS).find({})
                 companies = await companies_cursor.to_list(length=10)
                 
                 if not companies:
                     await self.send_message(chat_id, "Desculpe, nenhuma empresa configurada no sistema.")
                     return
                     
                 # Por enquanto, pega a primeira empresa encontrada para não travar o usuário
                 # (Melhoria futura: fluxo de seleção real)
                 first_company = companies[0]
                 company_id = first_company["company_id"]
                 
                 # Criar Customer
                 customer_id = f"CUST-{formatted_phone.replace('+', '')}"
                 new_customer = Customer(
                    customer_id=customer_id,
                    phone_number=formatted_phone,
                    company_id=company_id,
                    name=f"{session.first_name} {session.last_name or ''}".strip(),
                    telegram_chat_id=chat_id
                 )
                 try:
                    await get_collection(COLLECTION_CUSTOMERS).insert_one(new_customer.dict(by_alias=True))
                 except Exception:
                    # Se der erro de duplicidade (race condition), tenta buscar
                    pass

                 await self.update_session_state(
                    session,
                    SessionState.REGISTERED,
                    phone_number=formatted_phone,
                    customer_id=customer_id,
                    company_id=company_id
                 )
                 
                 welcome = await self.get_welcome_message(company_id, session.first_name)
                 await self.send_message(chat_id, DEFAULT_MESSAGES["phone_registered"])
                 await self.send_message(chat_id, f"(Automaticamente vinculado à empresa: {first_company.get('company_name')})")
                 await self.send_message(chat_id, welcome)

    async def lookup_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Busca cliente por telefone no MongoDB"""
        return await get_collection(COLLECTION_CUSTOMERS).find_one({"phone_number": phone})

    async def get_welcome_message(self, company_id: str, first_name: str) -> str:
        """Retorna mensagem de boas-vindas da empresa ou fallback"""
        config = await get_collection(COLLECTION_COMPANY_CONFIGS).find_one({"company_id": company_id})
        if config and config.get("bot_welcome_message"):
            return config["bot_welcome_message"]
        return f"Olá {first_name or ''}, em que posso ajudar?"

    async def check_business_hours(self, company_id: str) -> tuple[bool, str, str]:
        """Verifica horário usando business_hours.py. Retorna (is_open, hours_str, outside_message)"""
        config = await get_collection(COLLECTION_COMPANY_CONFIGS).find_one({"company_id": company_id})
        
        if not config:
            return True, "", ""  # Se não tem config, assume aberto
            
        hours = config.get("business_hours")
        outside_msg = config.get("bot_outside_hours_message") or DEFAULT_MESSAGES["outside_hours"]
        
        if not hours:
            return True, "", outside_msg
            
        # Usar módulo business_hours.py
        is_open, hours_str = check_business_hours(hours)
        
        return is_open, hours_str, outside_msg

    async def process_message(self, chat_id: int, text: str, session: BotSession):
        """Processa mensagem através do pipeline"""
        
        # Verificar horário (Aviso apenas)
        is_open, hours_str, outside_msg = await self.check_business_hours(session.company_id)
        
        if not is_open:
            # Envia aviso mas continua processamento
            msg = outside_msg.format(business_hours=hours_str)
            await self.send_message(chat_id, msg)
            
        # Ingestão
        try:
             # Criar request de ingestão
             # Importante: enviar metadata com company_id para o pipeline saber o contexto
             request = IngestMessageRequest(
                 channel=IngestChannel.TELEGRAM,
                 external_user_id=f"telegram:{chat_id}",
                 text=text,
                 metadata={
                     "chat_id": chat_id,
                     "username": session.username,
                     "first_name": session.first_name,
                     "company_id": session.company_id,
                     "phone_number": session.phone_number
                 }
             )
             
             # Chamar ingest_message diretamente
             response = await ingest_message(request)
             
             if response.reply_text:
                 await self.send_message(chat_id, response.reply_text)
                 
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self.send_message(chat_id, "Desculpe, tive um erro interno ao processar sua mensagem.")

    async def send_message(self, chat_id: int, text: str):
        """Envia mensagem usando adapter"""
        try:
            await self.adapter.send_message(chat_id, text)
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
