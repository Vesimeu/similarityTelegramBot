import logging
from telebot import types

logger = logging.getLogger(__name__)

async def cmd_test_search(bot, message, profile_service, matching_service, admin_ids):
    user_id = message.from_user.id
    if user_id not in admin_ids:
        await bot.reply_to(message, "❌ Команда только для тестирования")
        return
    profile = await profile_service.get_profile(user_id)
    if not profile:
        await bot.reply_to(message, "❌ Профиль не найден. Сначала заполните /start")
        return
    report = [
        "🔧 <b>ТЕСТ ПОИСКА</b>",
        f"👤 <b>Ваш профиль</b>:",
        f"- Возраст: {profile.get('age')}",
        f"- Пол: {profile.get('gender')}",
        f"- Диапазон поиска возраста: {profile.get('preferred_age_range', [18, 99])}",
        f"- Город: {profile.get('preferences', {}).get('preferred_city', 'не указан')}",
        f"- Ключ. слово: {profile.get('preferences', {}).get('preferred_keyword', 'не указано')}"
    ]
    await bot.send_message(user_id, "\n".join(report), parse_mode="HTML")
    await matching_service.find_pair(user_id)
    logger.debug(f"Тестовый поиск для {user_id}: {profile}")

async def toggle_profile_links_mode(bot, message, admin_settings_collection, admin_id):
    try:
        if message.from_user.id != admin_id:
            logger.warning(f"Unauthorized access attempt by {message.from_user.id} (@{message.from_user.username})")
            await bot.reply_to(message, "⛔ Доступ запрещен")
            return
        current_settings = await admin_settings_collection.find_one({"_id": "pairs_display"}) or {"show_full_profiles": True}
        new_mode = not current_settings.get("show_full_profiles", True)
        update_result = await admin_settings_collection.update_one(
            {"_id": "pairs_display"},
            {"$set": {
                "show_full_profiles": new_mode,
                "last_modified": types.datetime.datetime.now(),
                "modified_by": message.from_user.id
            }},
            upsert=True
        )
        response_message = (
            f"🔘 Режим профилей: {'🔗 ССЫЛКИ' if new_mode else '📝 ТЕКСТ'}\n"
            f"🆔 Изменил: {message.from_user.id}\n"
            f"🕒 Время: {types.datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Документов обновлено: {update_result.modified_count}"
        )
        await bot.reply_to(message, response_message)
        if update_result.modified_count == 0:
            logger.warning("No documents were modified during update")
    except Exception as e:
        logger.error(f"Ошибка в toggle_profile_links_mode: {e}")
        await bot.reply_to(message, "⚠️ Ошибка при переключении режима профилей") 