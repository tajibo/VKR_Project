# bot/handlers/topics.py

import pickle
from gensim import corpora
from gensim.models.ldamodel import LdaModel
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler
from db.database import SessionLocal
from db.models import User, UserActivity, ErrorLog
from bot.handlers.utils import log_activity

LDA_DICT_PKL = "ml/topics/models/lda_dictionary.pkl"
LDA_MODEL_PKL = "ml/topics/models/lda_model_v1.pkl"

try:
    with open(LDA_DICT_PKL, "rb") as f:
        lda_dictionary = pickle.load(f)
    lda_model = LdaModel.load(LDA_MODEL_PKL)
except Exception:
    lda_dictionary = None
    lda_model = None


@log_activity("topics")
async def topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /topics — бот попросит несколько текстовых строк (через запятую или новую строку),
    после чего вернёт распределение по темам.
    """
    user_id_telegram = update.effective_user.id
    user_texts = " ".join(context.args) if context.args else None

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return

        if not user_texts:
            await update.message.reply_text("Пожалуйста, после команды /topics введите тексты разделённые точкой с запятой (или новой строкой).")
            return

        if not lda_dictionary or not lda_model:
            await update.message.reply_text("❗ Модель Topic Modeling пока не загружена.")
            return

        # Разбиваем входной текст на «документы» по точке с запятой
        docs = [doc.strip() for doc in user_texts.split(";") if doc.strip()]

        # Преобразуем каждый документ в Bag-of-Words
        corpus = [lda_dictionary.doc2bow(doc.lower().split()) for doc in docs]

        # Получаем распределение тем
        response_text = ""
        for idx, bows in enumerate(corpus):
            topic_dist = lda_model.get_document_topics(bows, minimum_probability=0.0)
            # Сортируем темы по вероятности
            topic_dist_sorted = sorted(topic_dist, key=lambda tup: tup[1], reverse=True)
            top_topics = topic_dist_sorted[:3]  # топ-3 тем

            response_text += f"<b>Документ {idx+1}:</b>\n"
            for topic_num, prob in top_topics:
                terms = lda_model.show_topic(topic_num, topn=5)
                terms_str = ", ".join([term for term, _ in terms])
                response_text += f"• Тема {topic_num} (вероятность {prob:.2f}): {terms_str}\n"
            response_text += "\n"

        # Логируем
        activity = UserActivity(
            user_id=db_user.id,
            query_text=user_texts[:100],
            intent_label="topics",
            handler_name="topics",
            response_time_ms=None
        )
        db.add(activity)
        db.commit()

        await update.message.reply_html(response_text)

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="topics",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Произошла ошибка при Topic Modeling.")
    finally:
        db.close()


# Экспорт для main.py
topics_handler = CommandHandler("topics", topics_command)
