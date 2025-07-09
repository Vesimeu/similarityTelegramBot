import logging
from telebot import types

logger = logging.getLogger(__name__)

async def handle_visibility_settings(bot, user_id, profile_service):
    profile = await profile_service.get_profile(user_id)
    if not profile:
        await bot.send_message(user_id, "❌ Профиль не найден.")
        return
    visibility = profile.get("visibility", {
        "name": True, "age": True, "gender": True, "city": True,
        "email": True, "photo_url": True, "social_links": True, "interests": True, "phone": True
    })
    visibility_status = "👀 Текущая видимость полей:\n"
    for field, is_visible in visibility.items():
        status = "🟢 Видимо" if is_visible else "🔴 Скрыто"
        visibility_status += f"{field.capitalize()}: {status}\n"
    # TODO: вынести клавиатуру в keyboards
    visibility_keyboard = types.InlineKeyboardMarkup()
    visibility_keyboard.row(
        types.InlineKeyboardButton("👤 Имя", callback_data="toggle_visibility_name"),
        types.InlineKeyboardButton("🎂 Возраст", callback_data="toggle_visibility_age"),
        types.InlineKeyboardButton("🚻 Гендер", callback_data="toggle_visibility_gender")
    )
    visibility_keyboard.row(
        types.InlineKeyboardButton("🏙️ Город", callback_data="toggle_visibility_city"),
        types.InlineKeyboardButton("📧 Email", callback_data="toggle_visibility_email"),
        types.InlineKeyboardButton("🌐 URL", callback_data="toggle_visibility_url")
    )
    visibility_keyboard.row(
        types.InlineKeyboardButton("🔗 Соцсети", callback_data="toggle_visibility_social_links"),
        types.InlineKeyboardButton("🎨 Интересы", callback_data="toggle_visibility_interests"),
        types.InlineKeyboardButton("📞 Телефон", callback_data="toggle_visibility_phone")
    )
    await bot.send_message(user_id, visibility_status, reply_markup=visibility_keyboard)

async def handle_toggle_visibility(bot, call, profile_service):
    user_id = call.from_user.id
    field = call.data.replace("toggle_visibility_", "")
    profile = await profile_service.get_profile(user_id)
    if not profile:
        await bot.answer_callback_query(call.id, "❌ Профиль не найден.")
        return
    visibility = profile.get("visibility", {
        "name": True, "age": True, "gender": True, "city": True,
        "email": True, "photo_url": True, "social_links": True, "interests": True, "phone": True
    })
    visibility[field] = not visibility.get(field, True)
    await profile_service.update_profile(user_id, {"visibility": visibility})
    status = "видимо" if visibility[field] else "скрыто"
    await bot.answer_callback_query(call.id, f"✅ Поле '{field}' теперь {status}.")
    await handle_visibility_settings(bot, user_id, profile_service)

async def handle_reset_preferences(bot, call, profile_service):
    user_id = call.from_user.id
    profile = await profile_service.get_profile(user_id)
    current_name = profile.get("name", "") if profile else ""
    await profile_service.update_profile(user_id, {
        "name": current_name,
        "age": None,
        "gender": None,
        "city": None,
        "photo_url": None,
        "preferences": {"gender": "Любой", "preferred_city": "", "preferred_keyword": ""},
        "visibility": {
            "name": True, "age": True, "gender": True, "city": True,
            "email": False, "photo_url": False, "social_links": False, "interests": False, "phone": False
        }
    })
    await bot.answer_callback_query(call.id, "✅ Все настройки сброшены")
    await handle_visibility_settings(bot, user_id, profile_service) 