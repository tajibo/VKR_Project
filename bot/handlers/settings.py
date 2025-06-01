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

# Состояния ConversationHandler (без смены языка):
# 0 – выбор (CHOOSING), 1 – ввод длины, 2 – дедлайны, 3 – карточки
CHOOSING, TYPING_SUMMARY_LENGTH, TYPING_DEADLINE, TYPING_FLASH = range(4)

# Текст для отмены
CANCEL_COMMAND = "Отмена"

# Клавиатура выбора опции: три пункта + отмена
CHOICES_KEYBOARD = [["1", "2"], ["3", CANCEL_COMMAND]]
CHOICES_MARKUP = ReplyKeyboardMarkup(CHOICES_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)

@log_activity("settings_start")
async def start_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Entry point для /settings. Показываем текущие настройки (без языка) и предлагаем выбор.
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
            f"1️⃣ Длина суммаризации: <code>{setting.default_summary_length}</code> предложений\n"
            f"2️⃣ Уведомления о дедлайнах: <code>{'включены' if setting.deadline_notifications else 'выключены'}</code>\n"
            f"3️⃣ Уведомления о карточках: <code>{'включены' if setting.flashcard_notifications else 'выключены'}</code>\n\n"
            "Выберите, что хотите изменить:\n"
            "1 – Изменить длину суммаризации\n"
            "2 – Включить/выключить уведомления о дедлайнах\n"
            "3 – Включить/выключить уведомления о карточках\n\n"
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
    Обработка выбора 1–3 или 'Отмена'
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

    if text == "2":
        await update.message.reply_text(
            "Уведомления о дедлайнах можно <b>включить</b> или <b>выключить</b>. Введите <code>Да</code> или <code>Нет</code>:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TYPING_DEADLINE

    if text == "3":
        await update.message.reply_text(
            "Уведомления о карточках можно <b>включить</b> или <b>выключить</b>. Введите <code>Да</code> или <code>Нет</code>:",
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TYPING_FLASH

    await update.message.reply_text(
        "Пожалуйста, выберите вариант из клавиатуры (1–3) или введите «Отмена».",
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


@log_activity("set_deadline_notifications")
async def set_deadline_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Включение/выключение уведомлений о дедлайнах.
    """
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if text not in {"да", "нет"}:
        await update.message.reply_text(
            "❌ Пожалуйста, введите «Да» или «Нет»:"
        )
        return TYPING_DEADLINE

    choice = True if text == "да" else False

    db = SessionLocal()
    try:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
        if not setting:
            setting = UserSetting(user_id=user_id)
            db.add(setting)

        setting.deadline_notifications = choice
        db.commit()

        status = "включены" if choice else "выключены"
        await update.message.reply_text(
            f"✅ Уведомления о дедлайнах теперь {status}.",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=user_id,
                handler_name="set_deadline_notifications",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось сохранить настройку. Попробуйте позже.")
    finally:
        db.close()

    return ConversationHandler.END


@log_activity("set_flashcard_notifications")
async def set_flashcard_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Включение/выключение уведомлений о карточках.
    """
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()

    if text not in {"да", "нет"}:
        await update.message.reply_text(
            "❌ Пожалуйста, введите «Да» или «Нет»:"
        )
        return TYPING_FLASH

    choice = True if text == "да" else False

    db = SessionLocal()
    try:
        setting = db.query(UserSetting).filter(UserSetting.user_id == user_id).first()
        if not setting:
            setting = UserSetting(user_id=user_id)
            db.add(setting)

        setting.flashcard_notifications = choice
        db.commit()

        status = "включены" if choice else "выключены"
        await update.message.reply_text(
            f"✅ Уведомления о карточках теперь {status}.",
            reply_markup=ReplyKeyboardRemove(),
        )
    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=user_id,
                handler_name="set_flashcard_notifications",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось сохранить настройку. Попробуйте позже.")
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
        TYPING_DEADLINE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_deadline_notifications)],
        TYPING_FLASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_flashcard_notifications)],
    },
    fallbacks=[CommandHandler("cancel", cancel_settings)],
    allow_reentry=True,
)
