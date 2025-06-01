# bot/handlers/intent.py

import pickle
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db.database import SessionLocal
from db.models import User, UserActivity, ErrorLog

from bot.handlers.utils import log_activity

INTENT_PKL_PATH = "ml/intent_classification/models/intent_model.pkl"
VECTORIZER_PKL_PATH = "ml/intent_classification/models/vectorizer_intent.pkl"
LABELENC_PKL_PATH = "ml/intent_classification/models/label_encoder_intent.pkl"

# Предварительно загружаем модели (или можно загружать при первом запросе)
try:
    with open(VECTORIZER_PKL_PATH, "rb") as f:
        vectorizer = pickle.load(f)
    with open(LABELENC_PKL_PATH, "rb") as f:
        label_encoder = pickle.load(f)
    with open(INTENT_PKL_PATH, "rb") as f:
        intent_model = pickle.load(f)
except Exception:
    vectorizer = None
    label_encoder = None
    intent_model = None


@log_activity("intent")
async def intent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /intent <текст> — распознаёт intent и возвращает заранее заготовленный ответ.
    """
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return

        if not vectorizer or not intent_model or not label_encoder:
            await update.message.reply_text("❗ Модель intent-классификации пока не загружена.")
            return

        # Собираем текст после команды
        if not context.args:
            await update.message.reply_text("Пожалуйста, введите текст после /intent.")
            return
        user_text = " ".join(context.args)

        # Векторизуем и предсказываем
        X = vectorizer.transform([user_text])
        pred_label_idx = intent_model.predict(X)[0]
        intent_name = label_encoder.inverse_transform([pred_label_idx])[0]

        # Здесь можно иметь заранее заготовленный словарь intent→response
        intent_responses = {
            "apply_course": "Чтобы подать заявку на курс, перейдите по ссылке: https://example.com/apply",
            "ask_time": "Сейчас сейчас примерно время UTC.",
            "other": "Извините, я не понял вашего запроса.",
            # добавьте все ваши intent→ответы
        }
        response_text = intent_responses.get(intent_name, "Ответ для этого intent ещё не настроен.")

        # Логируем intent_label в UserActivity
        # (можно обновить последнюю запись, но проще — создать новую)
        activity = UserActivity(
            user_id=db_user.id,
            query_text=user_text,
            intent_label=intent_name,
            handler_name="intent",
            response_time_ms=None
        )
        db.add(activity)
        db.commit()

        await update.message.reply_text(response_text)

        # После ответа предлагаем оставить обратную связь
        await request_feedback(update, context)

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="intent",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Произошла ошибка при работе intent-классификации.")
    finally:
        db.close()


# Экспорт для main.py
intent_handler = CommandHandler("intent", intent_command)
