import asyncio
import random
from telebot import types
import logging

logger = logging.getLogger(__name__)

from keyboards.keyboards import main_menu_keyboard
# TODO: импортировать другие клавиатуры по мере необходимости

# Шаблон: сервис поиска пары будет импортироваться
# from services.matching_service import MatchingService

# Глобальные переменные для хранения состояния поиска (будут вынесены в сервис/хранилище)
current_search_results = {}
user_skip_settings = {}
awaiting_skip_input = set()
awaiting_temp_skip_input = set()

async def handle_find_pair(bot, message, matching_service, user_data, current_search_results, user_skip_settings):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал поиск пары.")
    # Очищаем временные настройки пропуска
    if user_id in user_skip_settings:
        user_skip_settings[user_id]['temporary'] = 0
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
async def show_partner_profile(bot, user_id, matching_service):
    if user_id not in current_search_results:
        # Если нет сессии поиска — инициируем поиск
        await handle_find_pair(bot, None, matching_service, {}, current_search_results, user_skip_settings)
        return
    data = current_search_results[user_id]
    try:
        partner = await matching_service.get_partner_profile(user_id, data["current_index"])
        if not partner:
            await bot.send_message(user_id, "🏰 Все анкеты просмотрены!", parse_mode="Markdown")
            del current_search_results[user_id]
            return
        # ... здесь формируем текст профиля и клавиатуру ...
        keyboard = types.InlineKeyboardMarkup()
        # Добавить кнопки next/prev/like и т.д.
        await bot.send_message(user_id, f"Профиль: {partner}", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка показа профиля: {e}")
        await bot.send_message(user_id, "Ошибка показа профиля.")

# Навигация по анкетам (next/prev)
async def handle_navigation(bot, call, matching_service):
    user_id = call.from_user.id
    if user_id not in current_search_results:
        await bot.answer_callback_query(call.id, "❌ Сессия поиска устарела")
        return
    data = current_search_results[user_id]
    if call.data == "next_profile":
        data["current_index"] += 1
    elif call.data == "prev_profile":
        data["current_index"] = max(0, data["current_index"] - 1)
    await show_partner_profile(bot, user_id, matching_service)
    await bot.answer_callback_query(call.id)

# Обработка постоянного skip
async def handle_skip_input(bot, message, matching_service):
    user_id = message.from_user.id
    try:
        skip_count = int(message.text)
        if 0 <= skip_count <= 10:
            user_skip_settings[user_id] = {'permanent': skip_count, 'temporary': 0}
            awaiting_skip_input.discard(user_id)
            await bot.send_message(user_id, f"⚙️ Установлен постоянный шаг: {skip_count} анкет\n🔮 Начинаю поиск...", parse_mode="Markdown")
            await handle_find_pair(bot, message, matching_service, {}, current_search_results, user_skip_settings)
        else:
            await bot.send_message(user_id, "⚠️ Введите число от 0 до 10", parse_mode="Markdown")
    except ValueError:
        await bot.send_message(user_id, "⚠️ Пожалуйста, введите число", parse_mode="Markdown")

# Обработка разового skip
async def handle_temp_skip_input(bot, message, matching_service):
    user_id = message.from_user.id
    try:
        skip_count = int(message.text)
        if skip_count >= 0:
            perm = user_skip_settings.get(user_id, {}).get('permanent', 0)
            user_skip_settings[user_id] = {'permanent': perm, 'temporary': skip_count}
            awaiting_temp_skip_input.discard(user_id)
            await bot.send_message(user_id, f"⏩ Будет пропущено {skip_count} анкет (разово)\n⚙️ Постоянный шаг: {perm} анкет\n🔮 Начинаю поиск...", parse_mode="Markdown")
            await handle_find_pair(bot, message, matching_service, {}, current_search_results, user_skip_settings)
        else:
            await bot.send_message(user_id, "⚠️ Введите положительное число", parse_mode="Markdown")
    except ValueError:
        await bot.send_message(user_id, "⚠️ Пожалуйста, введите число", parse_mode="Markdown")

# Callback-обработчик выбора режима skip
async def handle_skip_mode(bot, call):
    user_id = call.from_user.id
    if call.data == "skip_default":
        awaiting_skip_input.add(user_id)
        await bot.send_message(user_id, "🔢 Введите ПОСТОЯННЫЙ шаг пропуска цифрой (от 0 до 10):", parse_mode="Markdown")
    else:
        awaiting_temp_skip_input.add(user_id)
        await bot.send_message(user_id, "⏩ Введите количество анкет для РАЗОВОГО пропуска:", parse_mode="Markdown")
    await bot.answer_callback_query(call.id)

# Callback-обработчик like
async def handle_like(bot, call, matching_service):
    user_id = call.from_user.id
    partner_id = int(call.data.split('_')[1])
    await matching_service.like_partner(user_id, partner_id)
    await bot.answer_callback_query(call.id, "💌 Симпатия отправлена!")
    # Можно сразу показать следующего партнёра
    current_search_results[user_id]["current_index"] += 1
    await show_partner_profile(bot, user_id, matching_service) 