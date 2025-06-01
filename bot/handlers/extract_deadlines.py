# bot/handlers/extract_deadlines.py

import pickle
import nltk
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, ConversationHandler, filters
from db.database import SessionLocal
from db.models import User, UserActivity, ErrorLog
from bot.handlers.utils import log_activity

# Загружаем необходимые модели/словарь признаков
CRF_MODEL_PKL = "ml/ner/models/ner_crf_v1.pkl"
CRF_FEATURES_PKL = "ml/ner/models/ner_features.pkl"

try:
    with open(CRF_MODEL_PKL, "rb") as f:
        crf_model = pickle.load(f)
    with open(CRF_FEATURES_PKL, "rb") as f:
        feature_dict = pickle.load(f)
except Exception:
    crf_model = None
    feature_dict = None

# Состояние для ConversationHandler
ASK_TEXT_DL = 1

nltk.download("punkt")
nltk.download("averaged_perceptron_tagger")

def tokenize_and_features(sent):
    """
    Подготовка признаков для каждого токена в предложении (для CRF).
    """
    tokens = nltk.word_tokenize(sent)
    pos_tags = nltk.pos_tag(tokens, lang="rus")
    features = []
    for i, token in enumerate(tokens):
        token_feats = {
            "token": token,
            "lower": token.lower(),
            "is_digit": token.isdigit(),
            "pos": pos_tags[i][1],
            "prefix-1": token[0] if token else "",
            "suffix-1": token[-1] if token else "",
        }
        features.append(token_feats)
    return tokens, features

@log_activity("extract_deadlines_start")
async def extract_deadlines_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return ConversationHandler.END

        await update.message.reply_text("Пришлите текст, из которого нужно извлечь дедлайны:")
        return ASK_TEXT_DL

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="extract_deadlines_start",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось начать извлечение дедлайнов.")
        return ConversationHandler.END

    finally:
        db.close()

@log_activity("extract_deadlines_text")
async def extract_deadlines_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id_telegram = update.effective_user.id
    input_text = update.message.text.strip()

    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()

        if not crf_model or not feature_dict:
            await update.message.reply_text("❗ Модель NER пока не загружена.")
            return ConversationHandler.END

        # Разбиваем на предложения
        sentences = nltk.sent_tokenize(input_text)

        extracted = []
        for sent in sentences:
            tokens, feats = tokenize_and_features(sent)
            # Подготавливаем фичи для модели
            feats_list = []
            for feat in feats:
                token_feat = {}
                for k in feat:
                    token_feat[k] = feat[k]
                feats_list.append(token_feat)

            # Предсказываем BIO-метки
            tags = crf_model.predict_single(feats_list)
            current_entity = []
            current_label = None
            for token, tag in zip(tokens, tags):
                if tag.startswith("B-"):
                    if current_entity:
                        extracted.append((" ".join(current_entity), current_label))
                        current_entity = []
                    current_entity = [token]
                    current_label = tag.split("-")[1]
                elif tag.startswith("I-") and current_entity:
                    current_entity.append(token)
                else:
                    if current_entity:
                        extracted.append((" ".join(current_entity), current_label))
                        current_entity = []
                        current_label = None
            if current_entity:
                extracted.append((" ".join(current_entity), current_label))

        if not extracted:
            await update.message.reply_text("Не удалось найти дедлайны в этом тексте.")
        else:
            msg = "<b>Найденные сущности (дедлайны/события):</b>\n"
            for ent, label in extracted:
                msg += f"• {ent} → {label}\n"
            await update.message.reply_html(msg)

        # Логируем в UserActivity
        activity = UserActivity(
            user_id=db_user.id,
            query_text=input_text[:100],
            intent_label="extract_deadlines",
            handler_name="extract_deadlines",
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
                handler_name="extract_deadlines_text",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Произошла ошибка при извлечении дедлайнов.")
    finally:
        db.close()

    return ConversationHandler.END

@log_activity("cancel_extract_deadlines")
async def cancel_extract_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Ок, отмена. Возвращаюсь в основное меню.")
    return ConversationHandler.END

# Обязательно объявляем именно это имя:
extract_deadlines_handler = ConversationHandler(
    entry_points=[CommandHandler("extract_deadlines", extract_deadlines_start)],
    states={
        ASK_TEXT_DL: [MessageHandler(filters.TEXT & ~filters.COMMAND, extract_deadlines_text)],
    },
    fallbacks=[CommandHandler("cancel", cancel_extract_deadlines)],
    allow_reentry=True,
)
