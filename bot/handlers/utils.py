# bot/handlers/utils.py

import time
from telegram import Update
from telegram.ext import ContextTypes
from db.database import SessionLocal
from db.models import User, UserActivity


def log_activity(handler_name: str):
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user_id_telegram = update.effective_user.id if update.effective_user else None
            query_text = update.callback_query.data if update.callback_query else (update.message.text if update.message else None)

            start_ts = time.time()
            db = SessionLocal()
            try:
                user_pk = None
                if user_id_telegram is not None:
                    user_obj = db.query(User).filter(User.telegram_id == user_id_telegram).first()
                    if user_obj:
                        user_pk = user_obj.id

                # Если user_pk остался None — не создаём запись о активности!
                activity_row = None
                if user_pk is not None:
                    activity_row = UserActivity(
                        user_id=user_pk,
                        query_text=query_text,
                        intent_label=None,
                        handler_name=handler_name,
                        response_time_ms=None
                    )
                    db.add(activity_row)
                    db.commit()
                    db.refresh(activity_row)

                result = await func(update, context)

            except Exception:
                db.rollback()
                db.close()
                raise
            else:
                if activity_row:
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                    try:
                        activity_row.response_time_ms = elapsed_ms
                        db.add(activity_row)
                        db.commit()
                    except Exception:
                        db.rollback()
                    finally:
                        db.close()
                else:
                    db.close()

                return result

        return wrapper
    return decoratoror