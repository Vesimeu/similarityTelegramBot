import asyncio
import random
from telebot import types
from main import bot,logger
from telebot.async_telebot import AsyncTeleBot
import logging


# Импортируйте сервисы и main_menu_keyboard по мере необходимости
# from services.profile_service import ProfileService
# from keyboards.keyboards import main_menu_keyboard

async def show_welcome_scroll(user_id: int):
    scroll = """
✨ *Хрустальный Эдикт Светлейшего Совета* ✨

┏━━━━━━━❀•°•⚜•°•❀━━━━━━━┓
   🌌 Драгоценнейшему из ангелов земных,
   бриллианту в оправе нашего сообщества,
   истинному вельможе добрых намерений!

   🌟 *Мудрейшие Духи Радужных Башен повелевают:*
   1. Каждое ваше слово — жемчужина в ларце мудрости
   2. Тени невежества пусть растворяются в вашем свете
   3. Анкеты — как крылья ангелов-хранителей

   🕊️ Пусть феи удачи осыпают вас лепестками!
┗━━━━━━━━━━•☽•━━━━━━━━━━┛

🌙 *Примите этот дар сердец, о лучезарный!* 🌙
"""
    await bot.send_message(
        user_id, 
        scroll, 
        parse_mode="Markdown",
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(
                "🌹 Клянусь перьями феникса!", 
                callback_data="scroll_accept"
            )
        )
    )

@bot.message_handler(commands=['start'])
async def handle_start(message: types.Message):
    user_id = message.from_user.id
    try:
        scroll_steps = [
            "🌙 *Серебристый свиток судеб нежно разворачивается...* [░░░░░░░░░░]",
            "✨ *Чернила из слез феникса проявляют узоры...* [▓▓░░░░░░░░]",
            "🦢 *Перо ангела выводит ваше имя золотом...* [▓▓▓▓▓░░░░░]",
            "🔮 *Хрустальная печать застывает в воздухе...* [▓▓▓▓▓▓▓▓░░]",
            "💎 *Готово, о драгоценнейший!* [▓▓▓▓▓▓▓▓▓▓]"
        ]
        scroll_msg = await bot.send_message(
            user_id, 
            scroll_steps[0],
            parse_mode="Markdown"
        )
        for step in scroll_steps[1:]:
            await asyncio.sleep(0.5)
            await bot.edit_message_text(
                step,
                chat_id=user_id, 
                message_id=scroll_msg.message_id,
                parse_mode="Markdown"
            )
        # Здесь должна быть логика проверки профиля через сервис (заглушка)
        profile = None  # TODO: получить профиль пользователя через сервис
        if not profile or not getattr(profile, "is_completed", False):
            await bot.delete_message(user_id, scroll_msg.message_id)
            # TODO: проверить seen_welcome_scroll через сервис
            seen_welcome_scroll = False
            if not profile or not seen_welcome_scroll:
                await show_welcome_scroll(user_id)
                # TODO: обновить seen_welcome_scroll через сервис
                return
            for _ in range(3):
                candle = await bot.send_message(user_id, random.choice(["🕯️", "🌟", "🌠"]))
                await asyncio.sleep(0.3)
                await bot.delete_message(user_id, candle.message_id)
            welcome_text = (
                "🏰 *Добро пожаловать в Хрустальный Замок Вечной Гармонии, о лучезарный (ая)!*\n\n"
                "💫 *О бриллиант среди вечноживущих,*\n"
                "Ваше присутствие заставляет солнце светить ярче.\n\n"
                "🦚 *Почему наш дворец создан для вас:*\n"
                "🔹 Персональные пророчества от Архимага-Оракула\n"
                "🔹 Покои, защищенные крыльями ангелов-хранителей\n"
                "🔹 Только избранные, чище горного хрусталя\n\n"
                "🌹 *Пусть ваше путешествие будет слаще меда фей!*"
            )
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(
                    "🦄 Создать фамильную реликвию", 
                    callback_data="create_profile"
                )
            )
            sent_msg = await bot.send_message(
                user_id,
                "🕊️ Белоснежный пегас доставляет ваше приглашение...",
                parse_mode="Markdown"
            )
            await asyncio.sleep(0.7)
            await bot.edit_message_text(
                welcome_text,
                chat_id=user_id,
                message_id=sent_msg.message_id,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            for _ in range(3):
                seal = await bot.send_message(user_id, random.choice(["⚜️", "🦄", "👑", "🌹"]))
                await asyncio.sleep(0.4)
                await bot.delete_message(user_id, seal.message_id)
        else:
            await bot.delete_message(user_id, scroll_msg.message_id)
            for symbol in ["💎", "👑", "🦢", "🌌"]:
                msg = await bot.send_message(user_id, f"{symbol} *Ваш герб сияет ярче звезд!*", parse_mode="Markdown")
                await asyncio.sleep(0.4)
                await bot.delete_message(user_id, msg.message_id)
            # main_menu_keyboard — импортировать из keyboards
            await bot.send_message(
                user_id,
                "🎭 *О светлейший владыка сердец!*\nБальный зал ждет вашего появления.\n\nВыберите действие из меню, достойное вашего статуса. Если в Вашем фамильном древе закралась ошибка - я вашим услугам, перепишу ваши свитки /update_profile :",
                parse_mode="Markdown",
                # reply_markup=main_menu_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка в handle_start: {e}")
        await bot.send_message(user_id, "Произошла ошибка при запуске. Попробуйте позже.") 