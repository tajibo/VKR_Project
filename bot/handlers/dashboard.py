# bot/handlers/dashboard.py

from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db.database import SessionLocal
from db.models import User, File, UserActivity, Role
from sqlalchemy import func
from bot.handlers.auth_utils import requires_role
from bot.handlers.utils import log_activity

@log_activity("dashboard")
@requires_role(["admin", "manager", "client"])
async def dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /dashboard — личный кабинет пользователя:
    показывает:
    • Логин и роль
    • Количество загруженных файлов
    • Всего запросов к ботам (UserActivity)
    """
    user_id = context.user_data.get("user_id")
    if not user_id:
        await update.message.reply_text("Не найден user_id. Попробуйте /login.")
        return

    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.id == user_id).first()
        if not user_obj:
            await update.message.reply_text("Пользователь не найден. Попробуйте /login.")
            return

        role_name = db.query(Role).filter(Role.id == user_obj.role_id).first().name
        files_count = db.query(func.count(File.id)).filter(File.user_id == user_obj.id).scalar() or 0
        total_requests = db.query(func.count(UserActivity.id)).filter(UserActivity.user_id == user_obj.id).scalar() or 0

        text = (
            f"<b>Личный кабинет</b>\n\n"
            f"👤 Логин: <code>{user_obj.username}</code>\n"
            f"🔑 Роль: <code>{role_name}</code>\n\n"
            f"📂 Загружено файлов: {files_count}\n"
            f"📈 Всего запросов к боту: {total_requests}\n"
        )
        await update.message.reply_html(text)
    finally:
        db.close()

# Экспортируем CommandHandler для main.py
dashboard_handler = CommandHandler("dashboard", dashboard_handler)
