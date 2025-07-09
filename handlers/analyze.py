import logging
import asyncio
from services.poll_service import PollService

logger = logging.getLogger(__name__)

async def handle_analyze(bot, message, poll_service: PollService):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        logger.info(f"Начало обработки анализа для пользователя {user_id}")
        progress_msg = await bot.reply_to(message, "⏳ Анализируем ваши совпадения...")
        eligible, msg = await asyncio.wait_for(poll_service.check_eligible(user_id), timeout=10.0)
        if not eligible:
            await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=msg)
            logger.info("Пользователь не прошел проверку eligibility")
            return
        report = await asyncio.wait_for(poll_service.generate_report(user_id), timeout=30.0)
        if not report.strip():
            logger.error("Получен пустой отчет")
            raise ValueError("Пустой отчет")
        if len(report) > 4000:
            await bot.delete_message(chat_id=chat_id, message_id=progress_msg.message_id)
            parts = [report[i:i+4000] for i in range(0, len(report), 4000)]
            for part in parts:
                await bot.send_message(chat_id, part, parse_mode='HTML')
        else:
            await bot.edit_message_text(chat_id=chat_id, message_id=progress_msg.message_id, text=report, parse_mode='HTML')
        logger.info(f"Анализ для {user_id} успешно завершен")
    except asyncio.TimeoutError:
        logger.error("Таймаут при анализе")
        await bot.reply_to(message, "⚠️ Анализ занял слишком много времени. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Ошибка в handle_analyze: {e}")
        await bot.reply_to(message, "⚠️ Произошла ошибка при формировании отчета") 