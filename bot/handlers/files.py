# bot/handlers/files.py

import os
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler
from db.database import SessionLocal
from db.models import User, File, ErrorLog
from bot.handlers.utils import log_activity

# Папка для сохранения загруженных файлов
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Состояния
WAIT_FOR_FILE, = range(1)

@log_activity("upload_start")
async def upload_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    await update.message.reply_text("Пришлите файл, который хотите загрузить:")
    return WAIT_FOR_FILE

@log_activity("receive_file")
async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return ConversationHandler.END

        # Ожидаем, что пользователь прислал документ (Document)
        if not update.message.document:
            await update.message.reply_text("Пожалуйста, отправьте именно файл (не фото или текст).")
            return WAIT_FOR_FILE

        document = update.message.document
        file_id = document.file_id
        file_name = document.file_name

        # Скачиваем файл
        new_file = await context.bot.get_file(file_id)
        save_path = os.path.join(UPLOAD_DIR, file_name)
        await new_file.download_to_drive(save_path)

        # Сохраняем в БД
        file_record = File(
            user_id=db_user.id,
            filename=file_name,
            file_path=save_path
        )
        db.add(file_record)
        db.commit()

        await update.message.reply_text(f"✅ Файл \"{file_name}\" успешно сохранён.")
    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="receive_file",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Произошла ошибка при сохранении файла.")
    finally:
        db.close()

    return ConversationHandler.END

@log_activity("cancel_upload")
async def cancel_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ок, отмена. Возвращаюсь в основное меню.")
    return ConversationHandler.END


@log_activity("list_files")
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /list_files — выводит список файлов пользователя с inline-кнопками для скачивания.
    """
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return

        files = db.query(File).filter(File.user_id == db_user.id).all()
        if not files:
            await update.message.reply_text("У вас нет загруженных файлов.")
            return

        # Формируем inline-кнопки
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = []
        for f in files:
            keyboard.append([InlineKeyboardButton(f.filename, callback_data=f"download_{f.id}")])
        markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("Ваши файлы:", reply_markup=markup)

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="list_files",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось получить список файлов.")
    finally:
        db.close()


@log_activity("download_file")
async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик CallbackQueryHandler для скачивания файла по ID.
    """
    query = update.callback_query
    await query.answer()
    data = query.data  # ожидаем формат "download_<id>"
    user_id_telegram = query.from_user.id
    file_id = int(data.split("_", 1)[1])

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await query.edit_message_text("Сначала зарегистрируйтесь через /start.")
            return

        file_record = db.query(File).filter(File.id == file_id, File.user_id == db_user.id).first()
        if not file_record:
            await query.edit_message_text("Файл не найден или у вас нет доступа к нему.")
            return

        # Отправляем файл
        with open(file_record.file_path, "rb") as f:
            await context.bot.send_document(chat_id=query.message.chat_id, document=InputFile(f, filename=file_record.filename))

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="download_file",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await query.edit_message_text("❗ Ошибка при скачивании файла.")
    finally:
        db.close()


# Экспорт ConversationHandler и Handler’ов
upload_handler = ConversationHandler(
    entry_points=[CommandHandler("upload", upload_start)],
    states={
        WAIT_FOR_FILE: [MessageHandler(filters.Document.ALL, receive_file)],
    },
    fallbacks=[CommandHandler("cancel", cancel_upload)],
    allow_reentry=True,
)

list_files_handler = CommandHandler("list_files", list_files)
download_file_handler = CallbackQueryHandler(download_file, pattern="^download_\\d+$")
