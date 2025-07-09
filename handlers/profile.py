import asyncio
from telebot import types
from services.profile_service import ProfileService
import logging

logger = logging.getLogger(__name__)

# Импортируй keyboards, когда они будут вынесены
from keyboards.keyboards import gender_keyboard, preferred_gender_keyboard, main_menu_keyboard
from texts.texts import WELCOME_TEXT, WELCOME_SCROLL
# TODO: импортировать остальные тексты и клавиатуры по мере необходимости
from datetime import datetime
from utils.state_service import StateService

# Все функции теперь принимают state_service вместо user_data

async def cmd_update_profile(bot, message, profile_service: ProfileService, state_service: StateService):
    user_id = message.from_user.id
    chat_id = message.chat.id
    try:
        logger.info(f"Пользователь {user_id} начал обновление профиля.")
        scroll_msg = await bot.send_message(
            chat_id,
            "📜 *Свиток анкеты разворачивается...*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
        await bot.edit_message_text(
            "✍️ *Перо окунается в чернила...*",
            chat_id=chat_id,
            message_id=scroll_msg.message_id,
            parse_mode="Markdown"
        )
        await asyncio.sleep(1)
        await bot.delete_message(chat_id, scroll_msg.message_id)
        await bot.send_message(
            user_id,
            "🖋️ Пожалуйста, введите ваше имя:",
            reply_markup=types.ForceReply()
        )
        # Сохраняем состояние пользователя через state_service
        state_service.set_user_state(user_id, {"step": "waiting_for_name", "registration": True})
    except Exception as e:
        logger.error(f"Ошибка в cmd_update_profile: {e}")
        await bot.send_message(user_id, "Пожалуйста, введите ваше имя:")

async def handle_name_input(bot, message, profile_service: ProfileService, state_service: StateService):
    user_id = message.from_user.id
    name = message.text.strip()
    try:
        # Анимация записи имени
        writing_steps = [
            f"🕊️ *Драгоценный(ая) {name}, феи уже шепчут ваше имя на утреннем ветерке...*",
            f"📜 *Мудрые эльф-писцы выводят «{name}» серебряными чернилами...*",
            f"✨ *Хрустальный свиток трепещет от счастья, принимая ваше имя...*"
        ]
        writing_msg = await bot.send_message(
            user_id, 
            writing_steps[0],
            parse_mode="Markdown"
        )
        for step in writing_steps[1:]:
            await asyncio.sleep(1.2)
            await bot.edit_message_text(
                step,
                chat_id=user_id,
                message_id=writing_msg.message_id,
                parse_mode="Markdown"
            )
        if await profile_service.update_profile(user_id, {"name": name}):
            await bot.edit_message_text(
                f"💎 *«{name}» - имя достойное королевской крови!*\n\n🦢 *Теперь перо судьбы замерло в ожидании...*",
                chat_id=user_id,
                message_id=writing_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            # gender_keyboard — импортировать из keyboards
            await bot.send_message(
                user_id,
                "🌹 *О, прекраснейший(ая) из вечноблаженствующих!*\nВаш пол Мужской или Женский, каков ваш гендер?\n\n*Выберите вариант ниже , драгоценный (ая):*",
                parse_mode="Markdown",
                # reply_markup=gender_keyboard
            )
            # Обновляем шаг пользователя через state_service
            state = state_service.get_user_state(user_id)
            state["step"] = "waiting_for_gender"
            state_service.set_user_state(user_id, state)
        else:
            await bot.edit_message_text(
                f"💔 *О, светлейший(ая) {name}!\nЧернильные феи уронили хрустальный флакон...\n\n✨ *Не тревожьтесь!* Просто впишите своё имя ещё раз:",
                chat_id=user_id,
                message_id=writing_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            await bot.send_message(
                user_id,
                "🖋️ *Попробуйте снова, драгоценный(ая):*",
                parse_mode="Markdown",
                reply_markup=types.ForceReply()
            )
    except Exception as e:
        logger.error(f"Ошибка в ритуале именования: {e}")
        await bot.send_message(
            user_id,
            "🌪️ *О, бриллиант среди людей!*\nВолшебный вихрь помешал нам сохранить ваше имя...\n\n🕊️ *Позвольте попросить вас написать его ещё раз:*",
            parse_mode="Markdown",
            reply_markup=types.ForceReply()
        ) 

async def handle_gender_input(bot, message, profile_service: ProfileService, state_service: StateService):
    user_id = message.from_user.id
    chat_id = message.chat.id
    gender = message.text
    try:
        if gender not in ["Мужской", "Женский"]:
            wrong_msg = await bot.send_message(
                chat_id,
                "⚔️ *Рыцарь-хранитель хмурится:*\n🚫 Такого варианта нет в древних свитках!",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.edit_message_text(
                "❌ Пожалуйста, выберите пол из предложенных вариантов:",
                chat_id=chat_id,
                message_id=wrong_msg.message_id
            )
            return
        check_msg = await bot.send_message(
            chat_id,
            f"🔮 *Магический кристалл проверяет выбранный пол: {gender}...*",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)
        if await profile_service.update_profile(user_id, {"gender": gender}):
            await bot.edit_message_text(
                f"✅ *{gender} пол запечатан королевской печатью!*\n🌙 Теперь он навеки сохранен в архивах Гильдии",
                chat_id=chat_id,
                message_id=check_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.delete_message(chat_id, check_msg.message_id)
            age_msg = await bot.send_message(
                chat_id,
                "🧙 *Мудрец-хронолог вопрошает:*\n⌛ **Сколько зим вы видели, благородный искатель?**\n\n_Укажите ваш возраст цифрами (от 18 до 99)_\n✨ Вы увидите только тех, кто ищет ваш возраст",
                parse_mode="Markdown"
            )
            # Обновляем шаг пользователя через state_service
            state = state_service.get_user_state(user_id)
            state["step"] = "waiting_for_age"
            state_service.set_user_state(user_id, state)
            state["age_msg_id"] = age_msg.message_id
        else:
            await bot.edit_message_text(
                "💥 *Чернила внезапно воспламенились!*\n❌ Не удалось сохранить пол",
                chat_id=chat_id,
                message_id=check_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.send_message(
                chat_id,
                "Попробуйте выбрать пол снова:",
                # reply_markup=gender_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка в handle_gender_input: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при выборе пола.")

async def handle_age_input(bot, message, profile_service: ProfileService, state_service: StateService):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    try:
        if not text.isdigit():
            wrong_msg = await bot.send_message(
                chat_id,
                "📜 *Мудрец-каллиграф разглядывает ваши символы:*\n✖️ Это не похоже на цифры из королевских архивов!",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.edit_message_text(
                "❌ Возраст должен быть числом, благородный странник.",
                chat_id=chat_id,
                message_id=wrong_msg.message_id
            )
            return
        age = int(text)
        if not (18 <= age <= 99):
            scroll_msg = await bot.send_message(
                chat_id,
                f"🧙 *Хранитель времени разворачивает древний свиток:*\n⏳ Ваши {age} зим выходят за пределы дозволенного...",
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.edit_message_text(
                "❌ Возраст должен быть от 18 до 99 лет, согласно уставу Гильдии.",
                chat_id=chat_id,
                message_id=scroll_msg.message_id
            )
            return
        record_msg = await bot.send_message(
            chat_id,
            f"📖 *Писарь короля записывает в книгу судеб:*\n✍️ Возраст {age} зим заносится в анналы...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)
        if await profile_service.update_profile(user_id, {"age": age}):
            await bot.edit_message_text(
                f"✅ *{age} зим запечатлено золотыми чернилами!*\n🔒 Теперь он хранится в королевской библиотеке",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.delete_message(chat_id, record_msg.message_id)
            pref_msg = await bot.send_message(
                chat_id,
                "🎯 *Лучник-картограф вопрошает ....:*\n🏹 **В каком диапазоне искать Вам достойных спутников?**\n\n_О вы само благородство! Укажите предпочитаемый возраст партнера формате 'min-max' (например: 25-35)_\n✨ Ваше сиятельство вы увидите только тех, чьи предпочтения совпадают с вашим возрастом",
                parse_mode="Markdown"
            )
            # Обновляем шаг пользователя через state_service
            state = state_service.get_user_state(user_id)
            state["step"] = "waiting_for_preferred_age"
            state_service.set_user_state(user_id, state)
            state["pref_msg_id"] = pref_msg.message_id
        else:
            await bot.edit_message_text(
                "💥 *Чернильное пятно испортило пергамент!*\n❌ Не удалось сохранить возраст в архивах",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.send_message(
                chat_id,
                "Попробуйте ввести возраст снова:"
            )
    except Exception as e:
        logger.error(f"Ошибка в handle_age_input: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при вводе возраста.")

async def handle_preferred_age_input(bot, message, profile_service: ProfileService, state_service: StateService):
    user_id = message.from_user.id
    chat_id = message.chat.id
    text = message.text
    try:
        if "-" not in text:
            scroll = await bot.send_message(
                chat_id,
                "📜 *Мудрец-хронолог разворачивает древний свиток:*\n✖️ *Запись нарушает устав Гильдии!*\n\n🔮 Используйте формат «min-max» (пример: 25-35)",
                parse_mode="Markdown"
            )
            await asyncio.sleep(2)
            await bot.edit_message_text(
                "📛 Введите диапазон в формате «min-max»:",
                chat_id=chat_id,
                message_id=scroll.message_id
            )
            return
        min_age, max_age = map(int, text.split("-"))
        if min_age >= max_age or min_age < 18 or max_age > 100:
            await bot.send_message(
                chat_id,
                "⚔️ Минимальный возраст должен быть меньше максимального и в диапазоне 18-100!"
            )
            return
        record_msg = await bot.send_message(
            chat_id,
            f"📖 *Писарь короля записывает в книгу судеб:*\n✍️ Диапазон {min_age}-{max_age} зим заносится в анналы...",
            parse_mode="Markdown"
        )
        await asyncio.sleep(1.5)
        if await profile_service.update_profile(user_id, {"preferred_age_range": [min_age, max_age]}):
            await bot.edit_message_text(
                f"✅ *Диапазон {min_age}-{max_age} зим скреплен печатью!*\n🔒 Теперь он хранится в королевской библиотеке",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1)
            await bot.delete_message(chat_id, record_msg.message_id)
            await bot.send_message(
                chat_id,
                "🔮 *Оракул Гильдии вопрошает:*\n✨ **Кого ищет ваше сердце?**\n\n_Выберите предпочитаемый пол из свитка_",
                parse_mode="Markdown",
                # reply_markup=preferred_gender_keyboard
            )
            # Обновляем шаг пользователя через state_service
            state = state_service.get_user_state(user_id)
            state["step"] = "waiting_for_preferred_gender"
            state_service.set_user_state(user_id, state)
        else:
            await bot.edit_message_text(
                "💥 *Чернильное пятно испортило пергамент!*\n❌ Не удалось сохранить диапазон в архивах",
                chat_id=chat_id,
                message_id=record_msg.message_id,
                parse_mode="Markdown"
            )
            await asyncio.sleep(1.5)
            await bot.send_message(
                chat_id,
                "Попробуйте ввести диапазон снова:",
                reply_markup=types.ForceReply()
            )
    except Exception as e:
        logger.error(f"Ошибка в handle_preferred_age_input: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при вводе диапазона.")

async def handle_preferred_gender_input(bot, message, profile_service: ProfileService, state_service: StateService):
    user_id = message.from_user.id
    chat_id = message.chat.id
    gender = message.text
    try:
        if gender not in ["Мужской", "Женский", "Любой"]:
            await bot.send_message(
                chat_id,
                "❌ Пожалуйста, выберите пол из предложенных вариантов.",
                # reply_markup=preferred_gender_keyboard
            )
            return
        if await profile_service.update_profile(user_id, {"preferred_gender": gender, "preferences.gender": gender, "last_modified": datetime.now(), "is_completed": True}):
            await bot.send_message(
                chat_id,
                f"✅ Предпочитаемый пол сохранён: {gender}",
                # reply_markup=main_menu_keyboard
            )
            # Сбрасываем состояние пользователя через state_service
            state_service.clear_user_state(user_id)
        else:
            await bot.send_message(
                chat_id,
                "⚠️ Настройки не изменились (возможно, вы выбрали тот же пол)",
                # reply_markup=main_menu_keyboard
            )
    except Exception as e:
        logger.error(f"Ошибка в handle_preferred_gender_input: {e}")
        await bot.send_message(chat_id, "Произошла ошибка при выборе предпочитаемого пола.")

async def show_profile(bot, user_id, profile_service: ProfileService, is_owner=False):
    try:
        profile = await profile_service.get_profile(user_id)
        if profile:
            visibility = profile.get("visibility", {
                "name": True,
                "age": True,
                "gender": True,
                "city": True,
                "email": True,
                "photo_url": True,
                "social_links": True,
                "interests": True,
                "phone": True
            })
            profile_message = "👤 Ваш изумительно прекрасный профиль:\n" if is_owner else "👤 Профиль пользователя:\n"
            # TODO: доработать форматирование профиля, добавить новые поля, учесть видимость
            if is_owner or visibility.get("name", True):
                profile_message += f"🔁Имя: {profile.get('name', 'Не указано')}\n"
            if is_owner or visibility.get("age", True):
                profile_message += f"🔁Возраст: {profile.get('age', 'Не указан')}\n"
            if is_owner or visibility.get("gender", True):
                profile_message += f"🔁Гендер: {profile.get('gender', 'Не указан')}\n"
            if is_owner or visibility.get("city", True):
                profile_message += f"Город: {profile.get('city', 'Не указан')}\n"
            if is_owner or visibility.get("preferred_age_range", True):
                profile_message += f"Предпочитаемый возраст: {profile.get('preferred_age_range', 'Не указан')}\n"
            if is_owner or visibility.get("preferences", True):
                profile_message += f"Предпочитаемый гендер: {profile.get('preferences', {}).get('gender', 'Не указан')}\n"
            if is_owner or visibility.get("email", True):
                profile_message += f"Email: {profile.get('email', 'Не указан')}\n"
            if is_owner or visibility.get("photo_url", True):
                profile_message += f"URL: {profile.get('photo_url', 'Не указан')}\n"
            if is_owner or visibility.get("social_links", True):
                profile_message += f"Соцсети: {profile.get('social_links', 'Не указаны')}\n"
            if is_owner or visibility.get("interests", True):
                profile_message += f"Интересы: {profile.get('interests', 'Не указаны')}\n"
            if is_owner or visibility.get("phone", True):
                profile_message += f"Телефон: {profile.get('phone', 'Не указан')}\n"
            await bot.send_message(user_id, profile_message)
        else:
            await bot.send_message(user_id, "❌ Профиль не найден. Сначала заполните профиль.")
    except Exception as e:
        logger.error(f"Ошибка при отображении профиля: {e}", exc_info=True)
        await bot.send_message(user_id, "❌ Произошла ошибка при загрузке профиля.")
# TODO: доработать show_profile для интеграции с сервисом и новыми текстами

async def reset_profile(bot, user_id, profile_service: ProfileService):
    try:
        await profile_service.update_profile(user_id, {
            "name": None,
            "age": None,
            "gender": None,
            "city": None,
            "photo_url": None,
            "preferences": {
                "gender": "Любой",
                "preferred_city": "",
                "preferred_keyword": ""
            },
            "visibility": {
                "name": True,
                "age": True,
                "gender": True,
                "city": True,
                "email": False,
                "photo_url": False,
                "social_links": False,
                "interests": False,
                "phone": False
            }
        })
        await bot.send_message(user_id, "✅ Все настройки сброшены!")
        await show_profile(bot, user_id, profile_service, is_owner=True)
    except Exception as e:
        logger.error(f"Ошибка сброса профиля: {e}")
        await bot.send_message(user_id, "❌ Ошибка сброса профиля.")

async def handle_visibility_settings(bot, user_id, profile_service: ProfileService):
    try:
        profile = await profile_service.get_profile(user_id)
        if not profile:
            await bot.send_message(user_id, "❌ Профиль не найден.")
            return
        visibility = profile.get("visibility", {
            "name": True,
            "age": True,
            "gender": True,
            "city": True,
            "email": True,
            "photo_url": True,
            "social_links": True,
            "interests": True,
            "phone": True
        })
        visibility_status = "👀 Текущая видимость полей:\n"
        for field, is_visible in visibility.items():
            status = "🟢 Видимо" if is_visible else "🔴 Скрыто"
            visibility_status += f"{field.capitalize()}: {status}\n"
        # visibility_keyboard — импортировать из keyboards
        await bot.send_message(user_id, visibility_status) #, reply_markup=visibility_keyboard)
    except Exception as e:
        logger.error(f"Ошибка при отображении настроек видимости: {e}", exc_info=True)
        await bot.send_message(user_id, "❌ Произошла ошибка при загрузке настроек видимости.") 