# bot/handlers/admin.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from sqlalchemy import func
from db.database import SessionLocal
from db.models import User, Role
from bot.handlers.auth_utils import requires_role
from bot.handlers.utils import log_activity

@log_activity("admin_panel")
@requires_role(["admin"])
async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("👥 Список всех пользователей", callback_data="admin_list_users")],
        [InlineKeyboardButton("➕ Добавить роль пользователю", callback_data="admin_add_role")],
        [InlineKeyboardButton("📊 Глобальная статистика", callback_data="admin_stats")],
    ]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Панель администратора:", reply_markup=markup)

@log_activity("admin_callback")
@requires_role(["admin"])
async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data

    db = SessionLocal()
    try:
        if data == "admin_list_users":
            users = db.query(User).all()
            text = "<b>Список всех пользователей:</b>\n"
            for u in users:
                role_name = db.query(Role).filter(Role.id == u.role_id).first().name
                text += f"– {u.username} (роль: {role_name})\n"
            await query.edit_message_text(text, parse_mode="HTML")

        elif data == "admin_add_role":
            await query.edit_message_text(
                "Введите команду в формате:\n" 
                "/set_role <username> <role>\n" 
                "где роли: admin, manager, client"
            )

        elif data == "admin_stats":
            from bot.handlers.stats import stats_global_command
            await stats_global_command(update, context)

        else:
            await query.edit_message_text("Неизвестная команда.")
    finally:
        db.close()

@log_activity("set_role")
@requires_role(["admin"])
async def set_role_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) != 3:
        await update.message.reply_text("Неверный формат. Используйте /set_role <username> <role>.")
        return

    _, username, new_role = parts
    if new_role not in ("admin", "manager", "client"):
        await update.message.reply_text("Роль должна быть одной из: admin, manager, client.")
        return

    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.username == username).first()
        if not user_obj:
            await update.message.reply_text(f"Пользователь {username} не найден.")
            return

        role_obj = db.query(Role).filter(Role.name == new_role).first()
        if not role_obj:
            await update.message.reply_text(f"В системе нет роли {new_role}.")
            return

        user_obj.role_id = role_obj.id
        db.add(user_obj)
        db.commit()
        await update.message.reply_text(f"Роль пользователя {username} изменена на {new_role}.")
    except Exception:
        db.rollback()
        await update.message.reply_text("❗ Ошибка при изменении роли. Попробуйте ещё раз.")
    finally:
        db.close()

# Экспортируем объекты, которые будем регистрировать в main.py:
admin_panel_handler    = CommandHandler("admin_panel", admin_panel_handler)
admin_callback_handler = CallbackQueryHandler(admin_callback_handler, pattern="^admin_")
set_role_handler       = CommandHandler("set_role", set_role_handler)
