# bot/handlers/summarize.py

import nltk
import networkx as nx
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters

from db.database import SessionLocal
from db.models import User, UserSetting, UserActivity, ErrorLog

from bot.handlers.utils import log_activity

nltk.download("punkt")

# Состояния
ASK_TEXT, = range(1)

@log_activity("summarize_start")
async def summarize_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return ConversationHandler.END

        await update.message.reply_text("Пришлите текст, который нужно суммировать:")
        return ASK_TEXT

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="summarize_start",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось начать суммаризацию. Попробуйте позже.")
        return ConversationHandler.END

    finally:
        db.close()


@log_activity("summarize_text")
async def summarize_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    input_text = update.message.text.strip()

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        setting = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        K = setting.default_summary_length if setting else 3

        sentences = nltk.sent_tokenize(input_text)
        if len(sentences) <= K:
            await update.message.reply_text("Текст слишком короткий для суммаризации. Вот оригинал:")
            await update.message.reply_text(input_text)
            return ConversationHandler.END

        vectorizer = TfidfVectorizer(stop_words="russian")
        X = vectorizer.fit_transform(sentences)
        sim_matrix = (X * X.T).toarray()

        nx_graph = nx.from_numpy_array(sim_matrix)
        scores = nx.pagerank(nx_graph)

        ranked_sentences = sorted(((scores[i], s) for i, s in enumerate(sentences)), reverse=True)
        top_sentences = [s for _, s in ranked_sentences[:K]]

        final_sentences = []
        for sent in sentences:
            if sent in top_sentences:
                final_sentences.append(sent)

        summary = "\n".join(final_sentences)
        await update.message.reply_text("<b>Суммаризация:</b>\n" + summary, parse_mode="HTML")

        activity = UserActivity(
            user_id=db_user.id,
            query_text=input_text[:100],
            intent_label="summarize",
            handler_name="summarize",
            response_time_ms=None
        )
        db.add(activity)
        db.commit()

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="summarize_text",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Произошла ошибка при суммаризации.")
    finally:
        db.close()

    return ConversationHandler.END


@log_activity("cancel_summarize")
async def cancel_summarize(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ок, отмена. Возвращаюсь в основное меню.")
    return ConversationHandler.END

# ConversationHandler для /summarize
summarize_handler = ConversationHandler(
    entry_points=[CommandHandler("summarize", summarize_start)],
    states={
        ASK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, summarize_text)],
    },
    fallbacks=[CommandHandler("cancel", cancel_summarize)],
    allow_reentry=True,
)
