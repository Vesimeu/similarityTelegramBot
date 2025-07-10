from aiogram import types, Dispatcher
from keyboards.keyboards import main_menu_keyboard
from services.profile_service import get_profile, set_seen_welcome_scroll
import asyncio
import random

# Регистрируем хендлеры /start

def register_start_handlers(dp: Dispatcher):
    @dp.message_handler(commands=['start'])
    async def handle_start(message: types.Message):
        """
        Хендлер /start:
        - Анимация свитка
        - Проверка профиля через сервис
        - Показ welcome_scroll новым пользователям
        - Приветствие и главное меню для зарегистрированных
        """
        user_id = message.from_user.id
        try:
            # Анимация с волшебным свитком
            scroll_steps = [
                "🌙 *Серебристый свиток судеб нежно разворачивается...* [░░░░░░░░░░]",
                "✨ *Чернила из слез феникса проявляют узоры...* [▓▓░░░░░░░░]",
                "🦢 *Перо ангела выводит ваше имя золотом...* [▓▓▓▓▓░░░░░]",
                "🔮 *Хрустальная печать застывает в воздухе...* [▓▓▓▓▓▓▓▓░░]",
                "💎 *Готово, о драгоценнейший!* [▓▓▓▓▓▓▓▓▓▓]"
            ]
            scroll_msg = await message.answer(scroll_steps[0], parse_mode="Markdown")
            for step in scroll_steps[1:]:
                await asyncio.sleep(0.5)
                await message.bot.edit_message_text(
                    step,
                    chat_id=user_id,
                    message_id=scroll_msg.message_id,
                    parse_mode="Markdown"
                )

            # Проверка профиля через сервис
            profile = await get_profile(user_id)

            if not profile or not profile.get("is_completed", False):
                await message.bot.delete_message(user_id, scroll_msg.message_id)
                # Новый пользователь — показываем welcome_scroll
                if not profile or not profile.get("seen_welcome_scroll", False):
                    await show_welcome_scroll(message)
                    await set_seen_welcome_scroll(user_id)
                    return
                # Эффекты для возвратившихся
                for _ in range(3):
                    candle = await message.answer(random.choice(["🕯️", "🌟", "🌠"]))
                    await asyncio.sleep(0.3)
                    await message.bot.delete_message(user_id, candle.message_id)
                # Приветствие и кнопка создания профиля
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
                sent_msg = await message.answer(
                    "🕊️ Белоснежный пегас доставляет ваше приглашение...",
                    parse_mode="Markdown"
                )
                await asyncio.sleep(0.7)
                await message.bot.edit_message_text(
                    welcome_text,
                    chat_id=user_id,
                    message_id=sent_msg.message_id,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                for _ in range(3):
                    seal = await message.answer(random.choice(["⚜️", "🦄", "👑", "🌹"]))
                    await asyncio.sleep(0.4)
                    await message.bot.delete_message(user_id, seal.message_id)
            else:
                # Для зарегистрированных пользователей
                await message.bot.delete_message(user_id, scroll_msg.message_id)
                for symbol in ["💎", "👑", "🦢", "🌌"]:
                    msg = await message.answer(f"{symbol} *Ваш герб сияет ярче звезд!*", parse_mode="Markdown")
                    await asyncio.sleep(0.4)
                    await message.bot.delete_message(user_id, msg.message_id)
                await message.answer(
                    "🎭 *О светлейший владыка сердец!*\nБальный зал ждет вашего появления.\n\n"
                    "Выберите действие из меню, достойное вашего статуса. "
                    "Если в Вашем фамильном древе закралась ошибка - я вашим услугам, перепишу ваши свитки /update_profile :",
                    parse_mode="Markdown",
                    reply_markup=main_menu_keyboard
                )
        except Exception as e:
            await message.answer("Произошла ошибка при запуске. Попробуйте позже.")

async def show_welcome_scroll(message: types.Message):
    """
    Отправляет приветственный свиток новым пользователям
    """
    scroll_text = """
✨ *Хрустальный Манускрипт Благородного Общества* ✨

   🦚 *О, сияющий алмаз в оправе нашего собрания!*  🦚

🌸 *Бот специализирован на том , что на основе ваших ответов,*  
🌸 *подбирает близкого по духу, человека:*
🌸 *Для этого нужно ответить на несколько вопросов в @apbaabpa,*
🌸 *Очень важно отметить свою геопозицию 📍@apbabpa_bot,*
🌸 *Чтобы посмотреть результаты нужно пройти регистрацию ниже:*

༺ *Священные Заповеди для Благородных Душ* ༻

▸ Зарегистрируйтесь здесь , введите пол,возраст
▸ далее отвечайте на вопросы в группе @apbaabpa
▸ далее по команде /analyze  смотрите результат

💎 *Привилегии для столь блистательной особы:*
- Персональные рекомендации от придворного оракула
- Только достойнейшие из достойных
- Защита крыльями ангелов-хранителей

🌹 *Как удостоиться чести беседы:*
1. Создать фамильный герб (анкету)
2. Обменяться драгоценными речами в @dveoo
3. Посетить Бальный Зал @apbaabpa


🦢 *Пусть феи удачи осыпают вас лепестками сакуры!* 🦢
"""
    scroll_parts = [
        "💌 *Письмо с золотой каймой медленно парит в воздухе...*",
        "🕊️ *Голубь преклоняется перед вашим величием...*",
        "🌹 *Невидимые пажи целуют край свитка...*",
        "👑 *Ваше имя выгравировано на хрустальной пластине...*",
        scroll_text
    ]
    for part in scroll_parts:
        msg = await message.answer(part, parse_mode="Markdown")
        await asyncio.sleep(0.7)
        await message.bot.delete_message(message.chat.id, msg.message_id)
    await message.answer(scroll_text, parse_mode="Markdown") 