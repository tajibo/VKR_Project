# bot/handlers/feedback.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from db.database import SessionLocal
from db.models import User, UserFeedback, ErrorLog
from bot.handlers.utils import log_activity

@log_activity("request_feedback")
async def request_feedback(update: Update, context: CallbackContext) -> None:
    """
    Вызывается после того, как бот ответил на запрос пользователя.
    Отправляет Inline-клавиатуру с кнопками «👍 Полезно» и «👎 Не помогло».
    """
    # Предполагаем, что update.message уже содержит текст ответа бота,
    # и мы вызываем этот хендлер через context.bot.send_message(..., reply_markup=markup)
    keyboard = [
        [
            InlineKeyboardButton("👍 Полезно", callback_data="like"),
            InlineKeyboardButton("👎 Не помогло", callback_data="dislike"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Оцените, пожалуйста, полезность ответа:", reply_markup=markup)


@log_activity("process_feedback")
async def process_feedback(update: Update, context: CallbackContext) -> None:
    """
    Обрабатывает нажатие на Inline-кнопку «👍» или «👎». 
    Сохраняет рейтинг и (опционально) комментарий.
    """
    query = update.callback_query
    user_id_telegram = query.from_user.id
    rating = 1 if query.data == "like" else 0

    # Предположим, что исходный запрос пользователя можно получить из reply_to_message:
    original_query_text = ""
    if query.message and query.message.reply_to_message:
        original_query_text = query.message.reply_to_message.text

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await query.answer("Сначала зарегистрируйтесь через /start.", show_alert=True)
            return

        fb = UserFeedback(
            user_id=db_user.id,
            query_text=original_query_text,
            rating=rating,
            comment=None
        )
        db.add(fb)
        db.commit()

        await query.answer("Спасибо за ваш отзыв!", show_alert=False)
    except Exception as e:
        err_db = SessionLocal()
        err_db.add(ErrorLog(
            user_id=db_user.id if db_user else None,
            handler_name="process_feedback",
            error_text=str(e)
        ))
        err_db.commit()
        err_db.close()
        await query.answer("Не удалось сохранить отзыв. Попробуйте позже.", show_alert=True)
    finally:
        db.close()
