# bot/handlers/settings.py

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from db.database import SessionLocal
from db.models import User, UserSetting, ErrorLog
from bot.handlers.utils import log_activity

# Состояния ConversationHandler (только изменение длины суммаризации):
CHOOSING, TYPING_SUMMARY_LENGTH = range(2)

# Текст для отмены
CANCEL_COMMAND = "Отмена"

# Клавиатура выбора опции: единственный пункт + отмена
CHOICES_KEYBOARD = [["1", CANCEL_COMMAND]]
CHOICES_MARKUP = ReplyKeyboardMarkup(CHOICES_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

@log_activity("settings_start")
async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point для /settings. Показываем текущее значение длины суммаризации и предлагаем изменить.
    """
    user_id = update.effective_user.id

    db = SessionLocal()
    try:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
        if not setting:
            setting = UserSetting(user_id=user_id)
            db.add(setting)
            db.commit()
            db.refresh(setting)

        text = (
            "<b>Ваши текущие настройки:</b>\n\n"
            f"1️⃣ Длина суммаризации: <code>{setting.default_summary_length}</code> предложений\n\n"
            "Выберите, что хотите изменить:\n"
            "1 – Изменить длину суммаризации\n\n"
            f"Или введите «{CANCEL_COMMAND}», чтобы отменить."
        )

        await update.message.reply_html(
            text,
            reply_markup=CHOICES_MARKUP,
        )
        return CHOOSING

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=user_id,
                handler_name="settings_start",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Внутренняя ошибка при работе с базой данных.")
        return ConversationHandler.END

    finally:
        db.close()


@log_activity("settings_choice")
async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обработка выбора 1 или 'Отмена'
    """
    text = update.message.text.strip()
    if text == CANCEL_COMMAND:
        await update.message.reply_text("Ок, отмена. Возвращаюсь в основное меню.", reply_markup=ReplyKeyboardRemove())
        return ConversationHandler.END

    if text == "1":
        await update.message.reply_text(
            "Укажите длину суммаризации в виде целого числа (сколько предложений выдавать):",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TYPING_SUMMARY_LENGTH

    await update.message.reply_text(
        "Пожалуйста, выберите «1», либо введите «Отмена».",
        reply_markup=CHOICES_MARKUP,
    )
    return CHOOSING


@log_activity("set_summary_length")
async def set_summary_length(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Сохранение нового значения default_summary_length.
    """
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text(
            "❌ Пожалуйста, введите целое число (например, 3):"
        )
        return TYPING_SUMMARY_LENGTH

    new_length = int(text)
    if new_length <= 0 or new_length > 20:
        await update.message.reply_text(
            "❌ Допустимый диапазон – от 1 до 20 предложений. Попробуйте ещё раз:"
        )
        return TYPING_SUMMARY_LENGTH

    db = SessionLocal()
    try:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
        if not setting:
            setting = UserSetting(user_id=user_id)
            db.add(setting)

        setting.default_summary_length = new_length
        db.commit()

        await update.message.reply_text(
            f"✅ Длина суммаризации изменена на {new_length} предложений.",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=user_id,
                handler_name="set_summary_length",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось сохранить длину. Попробуйте позже.")
    finally:
        db.close()

    return ConversationHandler.END


@log_activity("cancel_settings")
async def cancel_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Функция-отмена. Прерывает ConversationHandler.
    """
    await update.message.reply_text(
        "Ок, отмена. Возвращаюсь в основное меню.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# Регистрируем ConversationHandler — экспортируем для main.py
settings_handler = ConversationHandler(
    entry_points=[CommandHandler("settings", start_settings)],
    states={
        CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
        TYPING_SUMMARY_LENGTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_summary_length)],
    },
    fallbacks=[CommandHandler("cancel", cancel_settings)],
    allow_reentry=True,
)
