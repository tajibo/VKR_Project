import os
import logging
from datetime import timedelta

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackContext,
)
from sqlalchemy import func  # <-- обязательно, чтобы func.now() работал

from db.database import SessionLocal, engine, Base
from db.models import User, Role, UserSetting, PomodoroSession

# ---------------- Настройка логирования ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Убедимся, что таблицы созданы ----------------
Base.metadata.create_all(bind=engine)


# ---------------- Хендлер команды /start ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_id = tg_user.id
    username = tg_user.username or ""
    first_name = tg_user.first_name or ""

    db = SessionLocal()
    try:
        # Проверяем, существует ли пользователь
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            # Если нет, проверяем, есть ли роль "user"
            default_role = db.query(Role).filter(Role.name == "user").first()
            if not default_role:
                default_role = Role(name="user")
                db.add(default_role)
                db.commit()
                db.refresh(default_role)

            # Создаём новую запись о пользователе
            db_user = User(
                telegram_id=user_id,
                username=username,
                role_id=default_role.id
            )
            db.add(db_user)
            db.commit()

            # Также сразу создаём запись в user_settings с дефолтными значениями
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=25,
                break_duration=5,
                notifications_enabled=True
            )
            db.add(db_settings)
            db.commit()

            await update.message.reply_text(
                f"Привет, {first_name}! Вы успешно зарегистрированы ✅"
            )
        else:
            await update.message.reply_text(
                f"С возвращением, {first_name}! Ваш профиль уже в базе."
            )
    except Exception as e:
        logger.error("Ошибка при работе с БД: %s", e)
        await update.message.reply_text("Произошла ошибка при регистрации 🛑")
    finally:
        db.close()


# ---------------- Хендлер команды /help ----------------
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Это интеллектуальный ассистент Витте.\n\n"
        "/start — регистрация и начало работы\n"
        "/help — справка по боту\n\n"
        "/settings — просмотр/изменение ваших настроек pomodoro\n"
        "/set_pomodoro_duration <минуты> — установить длительность работы\n"
        "/set_break_duration <минуты> — установить длительность перерыва\n"
        "/toggle_notifications — включить/выключить уведомления\n\n"
        "/start_pomodoro — начать Pomodoro-сессию\n"
        "/stop_pomodoro — остановить текущую Pomodoro-сессию\n\n"
        "Автор: Тажибоев Д.У."
    )
    await update.message.reply_text(text)


# ---------------- Хендлер команды /settings ----------------
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            # На всякий случай, если записи не оказалось (добавляем дефолт)
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=25,
                break_duration=5,
                notifications_enabled=True
            )
            db.add(db_settings)
            db.commit()

        text = (
            f"Ваши текущие настройки:\n\n"
            f"• Pomodoro-длительность: {db_settings.pomodoro_duration} мин.\n"
            f"• Break-длительность: {db_settings.break_duration} мин.\n"
            f"• Уведомления: {'включены' if db_settings.notifications_enabled else 'выключены'}\n\n"
            "Чтобы изменить настройку, используйте команды:\n"
            "/set_pomodoro_duration <минуты>\n"
            "/set_break_duration <минуты>\n"
            "/toggle_notifications"
        )
        await update.message.reply_text(text)
    except Exception as e:
        logger.error("Ошибка при получении настроек: %s", e)
        await update.message.reply_text("Не удалось получить настройки 🛑")
    finally:
        db.close()


# ---------------- Хендлер команды /set_pomodoro_duration ----------------
async def set_pomodoro_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args  # ожидаем [<минуты>]

    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Использование: /set_pomodoro_duration <целое_число_минут>")
        return

    minutes = int(args[0])
    if minutes <= 0:
        await update.message.reply_text("Пожалуйста, укажите положительное число минут.")
        return

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            # На всякий случай: если настроек не было, создаём
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
        await update.message.reply_text(f"Pomodoro-длительность установлена на {minutes} минут.")
    except Exception as e:
        logger.error("Ошибка при установке pomodoro_duration: %s", e)
        await update.message.reply_text("Не удалось изменить Pomodoro-длительность 🛑")
    finally:
        db.close()


# ---------------- Хендлер команды /set_break_duration ----------------
async def set_break_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("Использование: /set_break_duration <целое_число_минут>")
        return

    minutes = int(args[0])
    if minutes <= 0:
        await update.message.reply_text("Пожалуйста, укажите положительное число минут.")
        return

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
                break_duration=minutes,
                notifications_enabled=True
            )
            db.add(db_settings)
        else:
            db_settings.break_duration = minutes

        db.commit()
        await update.message.reply_text(f"Break-длительность установлена на {minutes} минут.")
    except Exception as e:
        logger.error("Ошибка при установке break_duration: %s", e)
        await update.message.reply_text("Не удалось изменить Break-длительность 🛑")
    finally:
        db.close()


