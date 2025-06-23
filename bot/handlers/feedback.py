# bot/handlers/feedback.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.database import get_db
from db.models import User, UserFeedback
from bot.handlers.utils import log_activity

@log_activity("request_feedback")
async def request_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[
        InlineKeyboardButton("👍 Полезно", callback_data="like"),
        InlineKeyboardButton("👎 Не помогло", callback_data="dislike"),
    ]]
    markup = InlineKeyboardMarkup(keyboard)
    if update.message:
        await update.message.reply_text("Оцените ответ:", reply_markup=markup)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Оцените ответ:", reply_markup=markup)

@log_activity("process_feedback")
async def process_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    rating = 1 if query.data == "like" else 0
    original = query.message.reply_to_message.text if query.message.reply_to_message else None
    user_tid = query.from_user.id

    with get_db() as db:
        db_user = db.query(User).filter(User.telegram_id == user_tid).first()
        if not db_user:
            return await query.answer("Сначала /start.", show_alert=True)
        fb = UserFeedback(user_id=db_user.id, query_text=original, rating=rating)
        db.add(fb)
        db.commit()

    await query.edit_message_text("Спасибо за отзыв!")
