# bot/handlers/utils.py

import time
from telegram import Update
from telegram.ext import ContextTypes
from db.database import SessionLocal
from db.models import User, UserActivity

def log_activity(handler_name: str):
    """
    Декоратор для хендлеров: перед выполнением функции
    сохраняет в UserActivity информацию о запросе.
    """
    def decorator(func):
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            # Определяем user_id в БД
            user_id_telegram = None
            # Если это обычное текстовое сообщение
            if update.effective_user:
                user_id_telegram = update.effective_user.id

            # Получаем текст запроса: если это callback_query, берём data, иначе – message.text
            if update.callback_query:
                query_text = update.callback_query.data
            else:
                query_text = update.message.text if update.message else None

            # Засекаем время начала
            start_ts = time.time()

            db = SessionLocal()
            try:
                # Пытаемся найти пользователя в БД
                user_obj = None
                if user_id_telegram is not None:
                    user_obj = db.query(User).filter(User.telegram_id == user_id_telegram).first()
                user_pk = user_obj.id if user_obj else None

                # Создаём предварительный лог
                activity_row = UserActivity(
                    user_id=user_pk,
                    query_text=query_text,
                    intent_label=None,  # можно заполнить внутри хендлера, если нужно
                    handler_name=handler_name,
                    response_time_ms=None
                )
                db.add(activity_row)
                db.commit()
                db.refresh(activity_row)

                # Вызываем сам хендлер
                result = await func(update, context)

            except Exception:
                # В случае ошибки не обновляем response_time, просто закрываем сессию и пробрасываем дальше
                db.rollback()
                db.close()
                raise

            else:
                # Если всё прошло без исключений, рассчитываем время
                elapsed_ms = int((time.time() - start_ts) * 1000)
                try:
                    activity_row.response_time_ms = elapsed_ms
                    db.add(activity_row)
                    db.commit()
                except Exception:
                    db.rollback()
                finally:
                    db.close()

                return result

        return wrapper
    return decorator
