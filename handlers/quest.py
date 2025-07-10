import asyncio
from telebot import types
import logging
from services.quest_service import QuestService

logger = logging.getLogger(__name__)

# TODO: импортировать keyboards и тексты, если потребуется

async def handle_mangu_royal(bot, message):
    royal_scroll = (
        "📜 *Волшебный Указ Добросердечных Встреч*\n"
        "✨ **Запечатано лунным светом и лепестками хрустальных роз** ✨\n\n"
        "🦋 *Драгоценный гость, свет очей наших!*  \n"
        "В башне @apbaabpa, где феи плетут нити судеб, а мудрые волшебники бережно хранят каждое слово,  \n"
        "сегодня открываются врата *Турнира Ласковых Мнений*: \n\n"
        "🌹 Ваши мысли — как алмазы в короне королевства, и мы ждём их с трепетом  \n"
        "🕊️ Голубки-посланницы разнесут ваши слова по свету  \n"
        "🍃 Эльфы-хранители аккуратно сложат каждую идею в шкатулку мудрости  \n\n"
        "💎 *О, прекрасный странник, как присоединиться к этому дивному действу?*  \n"
        "1. Проследуйте в хрустальные чертоги: @apbaabpa  \n"
        "2. Шепните пароль «Лунный свет» стражам-гномам  \n"
        "3. Окунитесь в море тёплых бесед, где каждому рады!"
    )
    markup = types.InlineKeyboardMarkup()
    castle_button = types.InlineKeyboardButton(
        text="🔮 Коснуться волшебного зеркала 🔮",
        url="https://t.me/apbaabpa"
    )
    markup.add(castle_button)
    await bot.send_chat_action(message.chat.id, 'typing')
    await asyncio.sleep(1.2)
    herald_msg = await bot.send_message(
        message.chat.id,
        "🧚 *Фея-невидимка рассыпает звёздную пыль...*",
        parse_mode="Markdown"
    )
    await asyncio.sleep(0.8)
    await bot.edit_message_text(
        royal_scroll,
        chat_id=message.chat.id,
        message_id=herald_msg.message_id,
        parse_mode="Markdown",
        reply_markup=markup,
        disable_web_page_preview=True
    )
    seal_msg = await bot.send_message(
        message.chat.id,
        "🌺 *Печать Королевы Фей тает в воздухе, оставляя аромат жасмина...*",
        parse_mode="Markdown"
    )
    await asyncio.sleep(1.5)
    await bot.delete_message(message.chat.id, seal_msg.message_id)

async def handle_tournament(bot, message, quest_service: QuestService):
    await quest_service.start_quest(message)

async def handle_quest(bot, message, quest_service: QuestService):
    await quest_service.start_quest(message)

# Для регистрации хендлеров в main.py или роут  ере:
# bot.register_message_handler(lambda m: m.text == "🌺@apbaabpa", handle_tournament)
# bot.register_message_handler(commands=['quest'], handle_quest)
# bot.register_message_handler(commands=['mangu'], handle_mangu_royal) 