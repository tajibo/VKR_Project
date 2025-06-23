# bot/handlers/dashboard.py
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from sqlalchemy import func
from db.database import get_db
from db.models import User, File, UserActivity, Role
from bot.handlers.utils import log_activity
from bot.handlers.auth_utils import requires_role

@log_activity("dashboard")
@requires_role(["admin", "manager", "client"])
async def dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = context.user_data.get("user_id")
    if not user_id:
        await update.message.reply_text("Пожалуйста, войдите через /login.")
        return

    with get_db() as db:
        user_obj = db.query(User).filter(User.id == user_id).first()
        role_name = db.query(Role).filter(Role.id == user_obj.role_id).first().name
        files_count = db.query(func.count(File.id)).filter(File.user_id == user_obj.id).scalar() or 0
        total_requests = db.query(func.count(UserActivity.id)).filter(UserActivity.user_id == user_obj.id).scalar() or 0

    text = (
        f"<b>Кабинет</b>\n"
        f"👤 {user_obj.username} (роль: {role_name})\n"
        f"📂 Файлов: {files_count}\n"
        f"📈 Запросов: {total_requests}"
    )
    await update.message.reply_html(text)

dashboard_handler = CommandHandler("dashboard", dashboard_handler)
