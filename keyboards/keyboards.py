from telebot import types

# Главная клавиатура меню
main_menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_keyboard.add(
    types.KeyboardButton("Мой профиль"),
    types.KeyboardButton("Найти пару"),
    types.KeyboardButton("Настройки"),
    types.KeyboardButton("📍Где Вы @apbabpa_bot"),
    types.KeyboardButton("Анализ опросов")  # Новая кнопка
)

# Клавиатура выбора пола
gender_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
gender_keyboard.add(
    types.KeyboardButton("Мужской"),
    types.KeyboardButton("Женский"),
    # TODO: добавить "Любой" если потребуется
)

# Клавиатура выбора предпочитаемого пола
preferred_gender_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
preferred_gender_keyboard.add(
    types.KeyboardButton("Мужской"),
    types.KeyboardButton("Женский"),
    # TODO: добавить "Любой" если потребуется
)

# Клавиатура управления видимостью профиля
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
# Используйте visibility_keyboard в хендлерах для управления видимостью полей профиля

# TODO: добавить другие клавиатуры по мере необходимости 