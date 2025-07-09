import asyncio
import random
from telebot import types
import logging

logger = logging.getLogger(__name__)

from keyboards.keyboards import main_menu_keyboard
# TODO: импортировать другие клавиатуры по мере необходимости

from utils.state_service import StateService

# Все функции теперь принимают state_service вместо глобальных переменных

async def handle_find_pair(bot, message, matching_service, state_service: StateService):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал поиск пары.")
    # Очищаем временные настройки пропуска через state_service
    skip_settings = state_service.get_skip_settings(user_id)
    skip_settings["temporary"] = 0
    state_service.set_skip_settings(user_id, skip_settings)
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("🌄 Поиск анкет", callback_data="skip_default"),
        types.InlineKeyboardButton("🦋 Поиск с пропуском", callback_data="skip_temp")
    )
    await bot.send_message(
        user_id,
        "✨ *О, прекрасный цветок в садах Великого Духа!* ✨\n\n"
        "🦅 Кондор судьбы принес весть о вашей готовности найти родное сердце.\n\n"
        "☀️ *Если стеснительность мешает, то встретимся здесь https://parmesan-perm.ru/ :*\n"
        "• *Путь Мудрого Искателя* - ступайте уверенно, пропуская N анкет навсегда\n"
        "• *Миг Судьбы* - лишь однажды сверните с тропы, чтобы потом вернуться\n\n"
        "🌕 *Священное предсказание:*\n"
        "Вижу в дыме священной травы - ваша судьба уже плетет золотые нити встречи!\n\n"
        "🌾 *Мудрость предков гласит:*\n"
        "Чтобы очистить свой путь, сожгите старую анкету в священном огне настроек",
        reply_markup=markup,
        parse_mode="Markdown"
    )

# Показ профиля партнёра
async def show_partner_profile(bot, user_id, matching_service, state_service: StateService):
    search_results = state_service.get_search_results(user_id)
    if not search_results:
        await handle_find_pair(bot, None, matching_service, state_service)
        return
    data = search_results
    try:
        partner = await matching_service.get_partner_profile(user_id, data["current_index"])
        if not partner:
            await bot.send_message(user_id, "🏰 Все анкеты просмотрены!", parse_mode="Markdown")
            state_service.clear_search_results(user_id)
            return
        keyboard = types.InlineKeyboardMarkup()
        await bot.send_message(user_id, f"Профиль: {partner}", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка показа профиля: {e}")
        await bot.send_message(user_id, "Ошибка показа профиля.")

# Навигация по анкетам (next/prev)
async def handle_navigation(bot, call, matching_service, state_service: StateService):
    user_id = call.from_user.id
    data = state_service.get_search_results(user_id)
    if not data:
        await bot.answer_callback_query(call.id, "❌ Сессия поиска устарела")
        return
    if call.data == "next_profile":
        data["current_index"] += 1
    elif call.data == "prev_profile":
        data["current_index"] = max(0, data["current_index"] - 1)
    state_service.set_search_results(user_id, data)
    await show_partner_profile(bot, user_id, matching_service, state_service)
    await bot.answer_callback_query(call.id)

# Обработка постоянного skip
async def handle_skip_input(bot, message, matching_service, state_service: StateService):
    user_id = message.from_user.id
    try:
        skip_count = int(message.text)
        if 0 <= skip_count <= 10:
            state_service.set_skip_settings(user_id, {"permanent": skip_count, "temporary": 0})
            state_service.remove_awaiting_skip(user_id)
            await bot.send_message(user_id, f"⚙️ Установлен постоянный шаг: {skip_count} анкет\n🔮 Начинаю поиск...", parse_mode="Markdown")
            await handle_find_pair(bot, message, matching_service, state_service)
        else:
            await bot.send_message(user_id, "⚠️ Введите число от 0 до 10", parse_mode="Markdown")
    except ValueError:
        await bot.send_message(user_id, "⚠️ Пожалуйста, введите число", parse_mode="Markdown")

# Обработка разового skip
async def handle_temp_skip_input(bot, message, matching_service, state_service: StateService):
    user_id = message.from_user.id
    try:
        skip_count = int(message.text)
        if skip_count >= 0:
            perm = state_service.get_skip_settings(user_id).get('permanent', 0)
            state_service.set_skip_settings(user_id, {"permanent": perm, "temporary": skip_count})
            state_service.remove_awaiting_temp_skip(user_id)
            await bot.send_message(user_id, f"⏩ Будет пропущено {skip_count} анкет (разово)\n⚙️ Постоянный шаг: {perm} анкет\n🔮 Начинаю поиск...", parse_mode="Markdown")
            await handle_find_pair(bot, message, matching_service, state_service)
        else:
            await bot.send_message(user_id, "⚠️ Введите положительное число", parse_mode="Markdown")
    except ValueError:
        await bot.send_message(user_id, "⚠️ Пожалуйста, введите число", parse_mode="Markdown")

# Callback-обработчик выбора режима skip
async def handle_skip_mode(bot, call, state_service: StateService):
    user_id = call.from_user.id
    if call.data == "skip_default":
        state_service.add_awaiting_skip(user_id)
        await bot.send_message(user_id, "🔢 Введите ПОСТОЯННЫЙ шаг пропуска цифрой (от 0 до 10):", parse_mode="Markdown")
    else:
        state_service.add_awaiting_temp_skip(user_id)
        await bot.send_message(user_id, "⏩ Введите количество анкет для РАЗОВОГО пропуска:", parse_mode="Markdown")
    await bot.answer_callback_query(call.id)

# Callback-обработчик like
async def handle_like(bot, call, matching_service, state_service: StateService):
    user_id = call.from_user.id
    partner_id = int(call.data.split('_')[1])
    await matching_service.like_partner(user_id, partner_id)
    await bot.answer_callback_query(call.id, "💌 Симпатия отправлена!")
    data = state_service.get_search_results(user_id)
    data["current_index"] += 1
    state_service.set_search_results(user_id, data)
    await show_partner_profile(bot, user_id, matching_service, state_service) 