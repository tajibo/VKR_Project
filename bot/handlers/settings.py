# bot/handlers/settings.py

from telegram import Update
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters, ContextTypes
from db.database import SessionLocal
from db.models import User, UserSetting

# Состояния для ConversationHandler
(
    POMODORO_DURATION,  # состояние, когда бот ждёт от пользователя новое число для Pomodoro
    BREAK_DURATION      # состояние, когда бот ждёт число для Break
) = range(2)


# --- 1) Обработчики для «разговорной» команды /set_pomodoro_duration ---

# Шаг 1: пользователь ввёл /set_pomodoro_duration → бот спрашивает, сколько минут
async def set_pomodoro_duration_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text(
                "Сначала выполните /start для регистрации."
            )
            return ConversationHandler.END

        # Спрашиваем у пользователя число для Pomodoro
        await update.message.reply_text("Пожалуйста, введите новую Pomodoro-длительность (в минутах):")
        return POMODORO_DURATION

    except Exception:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END

    finally:
        db.close()


# Шаг 2: пользователь отправил сообщение с числом → сохраняем в базу
async def set_pomodoro_duration_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text("Некорректный ввод. Пожалуйста, отправьте целое число (например, 25).")
        return POMODORO_DURATION

    minutes = int(text)
    if minutes <= 0:
        await update.message.reply_text("Минуты должны быть положительным числом. Попробуйте ещё раз.")
        return POMODORO_DURATION

    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return ConversationHandler.END

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            # Если записей нет, создаём
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=minutes,
                break_duration=5,
                notifications_enabled=True
            )
            db.add(db_settings)
        else:
            db_settings.pomodoro_duration = minutes

        db.commit()
        await update.message.reply_text(f"✅ Pomodoro-длительность установлена на {minutes} минут.")
    except Exception:
        await update.message.reply_text("Не удалось сохранить настройки. Попробуйте позже.")
    finally:
        db.close()

    return ConversationHandler.END


# Опционально: пользователь может отменить ввод
async def cancel_pomodoro_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Команда отменена.")
    return ConversationHandler.END


# --- 2) Обработчики для «разговорной» команды /set_break_duration ---

# Шаг 1: пользователь ввёл /set_break_duration → бот спрашивает число
async def set_break_duration_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return ConversationHandler.END

        await update.message.reply_text("Пожалуйста, введите новую длительность перерыва (в минутах):")
        return BREAK_DURATION

    except Exception:
        await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
        return ConversationHandler.END

    finally:
        db.close()


# Шаг 2: пользователь отправил число → сохраняем в базу
async def set_break_duration_receive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text("Некорректный ввод. Пожалуйста, отправьте целое число (например, 5).")
        return BREAK_DURATION

    minutes = int(text)
    if minutes <= 0:
        await update.message.reply_text("Минуты должны быть положительным числом. Попробуйте ещё раз.")
        return BREAK_DURATION

    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return ConversationHandler.END

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=25,
                break_duration=minutes,
                notifications_enabled=True
            )
            db.add(db_settings)
        else:
            db_settings.break_duration = minutes

        db.commit()
        await update.message.reply_text(f"✅ Break-длительность установлена на {minutes} минут.")
    except Exception:
        await update.message.reply_text("Не удалось сохранить настройки. Попробуйте позже.")
    finally:
        db.close()

    return ConversationHandler.END


async def cancel_break_duration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Команда отменена.")
    return ConversationHandler.END


# --- 3) Обычный хендлер /settings и /toggle_notifications (без диалога) ---

# /settings — показать текущие настройки
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=25,
                break_duration=5,
                notifications_enabled=True
            )
            db.add(db_settings)
            db.commit()

        state = "включены" if db_settings.notifications_enabled else "выключены"
        text = (
            f"Ваши текущие настройки:\n\n"
            f"• Pomodoro-длительность: {db_settings.pomodoro_duration} мин.\n"
            f"• Break-длительность: {db_settings.break_duration} мин.\n"
            f"• Уведомления: {state}\n\n"
            "Чтобы изменить настройку, используйте:\n"
            "/set_pomodoro_duration (чтобы задать Pomodoro-длительность)\n"
            "/set_break_duration (чтобы задать длительность перерыва)\n"
            "/toggle_notifications (чтобы включить/выключить уведомления)"
        )
        await update.message.reply_text(text)
    except Exception:
        await update.message.reply_text("Не удалось получить настройки 🛑")
    finally:
        db.close()


# /toggle_notifications — включить/выключить уведомления
async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=25,
                break_duration=5,
                notifications_enabled=False
            )
            db.add(db_settings)
        else:
            db_settings.notifications_enabled = not db_settings.notifications_enabled

        db.commit()
        state = "включены" if db_settings.notifications_enabled else "выключены"
        await update.message.reply_text(f"Уведомления {state}.")
    except Exception:
        await update.message.reply_text("Не удалось переключить уведомления 🛑")
    finally:
        db.close()
