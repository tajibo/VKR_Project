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

# Импорт всех необходимых хендлеров
from bot.handlers.settings import settings_handler
from bot.handlers.feedback import request_feedback, process_feedback
from bot.handlers.stats import stats_command, stats_global_command
from bot.handlers.intent import intent_handler
from bot.handlers.summarize import summarize_handler
from bot.handlers.sentiment import sentiment_handler
from bot.handlers.topics import topics_handler
from bot.handlers.extract_deadlines import extract_deadlines_handler
from bot.handlers.generate_questions import generate_questions_handler
from bot.handlers.files import upload_handler, list_files_handler, download_file_handler

# Импорт нового модуля chat
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
        "/settings — настройки NLP-ассистента (язык, длина суммаризации, уведомления)\n"
        "/intent <текст> — intent-классификация (распознаёт цель вашего запроса)\n"
        "/summarize — суммаризация текста (бот попросит прислать текст)\n"
        "/sentiment <текст> — анализ тональности (позитив/нейтрально/негативно)\n"
        "/topics — выделение тем (бот попросит прислать несколько текстов)\n"
        "/extract_deadlines — NER для дедлайнов (бот попросит текст)\n"
        "/generate_questions — генерация вопросов (бот попросит текст)\n\n"
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
        BotCommand("intent", "Intent-классификация (/intent <текст>)"),
        BotCommand("summarize", "Суммаризация текста (бот попросит текст)"),
        BotCommand("sentiment", "Анализ тональности (/sentiment <текст>)"),
        BotCommand("topics", "Выделение тем (бот попросит тексты)"),
        BotCommand("extract_deadlines", "NER для дедлайнов (бот попросит текст)"),
        BotCommand("generate_questions", "Генерация вопросов (бот попросит текст)"),
        BotCommand("stats", "Ваша статистика использования"),
        BotCommand("stats_global", "Общая статистика (только admin)"),
        BotCommand("upload", "Загрузить файл"),
        BotCommand("list_files", "Показать ваши файлы"),
        BotCommand("download", "Скачать файл (/download <имя_файла>)"),
        BotCommand("cancel", "Отменить текущий диалог"),
    ])


# ---------------- Точка входа ----------------
def main():
    TOKEN = "7542036376:AAEeWEqZUfUTboVJhw_ASZDDomMsRiwrVQA"
    if not TOKEN:
        logger.error("Токен не задан.")
        return

    # ---------------- Инициализация приложения ----------------
    application = ApplicationBuilder().token(TOKEN).build()

    # ---------------- ПОДГРУЗКА ДОOБУЧЕННОЙ МОДЕЛИ ИЗ HUGGING FACE HUB ----------------
    # Замените <ваш_username> на ваш реальный никнейм на Hugging Face
    MODEL_REPO = "ваш_username/ruDialoGPT-finetuned"

    # Загружаем токенизатор и модель
    tokenizer_obj = AutoTokenizer.from_pretrained(MODEL_REPO)
    model_obj = AutoModelForCausalLM.from_pretrained(MODEL_REPO)

    # Определяем устройство (GPU, если доступен, иначе CPU)
    device_obj = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_obj.to(device_obj)

    # Если pad_token не задан, ставим его равным eos_token
    if tokenizer_obj.pad_token_id is None:
        tokenizer_obj.add_special_tokens({"pad_token": tokenizer_obj.eos_token})
        model_obj.resize_token_embeddings(len(tokenizer_obj))

    # Передаём эти объекты в модуль chat
    chat.tokenizer = tokenizer_obj
    chat.model = model_obj
    chat.device = device_obj

    # ---------------- РЕГИСТРАЦИЯ ХЕНДЛЕРОВ ----------------

    # 1) /start и /help
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # 2) ConversationHandler для /settings (NLP-настройки)
    application.add_handler(settings_handler)

    # 3) Обратная связь (Inline-кнопки)
    application.add_handler(CallbackQueryHandler(process_feedback, pattern="^(like|dislike)$"))

    # 4) Статистика
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("stats_global", stats_global_command))

    # 5) Intent-классификация
    application.add_handler(intent_handler)

    # 6) Суммаризация текста
    application.add_handler(summarize_handler)

    # 7) Анализ тональности
    application.add_handler(sentiment_handler)

    # 8) Выделение тем (Topic Modeling)
    application.add_handler(topics_handler)

    # 9) Извлечение дедлайнов (NER)
    application.add_handler(extract_deadlines_handler)

    # 10) Генерация вопросов
    application.add_handler(generate_questions_handler)

    # 11) Файловая система: загрузка и список файлов
    application.add_handler(upload_handler)
    application.add_handler(list_files_handler)
    application.add_handler(download_file_handler)

    # 12) Универсальный /cancel (фолбэк для всех ConversationHandler)
    application.add_handler(CommandHandler("cancel", settings_handler.fallbacks[0].callback))

    # ---------------- ХЕНДЛЕР “Свободного чата” через дообученную модель ----------------
    # Обратите внимание: этот хендлер нужно регистрировать после всех
    # других конкретных ConversationHandler’ов, чтобы он не блокировал
    # команды (/summarize, /extract_deadlines, и т.д.).
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, chat.chat_handler)
    )

    # После запуска приложения задаём список команд Telegram
    application.post_init = set_commands

    logger.info("Бот запускается…")
    application.run_polling()


if __name__ == "__main__":
    main()
