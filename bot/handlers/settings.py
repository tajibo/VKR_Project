# bot/handlers/settings.py
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters
from db.database import get_db
from db.models import UserSetting
from bot.handlers.utils import log_activity

CHOOSING, TYPING_SUMMARY_LENGTH = range(2)
CANCEL = "Отмена"
CHOICES_MARKUP = ReplyKeyboardMarkup([["1", CANCEL]], one_time_keyboard=True, resize_keyboard=True)

@log_activity("settings_start")
async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_tid = update.effective_user.id
    with get_db() as db:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user_tid).first()
        if not setting:
            setting = UserSetting(user_id=user_tid)
            db.add(setting)
            db.commit()
            db.refresh(setting)
    text = (
        f"<b>Текущая длина суммаризации:</b> {setting.default_summary_length}\n"
        "1 – Изменить длину\n"
        f"Или «{CANCEL}» для отмены."
    )
    await update.message.reply_html(text, reply_markup=CHOICES_MARKUP)
    return CHOOSING

@log_activity("settings_choice")
async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == CANCEL:
        await update.message.reply_text("Отмена.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END
    if text == "1":
        await update.message.reply_text("Введите целое число:", reply_markup=ReplyKeyboardRemove())
        return TYPING_SUMMARY_LENGTH
    await update.message.reply_text("Пожалуйста, «1» или «Отмена».", reply_markup=CHOICES_MARKUP)
    return CHOOSING

@log_activity("set_summary_length")
async def set_summary_length(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_tid = update.effective_user.id
    text = update.message.text.strip()
    if not text.isdigit() or not (1 <= int(text) <= 20):
        await update.message.reply_text("Введите число от 1 до 20:")
        return TYPING_SUMMARY_LENGTH
    new_len = int(text)
    with get_db() as db:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user_tid).first()
        setting.default_summary_length = new_len
        db.add(setting)
        db.commit()
    await update.message.reply_text(f"Длина суммаризации: {new_len}", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

@log_activity("cancel_settings")
async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

settings_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", start_settings)],
    states={
        CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
        TYPING_SUMMARY_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_summary_length)],
    },
    fallbacks=[CommandHandler("cancel", cancel_settings)],
    allow_reentry=True,
)
