# bot/handlers/model_artifacts.py

import os
import tempfile
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler
from huggingface_hub import hf_hub_download
from bot.handlers.auth_utils import requires_role
from bot.handlers.utils import log_activity

HUB_REPO_ID = "Dilshodbek11/ruDialoGPT-finetuned"  # ваш репозиторий на Hugging Face

@log_activity("download_model")
@requires_role(["admin", "manager"])
async def download_model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /download_model — скачивает артефакты модели (pytorch_model.bin, config.json и т.д.)
    из Hugging Face Hub и отправляет в чат. Доступно Admin и Manager.
    """
    await update.message.reply_text("Начинаю загрузку артефактов модели с Hugging Face…")

    # Пример: скачиваем файлы модели в /tmp и пересылаем их по очереди
    files_to_download = ["pytorch_model.bin", "config.json", "tokenizer.json"]  # список имен файлов в репо
    for filename in files_to_download:
        try:
            # Скачиваем во временную папку
            tmp_dir = tempfile.mkdtemp()
            local_path = hf_hub_download(repo_id=HUB_REPO_ID, filename=filename, local_dir=tmp_dir)
            # Отправляем файл пользователю
            with open(local_path, "rb") as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(f, filename=filename))
        except Exception as e:
            await update.message.reply_text(f"❗ Не удалось загрузить {filename}: {e}")

    await update.message.reply_text("✅ Все доступные артефакты отправлены.")
