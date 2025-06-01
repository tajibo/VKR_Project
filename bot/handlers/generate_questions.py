# bot/handlers/generate_questions.py

import pickle
import numpy as np
from tensorflow.keras.models import load_model
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters
from db.database import SessionLocal
from db.models import User, UserActivity, ErrorLog
from bot.handlers.utils import log_activity

# Состояния
ASK_PARA = 1

# Пути к файлам с моделью и токенизатором
QUESTION_MODEL_H5 = "ml/question_gen/models/question_gen_lstm_v1.h5"
TOKENIZER_PKL = "ml/question_gen/models/question_tokenizer.pkl"

try:
    question_model = load_model(QUESTION_MODEL_H5)
    with open(TOKENIZER_PKL, "rb") as f:
        tokenizer = pickle.load(f)
except Exception:
    question_model = None
    tokenizer = None

MAX_LEN = 100  # максимальная длина входной последовательности

@log_activity("generate_questions_start")
async def generate_questions_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return ConversationHandler.END

        await update.message.reply_text("Пришлите текст, из которого нужно сгенерировать вопросы:")
        return ASK_PARA

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="generate_questions_start",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Ошибка при запуске генерации вопросов.")
        return ConversationHandler.END

    finally:
        db.close()

@log_activity("generate_questions_text")
async def generate_questions_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    paragraph = update.message.text.strip()

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()

        if not question_model or not tokenizer:
            await update.message.reply_text("❗ Модель генерации вопросов пока не загружена.")
            return ConversationHandler.END

        # Преобразуем текст в последовательность индексов
        seq = tokenizer.texts_to_sequences([paragraph])
        seq_padded = np.array([np.pad(s, (0, MAX_LEN - len(s)), 'constant')[:MAX_LEN] for s in seq])

        # Генерируем вопросы (greedy decoding)
        # Предполагается, что модель выдаёт индексы токенов ответа
        preds = question_model.predict(seq_padded)
        # preds.shape = (1, max_question_len, vocab_size) — например, (1, 20, V)
        question_tokens = np.argmax(preds[0], axis=1)
        inv_map = {v: k for k, v in tokenizer.word_index.items()}
        # Собираем слова до первого <end> токена (предположим, индекс 0)
        generated = []
        for idx in question_tokens:
            word = inv_map.get(idx, None)
            if word is None or word == "endseq":
                break
            generated.append(word)
        question = " ".join(generated)

        # Логируем
        activity = UserActivity(
            user_id=db_user.id,
            query_text=paragraph[:100],
            intent_label="generate_questions",
            handler_name="generate_questions",
            response_time_ms=None
        )
        db.add(activity)
        db.commit()

        await update.message.reply_text(f"Сгенерированный вопрос:\n❓ {question}")

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="generate_questions_text",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Ошибка при генерации вопроса.")
    finally:
        db.close()

    return ConversationHandler.END

@log_activity("cancel_generate_questions")
async def cancel_generate_questions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ок, отмена. Возвращаюсь в основное меню.")
    return ConversationHandler.END

# ConversationHandler для /generate_questions
generate_questions_handler = ConversationHandler(
    entry_points=[CommandHandler("generate_questions", generate_questions_start)],
    states={
        ASK_PARA: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_questions_text)],
    },
    fallbacks=[CommandHandler("cancel", cancel_generate_questions)],
    allow_reentry=True,
)