# ---------------- Хендлер команды /toggle_notifications ----------------
async def toggle_notifications(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        status = "включены" if db_settings.notifications_enabled else "выключены"
        await update.message.reply_text(f"Уведомления {status}.")
    except Exception as e:
        logger.error("Ошибка при переключении уведомлений: %s", e)
        await update.message.reply_text("Не удалось переключить уведомления 🛑")
    finally:
        db.close()


# ---------------- Помощник для завершения Pomodoro ----------------
async def pomodoro_complete_callback(context: CallbackContext) -> None:
    """
    Этот коллбэк вызывается JobQueue по истечении pomodoro_duration минут.
    Отправляет сообщение пользователю и обновляет статус сессии в БД.
    """
    job_data = context.job.data  # хранит { "telegram_id": <id>, "session_id": <id> }
    telegram_id = job_data["telegram_id"]
    session_id = job_data["session_id"]

    # Обновляем запись в БД: ставим status="complete" и устанавливаем end_time
    db = SessionLocal()
    try:
        session = db.query(PomodoroSession).filter(PomodoroSession.id == session_id).first()
        if session and session.status == "start":
            session.status = "complete"
            session.end_time = func.now()
            db.commit()
    except Exception as e:
        logger.error("Ошибка при обновлении PomodoroSession: %s", e)
    finally:
        db.close()

    # Отправляем сообщение пользователю
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="⏰ Pomodoro завершён! Пора сделать перерыв."
        )
    except Exception as e:
        logger.error("Не удалось отправить сообщение о завершении Pomodoro: %s", e)


# ---------------- Хендлер команды /start_pomodoro ----------------
async def start_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            await update.message.reply_text("Сначала выполните /settings для инициализации.")
            return

        # Создаём новую PomodoroSession со статусом "start"
        new_session = PomodoroSession(
            user_id=db_user.id,
            status="start"
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # Планируем Job через pomodoro_duration минут
        # Важно: берём job_queue из application, а не из context.job_queue
        context.application.job_queue.run_once(
            pomodoro_complete_callback,
            when=db_settings.pomodoro_duration * 60,  # в секундах
            data={
                "telegram_id": user_id,
                "session_id": new_session.id
            }
        )

        await update.message.reply_text(
            f"✅ Pomodoro запущён на {db_settings.pomodoro_duration} минут. Успешной работы!"
        )
    except Exception as e:
        logger.error("Ошибка при запуске Pomodoro: %s", e)
        await update.message.reply_text("Не удалось запустить Pomodoro 🛑")
    finally:
        db.close()


# ---------------- Хендлер команды /stop_pomodoro ----------------
async def stop_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        # Находим последнюю сессию со статусом "start"
        session = (
            db.query(PomodoroSession)
            .filter(PomodoroSession.user_id == db_user.id, PomodoroSession.status == "start")
            .order_by(PomodoroSession.start_time.desc())
            .first()
        )
        if not session:
            await update.message.reply_text("Нет активной Pomodoro-сессии для остановки.")
            return

        session.status = "stopped"
        session.end_time = func.now()
        db.commit()

        await update.message.reply_text("⏹ Pomodoro остановлен досрочно.")
    except Exception as e:
        logger.error("Ошибка при остановке Pomodoro: %s", e)
        await update.message.reply_text("Не удалось остановить Pomodoro 🛑")
    finally:
        db.close()


# ---------------- Установка списка команд ----------------
async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Регистрация и начало работы"),
        BotCommand("help", "Справка по боту"),
        BotCommand("settings", "Просмотр/изменение настроек Pomodoro"),
        BotCommand("set_pomodoro_duration", "Установить длительность Pomodoro (мин.)"),
        BotCommand("set_break_duration", "Установить длительность перерыва (мин.)"),
        BotCommand("toggle_notifications", "Включить/выключить уведомления"),
        BotCommand("start_pomodoro", "Запустить Pomodoro-сессию"),
        BotCommand("stop_pomodoro", "Остановить текущую Pomodoro-сессию"),
    ])


# ---------------- Точка входа ----------------
def main():
    # Жестко захардкодим токен (ваш настоящий токен)
    TOKEN = "7542036376:AAEeWEqZUfUTboVJhw_ASZDDomMsRiwrVQA"

    print(">>> TELEGRAM_TOKEN =", TOKEN)

    if not TOKEN:
        logger.error("Токен не задан.")
        return

    # Строим приложение Telegram Bot
    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("set_pomodoro_duration", set_pomodoro_duration))
    application.add_handler(CommandHandler("set_break_duration", set_break_duration))
    application.add_handler(CommandHandler("toggle_notifications", toggle_notifications))
    application.add_handler(CommandHandler("start_pomodoro", start_pomodoro))
    application.add_handler(CommandHandler("stop_pomodoro", stop_pomodoro))

    # После запуска приложения установим список команд в Telegram
    application.post_init = set_commands

    logger.info("Бот запускается…")
    application.run_polling()


if __name__ == "__main__":
    main()
