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

# TODO: добавить другие клавиатуры по мере необходимости 