# bot/handlers/stats.py

import io
import matplotlib.pyplot as plt
from telegram import Update, InputFile
from telegram.ext import ContextTypes
from sqlalchemy import func
from db.database import SessionLocal
from db.models import User, UserActivity, ErrorLog

from bot.handlers.utils import log_activity

@log_activity("stats_user")
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stats — показывает личную статистику текущего пользователя:
      - общее число запросов
      - среднее время ответа
      - последние 5 запросов (query_text, response_time_ms)
    """
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user:
            await update.message.reply_text("Сначала зарегистрируйтесь через /start.")
            return

        # Получаем статистику
        total_requests = db.query(func.count(UserActivity.id)).filter(UserActivity.user_id == db_user.id).scalar()
        avg_time = db.query(func.avg(UserActivity.response_time_ms)).filter(UserActivity.user_id == db_user.id).scalar()

        last_5 = (
            db.query(UserActivity)
            .filter(UserActivity.user_id == db_user.id)
            .order_by(UserActivity.timestamp.desc())
            .limit(5)
            .all()
        )

        text = (
            f"<b>Ваша статистика:</b>\n"
            f"• Всего запросов: {total_requests or 0}\n"
            f"• Среднее время ответа: {int(avg_time) if avg_time else 0} мс\n\n"
            f"<b>Последние 5 запросов:</b>\n"
        )
        for act in last_5:
            q_text = act.query_text or "(нет текста)"
            rt = act.response_time_ms or 0
            text += f"– «{q_text[:50]}...» → {rt} мс\n"

        await update.message.reply_html(text)

    except Exception as e:
        db.rollback()
        # Логируем ошибку
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="stats_user",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось получить статистику. Попробуйте позже.")
    finally:
        db.close()


@log_activity("stats_global")
async def stats_global_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /stats_global — выводит агрегированную статистику по всем пользователям.
    Доступно только admin.
    """
    user_id_telegram = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id_telegram).first()
        if not db_user or db_user.role.name != "admin":
            await update.message.reply_text("🚫 У вас нет доступа к этой команде.")
            return

        # Топ-5 самых активных хендлеров по количеству запросов
        top_handlers = (
            db.query(UserActivity.handler_name, func.count(UserActivity.id).label("cnt"))
            .group_by(UserActivity.handler_name)
            .order_by(func.count(UserActivity.id).desc())
            .limit(5)
            .all()
        )

        # Топ-5 самых медленных хендлеров по среднему времени ответа
        slow_handlers = (
            db.query(UserActivity.handler_name, func.avg(UserActivity.response_time_ms).label("avg_rt"))
            .group_by(UserActivity.handler_name)
            .order_by(func.avg(UserActivity.response_time_ms).desc())
            .limit(5)
            .all()
        )

        total_users = db.query(func.count(User.id)).scalar()

        text = (
            f"<b>Общая статистика по боту:</b>\n"
            f"• Всего зарегистрированных пользователей: {total_users}\n\n"
            f"<b>Топ-5 самых активных хендлеров (по количеству запросов):</b>\n"
        )
        for handler_name, cnt in top_handlers:
            text += f"– {handler_name}: {cnt} запросов\n"

        text += "\n<b>Топ-5 самых медленных хендлеров (по среднему времени):</b>\n"
        for handler_name, avg_rt in slow_handlers:
            text += f"– {handler_name}: {int(avg_rt)} мс\n"

        await update.message.reply_html(text)

        # Дополнительно можно отправить график «число запросов по дням»
        # Ниже приведён пример построения и отправки такого графика:
        dates_counts = (
            db.query(
                func.date(UserActivity.timestamp).label("day"),
                func.count(UserActivity.id).label("cnt")
            )
            .group_by(func.date(UserActivity.timestamp))
            .order_by(func.date(UserActivity.timestamp))
            .all()
        )
        if dates_counts:
            # Разбиваем на списки
            days = [str(row.day) for row in dates_counts]
            counts = [row.cnt for row in dates_counts]

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

    except Exception as e:
        db.rollback()
        err_db = SessionLocal()
        try:
            err_db.add(ErrorLog(
                user_id=db_user.id if 'db_user' in locals() and db_user else None,
                handler_name="stats_global",
                error_text=str(e)
            ))
            err_db.commit()
        finally:
            err_db.close()

        await update.message.reply_text("❗ Не удалось получить глобальную статистику.")
    finally:
        db.close()
