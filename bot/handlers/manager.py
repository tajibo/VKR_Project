# bot/handlers/manager.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from sqlalchemy import func
from db.database import get_db
from db.models import User, File, Role
from bot.handlers.auth_utils import requires_role
from bot.handlers.utils import log_activity

@log_activity("manager_panel")
@requires_role(["admin", "manager"])
async def manager_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("👤 Список клиентов", callback_data="mgr_list_clients")],
        [InlineKeyboardButton("📁 Файлы клиентов", callback_data="mgr_list_files")],
    ]
    await update.message.reply_text("Панель менеджера:", reply_markup=InlineKeyboardMarkup(keyboard))

@log_activity("manager_callback")
@requires_role(["admin", "manager"])
async def manager_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    with get_db() as db:
        role_client = db.query(Role).filter(Role.name == "client").first()
        if not role_client:
            return await query.edit_message_text("Роль client не найдена.")
        if data == "mgr_list_clients":
            clients = db.query(User).filter(User.role_id == role_client.id).all()
            text = "<b>Клиенты:</b>\n" + "\n".join(f"– {c.username}" for c in clients)
            await query.edit_message_text(text, parse_mode="HTML")
        elif data == "mgr_list_files":
            rows = (
                db.query(User.username, func.count(File.id).label("cnt"))
                  .outerjoin(File, User.id == File.user_id)
                  .filter(User.role_id == role_client.id)
                  .group_by(User.username)
                  .all()
            )
            text = "<b>Файлы клиентов:</b>\n" + "\n".join(f"– {u}: {cnt}" for u, cnt in rows)
            await query.edit_message_text(text, parse_mode="HTML")
        else:
            await query.edit_message_text("Неизвестная команда.")

manager_panel_handler    = CommandHandler("manager_panel", manager_panel_handler)
manager_callback_handler = CallbackQueryHandler(manager_callback_handler, pattern="^mgr_")
