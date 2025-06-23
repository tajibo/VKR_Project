# bot/handlers/auth_utils.py
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

def requires_role(allowed_roles: list[str]):
    def decorator(handler):
        @wraps(handler)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            if not context.user_data.get("is_authenticated"):
                await update.message.reply_text(
                    "🚫 Доступ только для зарегистрированных пользователей. Используйте /login."
                )
                return
            user_role = context.user_data.get("role")
            if user_role not in allowed_roles:
                await update.message.reply_text("🚫 У вас нет прав для выполнения этой команды.")
                return
            return await handler(update, context, *args, **kwargs)
        return wrapper
    return decorator
