# bot/handlers/feedback.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.database import SessionLocal
from db.models import User, UserFeedback, ErrorLog
from bot.handlers.utils import log_activity

@log_activity("request_feedback")
async def request_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Отправляет Inline-клавиатуру с кнопками «👍 Полезно» и «👎 Не помогло».
    """
    keyboard = [
        [
            InlineKeyboardButton("👍 Полезно", callback_data="like"),
            InlineKeyboardButton("👎 Не помогло", callback_data="dislike"),
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Оцените, пожалуйста, полезность ответа:", reply_markup=markup)
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Оцените, пожалуйста, полезность ответа:",
            reply_markup=markup
        )

@log_activity("process_feedback")
async def process_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обрабатывает нажатие на кнопку «👍» или «👎» и сохраняет отзыв в БД.
    """
    query = update.callback_query
    await query.answer()

    user_id_telegram = query.from_user.id
    rating = 1 if query.data == "like" else 0

    original_query_text = None
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

        await query.edit_message_text("Спасибо за ваш отзыв! 👍")

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="process_feedback",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await query.answer("Не удалось сохранить отзыв. Попробуйте позже.", show_alert=True)

    finally:
        db.close()
