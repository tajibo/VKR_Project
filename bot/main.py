import os
import logging

from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from db.database import SessionLocal, engine, Base
from db.models import User, Role

# --- Логирование ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Убедимся, что таблицы созданы ---
Base.metadata.create_all(bind=engine)

# --- Обработчик команды /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_id = tg_user.id
    username = tg_user.username or ""
    first_name = tg_user.first_name or ""

    db = SessionLocal()
    try:
        # Проверяем, зарегистрирован ли уже этот telegram_id
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            # Если роли "user" нет — создаём
            default_role = db.query(Role).filter(Role.name == "user").first()
            if not default_role:
                default_role = Role(name="user")
                db.add(default_role)
                db.commit()
                db.refresh(default_role)

            # Создаём нового пользователя
            db_user = User(
                telegram_id=user_id,
                username=username,
                role_id=default_role.id
            )
            db.add(db_user)
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

# --- Обработчик команды /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Это интеллектуальный ассистент Витте.\n\n"
        "/start — регистрация и начало работы\n"
        "/help — справка по боту\n\n"
        "Автор: Иванов И.И."
    )
    await update.message.reply_text(text)

# --- Установка списка команд (будет вызвана после инициализации) ---
async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Регистрация и начало работы"),
        BotCommand("help", "Справка по боту"),
    ])

# --- Точка входа ---
def main():
    # Захардкодим токен только для упрощённой проверки.
    # Вставьте сюда именно тот токен, который дал вам BotFather:
    TOKEN = "7542036376:AAEeWEqZUfUTboVJhw_ASZDDomMsRiwrVQA"
    print(">>> TELEGRAM_TOKEN =", TOKEN)

    if not TOKEN or TOKEN.startswith("ВАШ_"):
        logger.error("Токен не задан или некорректен.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Регистрируем хендлеры
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Привяжем установку команд к post_init
    application.post_init = set_commands

    logger.info("Бот запускается…")
    application.run_polling()

if __name__ == "__main__":
    main()
