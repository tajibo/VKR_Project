# bot/handlers/manager.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from sqlalchemy import func
from db.database import SessionLocal
from db.models import User, File, Role
from bot.handlers.auth_utils import requires_role
from bot.handlers.utils import log_activity

@log_activity("manager_panel")
@requires_role(["admin", "manager"])
async def manager_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /manager_panel — панель менеджера: список клиентов и их файлы.
    Доступно Admin и Manager.
    """
    keyboard = [
        [InlineKeyboardButton("👤 Список клиентов", callback_data="mgr_list_clients")],
        [InlineKeyboardButton("📁 Файлы клиентов", callback_data="mgr_list_files")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Панель менеджера:", reply_markup=markup)

@log_activity("manager_callback")
@requires_role(["admin", "manager"])
async def manager_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    db = SessionLocal()
    try:
        role_client = db.query(Role).filter(Role.name == "client").first()
        if not role_client:
            await query.edit_message_text("Роль client не найдена.")
            return

        if data == "mgr_list_clients":
            clients = db.query(User).filter(User.role_id == role_client.id).all()
            text = "<b>Список клиентов:</b>\n"
            for c in clients:
                text += f"– {c.username}\n"
            await query.edit_message_text(text, parse_mode="HTML")

        elif data == "mgr_list_files":
            rows = (
                db.query(User.username, func.count(File.id).label("cnt"))
                  .outerjoin(File, User.id == File.user_id)
                  .filter(User.role_id == role_client.id)
                  .group_by(User.username)
                  .all()
            )
            text = "<b>Файлы клиентов (кол-во):</b>\n"
            for username, cnt in rows:
                text += f"– {username}: {cnt} файл(ов)\n"
            await query.edit_message_text(text, parse_mode="HTML")
        else:
            await query.edit_message_text("Неизвестная команда.")
    finally:
        db.close()

# Экспортируем объекты с правильными именами:
manager_panel_handler    = CommandHandler("manager_panel", manager_panel)
manager_callback_handler = CallbackQueryHandler(manager_callback, pattern="^mgr_")
