# bot/handlers/model_artifacts.py
import tempfile
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler
from huggingface_hub import hf_hub_download
from bot.handlers.auth_utils import requires_role
from bot.handlers.utils import log_activity

HUB_REPO_ID = "Dilshodbek11/ruDialoGPT-finetuned"

@log_activity("download_model")
@requires_role(["admin", "manager"])
async def download_model_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Загрузка артефактов модели…")
    files = ["pytorch_model.bin", "config.json", "tokenizer.json"]
    for name in files:
        try:
            tmp = tempfile.mkdtemp()
            path = hf_hub_download(repo_id=HUB_REPO_ID, filename=name, local_dir=tmp)
            with open(path, "rb") as f:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=InputFile(f, filename=name))
        except Exception as e:
            await update.message.reply_text(f"Ошибка {name}: {e}")
    await update.message.reply_text("Готово.")

download_model_handler = CommandHandler("download_model", download_model_handler)
