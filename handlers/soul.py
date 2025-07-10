import logging
from services.soul_service import SoulService

logger = logging.getLogger(__name__)
 
async def handle_soul_connection(bot, message, soul_service: SoulService):
    prophecy = await soul_service.generate_prophecy(message.from_user.id)
    await bot.reply_to(message, f"🔮 *Пророчество духов:*\n{prophecy}", parse_mode='Markdown') 