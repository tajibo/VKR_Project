# bot/handlers/files.py
import os
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler
from db.database import get_db
from db.models import User, File
from bot.handlers.utils import log_activity

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
WAIT_FOR_FILE = range(1)[0]

@log_activity("upload_start")
async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Пришлите файл для загрузки:")
    return WAIT_FOR_FILE

@log_activity("receive_file")
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_tid = update.effective_user.id
    if not update.message.document:
        await update.message.reply_text("Пожалуйста, отправьте файл.")
        return WAIT_FOR_FILE

    with get_db() as db:
        db_user = db.query(User).filter(User.telegram_id == user_tid).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь.")
            return ConversationHandler.END
        doc = update.message.document
        file_obj = await context.bot.get_file(doc.file_id)
        path = os.path.join(UPLOAD_DIR, doc.file_name)
        await file_obj.download_to_drive(path)

        record = File(user_id=db_user.id, filename=doc.file_name, file_path=path)
        db.add(record)
        db.commit()

    await update.message.reply_text(f"✅ Файл «{doc.file_name}» сохранён.")
    return ConversationHandler.END

@log_activity("cancel_upload")
async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена загрузки.")
    return ConversationHandler.END

@log_activity("list_files")
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tid = update.effective_user.id
    with get_db() as db:
        db_user = db.query(User).filter(User.telegram_id == user_tid).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь.")
            return
        files = db.query(File).filter(File.user_id == db_user.id).all()
    if not files:
        await update.message.reply_text("Нет загруженных файлов.")
        return

    keyboard = [[InlineKeyboardButton(f.filename, callback_data=f"download_{f.id}")] for f in files]
    await update.message.reply_text("Ваши файлы:", reply_markup=InlineKeyboardMarkup(keyboard))

@log_activity("download_file")
async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    fid = int(query.data.split("_", 1)[1])
    with get_db() as db:
        db_user = db.query(User).filter(User.telegram_id == uid).first()
        record = db.query(File).filter(File.id == fid, File.user_id == db_user.id).first()
    if not record:
        await query.edit_message_text("Файл не найден.")
        return
    with open(record.file_path, "rb") as f:
        await context.bot.send_document(chat_id=query.message.chat_id, document=InputFile(f, filename=record.filename))

upload_handler = ConversationHandler(
    entry_points=[CommandHandler("upload", upload_start)],
    states={WAIT_FOR_FILE: [MessageHandler(filters.Document.ALL, receive_file)]},
    fallbacks=[CommandHandler("cancel", cancel_upload)],
    allow_reentry=True,
)
list_files_handler = CommandHandler("list_files", list_files)
download_file_handler = CallbackQueryHandler(download_file, pattern="^download_\\d+$")
