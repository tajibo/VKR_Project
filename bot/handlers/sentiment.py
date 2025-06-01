# bot/handlers/sentiment.py

import pickle
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db.database import SessionLocal
from db.models import User, UserActivity, ErrorLog

from bot.handlers.utils import log_activity

SENTIMENT_PKL_PATH = "ml/sentiment/models/sentiment_mlp_v1.pkl"
SENTIMENT_VEC_PKL = "ml/sentiment/models/sentiment_vectorizer.pkl"
SENTIMENT_LE_PKL = "ml/sentiment/models/sentiment_label_encoder.pkl"

try:
    with open(SENTIMENT_VEC_PKL, "rb") as f:
        sentiment_vectorizer = pickle.load(f)
    with open(SENTIMENT_LE_PKL, "rb") as f:
        sentiment_label_encoder = pickle.load(f)
    with open(SENTIMENT_PKL_PATH, "rb") as f:
        sentiment_model = pickle.load(f)
except Exception:
    sentiment_vectorizer = None
    sentiment_label_encoder = None
    sentiment_model = None


@log_activity("sentiment")
async def sentiment_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /sentiment <текст> — возвращает «Позитивный», «Нейтральный» или «Негативный».
    """
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return

        if not sentiment_vectorizer or not sentiment_model or not sentiment_label_encoder:
            await update.message.reply_text("❗ Модель sentiment пока не загружена.")
            return

        if not context.args:
            await update.message.reply_text("Пожалуйста, введите текст после /sentiment.")
            return

        user_text = " ".join(context.args)
        X = sentiment_vectorizer.transform([user_text])
        pred_idx = sentiment_model.predict(X)[0]
        sentiment_label = sentiment_label_encoder.inverse_transform([pred_idx])[0]

        # Преобразуем метки в читаемый вид
        sentiment_map = {
            "positive": "👍 Позитивный",
            "neutral": "😐 Нейтральный",
            "negative": "👎 Негативный",
        }
        response_text = sentiment_map.get(sentiment_label, "Не удалось определить тональность.")

        # Логируем в UserActivity
        activity = UserActivity(
            user_id=db_user.id,
            query_text=user_text[:100],
            intent_label="sentiment",
            handler_name="sentiment",
            response_time_ms=None
        )
        db.add(activity)
        db.commit()

        await update.message.reply_text(response_text)

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="sentiment",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Произошла ошибка при анализе тональности.")
    finally:
        db.close()


# Экспорт для main.py
sentiment_handler = CommandHandler("sentiment", sentiment_command)
