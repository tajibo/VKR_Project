# bot/main.py
import logging
import os
import torch
from telegram import BotCommand, Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
from transformers import AutoTokenizer, AutoModelForCausalLM

from db.database import Base, engine, get_db
from bot.handlers.utils import log_activity
import bot.handlers.auth as auth
import bot.handlers.admin as admin
import bot.handlers.manager as manager
import bot.handlers.chat as chat
import bot.handlers.stats as stats
import bot.handlers.files as files
import bot.handlers.settings as settings
import bot.handlers.dashboard as dashboard
import bot.handlers.feedback as feedback
import bot.handlers.model_artifacts as artifacts
from bot.handlers import feedback
from telegram.ext import CommandHandler, CallbackQueryHandler

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

@log_activity("start")
async def start(update: Update, context):
    tg_user = update.effective_user
    with get_db() as db:
        existing = db.query(auth.User).filter(auth.User.telegram_id == tg_user.id).first()
        if not existing:
            client_role = db.query(auth.Role).filter(auth.Role.name == "client").first()
            if not client_role:
                client_role = auth.Role(name="client")
                db.add(client_role); db.commit(); db.refresh(client_role)
            new_user = auth.User(
                telegram_id=tg_user.id,
                username=tg_user.username or tg_user.first_name,
                password_hash="",
                role_id=client_role.id
            )
            db.add(new_user); db.commit()
            await update.message.reply_text(f"Привет, {tg_user.first_name}! Вы зарегистрированы.")
        else:
            await update.message.reply_text(f"С возвращением, {tg_user.first_name}!")

async def help_command(update: Update, context):
    cmds = [
        "/start","/help","/register","/login","/logout",
        "/settings","/summarize","/stats","/stats_global",
        "/upload","/list_files","/download","/manager_panel","/admin_panel"
    ]
    await update.message.reply_text("Доступные команды:\n" + "\n".join(cmds))

async def set_commands(application):
    commands = [
        BotCommand("start","Начать"), BotCommand("help","Помощь"),
        BotCommand("register","Регистрация"), BotCommand("login","Вход"),
        BotCommand("logout","Выход"), BotCommand("settings","Настройки"),
        BotCommand("stats","Моя статистика"), BotCommand("stats_global","Общая статистика"),
        BotCommand("upload","Загрузить файл"), BotCommand("list_files","Мои файлы"),
        BotCommand("manager_panel","Панель менеджера"), BotCommand("admin_panel","Панель администратора")
    ]
    await application.bot.set_my_commands(commands)

def main():
    load_dotenv()
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    HF_TOKEN = os.getenv("HUGGINGFACE_TOKEN")
    if not TOKEN or not HF_TOKEN:
        logger.error("Не заданы TELEGRAM_TOKEN или HUGGINGFACE_TOKEN")
        return

    REPO = "Dilshodbek11/ruDialoGPT-finetuned"
    tokenizer_obj = AutoTokenizer.from_pretrained(REPO, use_auth_token=HF_TOKEN)
    model_obj = AutoModelForCausalLM.from_pretrained(REPO, use_auth_token=HF_TOKEN)
    device_obj = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_obj.to(device_obj)
    if tokenizer_obj.pad_token_id is None:
        tokenizer_obj.add_special_tokens({"pad_token": tokenizer_obj.eos_token})
        model_obj.resize_token_embeddings(len(tokenizer_obj))

    chat.tokenizer = tokenizer_obj
    chat.model = model_obj
    chat.device = device_obj

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(auth.register_handler)
    app.add_handler(auth.login_handler)
    app.add_handler(CommandHandler("logout", auth.logout_command))
    app.add_handler(settings.settings_handler)
    app.add_handler(CommandHandler("stats", stats.stats_command))
    app.add_handler(CommandHandler("stats_global", stats.stats_global_command))
    app.add_handler(files.upload_handler)
    app.add_handler(files.list_files_handler)
    app.add_handler(files.download_file_handler)
    app.add_handler(manager.manager_panel_handler)
    app.add_handler(manager.manager_callback_handler)
    app.add_handler(admin.admin_panel_handler)
    app.add_handler(admin.admin_callback_handler)
    app.add_handler(admin.set_role_handler)
    app.add_handler(dashboard.dashboard_handler)
    app.add_handler(CommandHandler("feedback", feedback.request_feedback))
    app.add_handler(CallbackQueryHandler(feedback.process_feedback, pattern="^(like|dislike)$"))
    app.add_handler(artifacts.download_model_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat.chat_handler))

    app.post_init = set_commands
    logger.info("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
