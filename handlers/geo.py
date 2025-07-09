import logging
from services.poll_service import PollService

logger = logging.getLogger(__name__)

async def cmd_distance(bot, message, poll_service: PollService):
    try:
        if len(message.text.split()) < 2:
            await bot.reply_to(message, "Используйте: /distance user_id")
            return
        target_id = int(message.text.split()[1])
        response = await poll_service.get_user_distance(message.from_user.id, target_id)
        await bot.reply_to(message, response)
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка: {str(e)}")

async def cmd_nearby(bot, message, poll_service: PollService):
    try:
        radius = float(message.text.split()[1]) if len(message.text.split()) > 1 else 50.0
        nearby_users = await poll_service.find_nearby_users(message.from_user.id, radius)
        if not nearby_users:
            await bot.reply_to(message, f"🚷 Никого не найдено в радиусе {radius} км")
            return
        response = [f"🏘 Ближайшие пользователи (радиус {radius} км):"]
        for idx, user in enumerate(nearby_users, 1):
            response.append(f"{idx}. {user['name']} ({user['age']} лет) - {user['distance']:.1f} км")
        await bot.reply_to(message, "\n".join(response))
    except Exception as e:
        await bot.reply_to(message, f"❌ Ошибка: {str(e)}") 