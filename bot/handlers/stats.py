# bot/handlers/stats.py
import io
import matplotlib.pyplot as plt
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from sqlalchemy import func
from db.database import get_db
from db.models import User, UserActivity
from bot.handlers.utils import log_activity
from bot.handlers.auth_utils import requires_role

@log_activity("stats_user")
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tid = update.effective_user.id
    with get_db() as db:
        db_user = db.query(User).filter(User.telegram_id == user_tid).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return
        total_requests = db.query(func.count(UserActivity.id)).filter(UserActivity.user_id == db_user.id).scalar() or 0
        avg_time = db.query(func.avg(UserActivity.response_time_ms)).filter(UserActivity.user_id == db_user.id).scalar() or 0
        last_5 = (
            db.query(UserActivity)
            .filter(UserActivity.user_id == db_user.id)
            .order_by(UserActivity.timestamp.desc())
            .limit(5)
            .all()
        )

    text = (
        f"<b>Ваша статистика:</b>\n"
        f"• Всего запросов: {total_requests}\n"
        f"• Среднее время ответа: {int(avg_time)} мс\n\n"
        f"<b>Последние 5 запросов:</b>\n"
    )
    for act in last_5:
        q_text = act.query_text or "(нет текста)"
        rt = act.response_time_ms or 0
        text += f"– «{q_text[:50]}...» → {rt} мс\n"

    await update.message.reply_html(text)

@log_activity("stats_global")
@requires_role(["admin"])
async def stats_global_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tid = update.effective_user.id
    with get_db() as db:
        top_handlers = (
            db.query(UserActivity.handler_name, func.count(UserActivity.id).label("cnt"))
            .group_by(UserActivity.handler_name)
            .order_by(func.count(UserActivity.id).desc())
            .limit(5)
            .all()
        )
        slow_handlers = (
            db.query(UserActivity.handler_name, func.avg(UserActivity.response_time_ms).label("avg_rt"))
            .group_by(UserActivity.handler_name)
            .order_by(func.avg(UserActivity.response_time_ms).desc())
            .limit(5)
            .all()
        )
        total_users = db.query(func.count(User.id)).scalar() or 0

    text = (
        f"<b>Общая статистика по боту:</b>\n"
        f"• Всего пользователей: {total_users}\n\n"
        f"<b>Топ-5 активных хендлеров:</b>\n"
    )
    for h, cnt in top_handlers:
        text += f"– {h}: {cnt} запросов\n"
    text += "\n<b>Топ-5 медленных хендлеров:</b>\n"
    for h, avg in slow_handlers:
        text += f"– {h}: {int(avg)} мс\n"

    await update.message.reply_html(text)

    with get_db() as db:
        dates_counts = (
            db.query(func.date(UserActivity.timestamp).label("day"), func.count(UserActivity.id).label("cnt"))
            .group_by(func.date(UserActivity.timestamp))
            .order_by(func.date(UserActivity.timestamp))
            .all()
        )
    if dates_counts:
        days = [str(r.day) for r in dates_counts]
        counts = [r.cnt for r in dates_counts]
        plt.figure(figsize=(6,4))
        plt.plot(days, counts, marker="o")
        plt.xticks(rotation=45, ha="right")
        plt.title("Запросы по дням")
        plt.xlabel("Дата")
        plt.ylabel("Количество запросов")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close()
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=InputFile(buf, filename="requests_by_day.png"),
            caption="График запросов по дням"
        )
