# bot/main.py

import logging
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from telegram import BotCommand, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from db.database import SessionLocal, engine, Base
from db.models import User, Role, UserSetting, ErrorLog

# Импорт всех необходимых (оставшихся) хендлеров
import bot.handlers.settings as settings
from bot.handlers.feedback import request_feedback, process_feedback
from bot.handlers.stats import stats_command, stats_global_command
from bot.handlers.files import upload_handler, list_files_handler, download_file_handler

# Импорт модуля chat
import bot.handlers.chat as chat

from bot.handlers.utils import log_activity

# ---------------- Настройка логирования ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Убедимся, что таблицы созданы ----------------
Base.metadata.create_all(bind=engine)


# ---------------- Хендлер команды /start ----------------
@log_activity("start")
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

            # Создаём настройки по умолчанию
            db_settings = UserSetting(
                user_id=db_user.id,
                pomodoro_duration=25,
                break_duration=5,
                notifications_enabled=True,
                preferred_language="ru",
                default_summary_length=3,
                deadline_notifications=True,
                flashcard_notifications=True
            )
            db.add(db_settings)
            db.commit()

            await update.message.reply_text(f"Привет, {first_name}! Вы успешно зарегистрированы ✅")
        else:
            await update.message.reply_text(f"С возвращением, {first_name}! Ваш профиль в базе.")
    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="start",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("Произошла ошибка при регистрации 🛑")
    finally:
        db.close()


# ---------------- Хендлер команды /help ----------------
@log_activity("help_command")
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Это интеллектуальный ассистент Витте.\n\n"
        "/start — регистрация и начало работы\n"
        "/help — справка по боту\n\n"
        "/settings — настройки NLP-ассистента (длина суммаризации, уведомления)\n"
        "/summarize — суммаризация текста (бот попросит прислать текст)\n\n"
        "/stats — ваша личная статистика использования бота\n"
        "/stats_global — общая статистика (только admin)\n"
        "/upload — загрузить файл\n"
        "/list_files — показать ваши файлы\n"
        "/download <имя_файла> — скачать файл\n\n"
        "/cancel — отменить текущую операцию\n\n"
        "Автор: Тажибоев Д.У."
    )
    await update.message.reply_text(text)


# ---------------- Установка списка команд ----------------
async def set_commands(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Регистрация и начало работы"),
        BotCommand("help", "Справка по боту"),
        BotCommand("settings", "Настройки NLP-ассистента"),
        BotCommand("summarize", "Суммаризация текста (бот попросит текст)"),
        BotCommand("stats", "Ваша статистика использования"),
        BotCommand("stats_global", "Общая статистика (только admin)"),
        BotCommand("upload", "Загрузить файл"),
        BotCommand("list_files", "Показать ваши файлы"),
        BotCommand("download", "Скачать файл (/download <имя_файла>)"),
        BotCommand("cancel", "Отменить текущий диалог"),
    ])


# ---------------- Точка входа ----------------
def main():
    # Токен Telegram
    TOKEN = "7542036376:AAEeWEqZUfUTboVJhw_ASZDDomMsRiwrVQA"
    if not TOKEN:
        logger.error("Токен Telegram не задан.")
        return

    # ---------------- Инициализация приложения ----------------
    application = ApplicationBuilder().token(TOKEN).build()

    # ---------------- ПОДГРУЗКА ДОOБУЧЕННОЙ МОДЕЛИ ЧАТА ----------------
    MODEL_REPO = "Dilshodbek11/ruDialoGPT-finetuned"

    from dotenv import load_dotenv
    import os

    # Загружаем переменные из .env
    load_dotenv()

    # Читаем токен Hugging Face
    HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
    if not HUGGINGFACE_TOKEN:
        raise RuntimeError("Не задана переменная HUGGINGFACE_TOKEN в окружении")

    # Загружаем токенизатор и модель с помощью HUGGINGFACE_TOKEN
    tokenizer_obj = AutoTokenizer.from_pretrained(
        MODEL_REPO,
        use_auth_token=HUGGINGFACE_TOKEN
    )
    model_obj = AutoModelForCausalLM.from_pretrained(
        MODEL_REPO,
        use_auth_token=HUGGINGFACE_TOKEN
    )

    # ---------------- Определяем устройство ----------------
    device_obj = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_obj.to(device_obj)

    # ---------------- Если pad_token не задан, ставим его равным eos_token ----------------
    if tokenizer_obj.pad_token_id is None:
        tokenizer_obj.add_special_tokens({"pad_token": tokenizer_obj.eos_token})
        model_obj.resize_token_embeddings(len(tokenizer_obj))

    # ---------------- Передаём эти объекты в модуль chat ----------------
    chat.tokenizer = tokenizer_obj
    chat.model = model_obj
    chat.device = device_obj

    # ---------------- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ----------------

    # 1) /start, /help (ваша логика)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # 2) ConversationHandler для /settings
    application.add_handler(settings.settings_handler)

    # 3) Статистика
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("stats_global", stats_global_command))

    # 4) Файловая система
    application.add_handler(upload_handler)
    application.add_handler(list_files_handler)
    application.add_handler(download_file_handler)

    # 5) Свободный чат
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat.chat_handler))

    # Универсальный /cancel (у вас будет settings.settings_handler.fallbacks[0])
    application.add_handler(CommandHandler("cancel", settings.settings_handler.fallbacks[0].callback))


    # ---------------- ХЕНДЛЕР «Свободного чата» через модель ----------------
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat.chat_handler)
    )

    # После запуска приложения задаём список команд Telegram
    application.post_init = set_commands

    logger.info("Бот запускается…")
    application.run_polling()


if __name__ == "__main__":
    main()
