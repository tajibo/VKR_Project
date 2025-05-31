# bot/main.py

import logging

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from sqlalchemy import func

from db.database import SessionLocal, engine, Base
from db.models import User, Role, UserSetting, PomodoroSession

# Хендлеры из папки handlers
from bot.handlers.settings import (
    settings_command,
    toggle_notifications,
    set_pomodoro_duration_start,
    set_pomodoro_duration_receive,
    cancel_pomodoro_duration,
    set_break_duration_start,
    set_break_duration_receive,
    cancel_break_duration,
    POMODORO_DURATION,
    BREAK_DURATION,
)
from bot.handlers.pomodoro import (
    start_pomodoro,
    stop_pomodoro,
)

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
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            default_role = db.query(Role).filter(Role.name == "user").first()
            if not default_role:
                default_role = Role(name="user")
                db.add(default_role)
                db.commit()
                db.refresh(default_role)

            db_user = User(
                telegram_id=user_id,
                username=username,
                role_id=default_role.id
            )
            db.add(db_user)
            db.commit()

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
        "/settings — просмотр/изменение ваших настроек Pomodoro\n"
        "/set_pomodoro_duration — изменить Pomodoro-длительность (бот задаст вопрос)\n"
        "/set_break_duration — изменить длительность перерыва (бот задаст вопрос)\n"
        "/toggle_notifications — включить/выключить уведомления\n\n"
        "/start_pomodoro — начать Pomodoro-сессию\n"
        "/stop_pomodoro — остановить текущую Pomodoro-сессию\n\n"
        "Автор: Тажибоев Д.У."
    )
    await update.message.reply_text(text)


# ---------------- Установка списка команд ----------------
async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Регистрация и начало работы"),
        BotCommand("help", "Справка по боту"),
        BotCommand("settings", "Просмотр/изменение настроек Pomodoro"),
        BotCommand("set_pomodoro_duration", "Изменить Pomodoro-длительность (бот спросит)"),
        BotCommand("set_break_duration", "Изменить длительность перерыва (бот спросит)"),
        BotCommand("toggle_notifications", "Вкл/выкл уведомления"),
        BotCommand("start_pomodoro", "Запустить Pomodoro-сессию"),
        BotCommand("stop_pomodoro", "Остановить текущую Pomodoro-сессию"),
    ])


# ---------------- Точка входа ----------------
def main():
    TOKEN = "7542036376:AAEeWEqZUfUTboVJhw_ASZDDomMsRiwrVQA"
    if not TOKEN:
        logger.error("Токен не задан.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # --- Регистрация хендлеров ---

    # 1) /start и /help
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # 2) ConversationHandler для /set_pomodoro_duration
    conv_pomodoro = ConversationHandler(
        entry_points=[CommandHandler("set_pomodoro_duration", set_pomodoro_duration_start)],
        states={
            POMODORO_DURATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_pomodoro_duration_receive),
                # При желании можно добавить клавишу «Отмена»
                MessageHandler(filters.Regex("^(Отмена|cancel)$"), cancel_pomodoro_duration),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^(Отмена|cancel)$"), cancel_pomodoro_duration)],
        allow_reentry=True,
    )
    application.add_handler(conv_pomodoro)

    # 3) ConversationHandler для /set_break_duration
    conv_break = ConversationHandler(
        entry_points=[CommandHandler("set_break_duration", set_break_duration_start)],
        states={
            BREAK_DURATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_break_duration_receive),
                MessageHandler(filters.Regex("^(Отмена|cancel)$"), cancel_break_duration),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^(Отмена|cancel)$"), cancel_break_duration)],
        allow_reentry=True,
    )
    application.add_handler(conv_break)

    # 4) /settings (простое чтение)
    application.add_handler(CommandHandler("settings", settings_command))

    # 5) /toggle_notifications (мгновенное изменение)
    application.add_handler(CommandHandler("toggle_notifications", toggle_notifications))

    # 6) Pomodoro-сессии
    application.add_handler(CommandHandler("start_pomodoro", start_pomodoro))
    application.add_handler(CommandHandler("stop_pomodoro", stop_pomodoro))

    # После запуска приложения задаём список команд Telegram
    application.post_init = set_commands

    logger.info("Бот запускается…")
    application.run_polling()


if __name__ == "__main__":
    main()
