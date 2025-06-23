# bot/handlers/utils.py
import time
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from db.database import get_db
from db.models import User, UserActivity

def log_activity(handler_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            user_id_telegram = update.effective_user.id if update.effective_user else None
            query_text = (
                update.callback_query.data
                if update.callback_query
                else (update.message.text if update.message else None)
            )
            start_ts = time.time()
            activity = None

            if user_id_telegram:
                with get_db() as db:
                    user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
                    if user:
                        activity = UserActivity(
                            user_id=user.id,
                            query_text=query_text,
                            handler_name=handler_name
                        )
                        db.add(activity)
                        db.commit()
                        db.refresh(activity)

            result = await func(update, context, *args, **kwargs)

            if activity:
                elapsed = int((time.time() - start_ts) * 1000)
                with get_db() as db:
                    activity.response_time_ms = elapsed
                    db.add(activity)
                    db.commit()

            return result
        return wrapper
    return decorator
