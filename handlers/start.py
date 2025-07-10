from aiogram import types, Dispatcher

def register_start_handlers(dp: Dispatcher):
    @dp.message_handler(commands=['start'])
    async def handle_start(message: types.Message):
        await message.answer("Бот успешно запущен на aiogram 2!") 