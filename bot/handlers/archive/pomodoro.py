# bot/handlers/pomodoro.py

from telegram import Update
from telegram.ext import ContextTypes, CallbackContext
from db.database import SessionLocal
from db.models import User, UserSetting, PomodoroSession
from sqlalchemy import func

async def start_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        db_settings = db.query(UserSetting).filter(UserSetting.user_id == db_user.id).first()
        if not db_settings:
            await update.message.reply_text("Сначала выполните /settings для инициализации.")
            return

        # 1. Создаём новую PomodoroSession (status="start")
        new_session = PomodoroSession(user_id=db_user.id, status="start")
        db.add(new_session)
        db.commit()
        db.refresh(new_session)

        # 2. Отменяем старый pomodoro_job, если он был
        old_pomodoro_job = context.chat_data.get("pomodoro_job")
        if old_pomodoro_job:
            old_pomodoro_job.schedule_removal()
            context.chat_data.pop("pomodoro_job", None)

        # 3. Планируем Job на окончание Pomodoro
        seconds = db_settings.pomodoro_duration * 60
        pomodoro_job = context.application.job_queue.run_once(
            pomodoro_complete_callback,
            when=seconds,
            data={"telegram_id": user_id, "session_id": new_session.id}
        )
        context.chat_data["pomodoro_job"] = pomodoro_job

        await update.message.reply_text(
            f"✅ Pomodoro запущён на {db_settings.pomodoro_duration} минут. Успешной работы!"
        )
    except Exception:
        await update.message.reply_text("Не удалось запустить Pomodoro 🛑")
    finally:
        db.close()


async def pomodoro_complete_callback(context: CallbackContext) -> None:
    job_data = context.job.data  # {"telegram_id": <id>, "session_id": <id>}
    telegram_id = job_data["telegram_id"]
    session_id = job_data["session_id"]

    # 1. Обновляем PomodoroSession (status="complete", ставим end_time)
    db = SessionLocal()
    try:
        session = db.query(PomodoroSession).filter(PomodoroSession.id == session_id).first()
        if session and session.status == "start":
            session.status = "complete"
            session.end_time = func.now()
            db.commit()
        else:
            db.close()
            return
    except Exception:
        db.close()
        return
    finally:
        db.close()

    # 2. Отправляем сообщение о завершении Pomodoro
    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="⏰ Pomodoro завершён! Пора сделать перерыв."
        )
    except Exception:
        pass

    # 3. Планируем таймер перерыва (break_duration)
    db2 = SessionLocal()
    try:
        session = db2.query(PomodoroSession).filter(PomodoroSession.id == session_id).first()
        if not session:
            db2.close()
            return

        settings = db2.query(UserSetting).filter(UserSetting.user_id == session.user_id).first()
        if not settings:
            db2.close()
            return

        seconds_break = settings.break_duration * 60

        old_break_job = context.chat_data.get("break_job")
        if old_break_job:
            old_break_job.schedule_removal()
            context.chat_data.pop("break_job", None)

        break_job = context.job_queue.run_once(
            break_complete_callback,
            when=seconds_break,
            data={"telegram_id": telegram_id, "session_id": session_id}
        )
        context.chat_data["break_job"] = break_job
    except Exception:
        pass
    finally:
        db2.close()


async def break_complete_callback(context: CallbackContext) -> None:
    job_data = context.job.data  # {"telegram_id": <id>, "session_id": <id>}
    telegram_id = job_data["telegram_id"]

    try:
        await context.bot.send_message(
            chat_id=telegram_id,
            text="⏳ Перерыв завершён! Можно возвращаться к работе."
        )
    except Exception:
        pass
    finally:
        context.chat_data.pop("break_job", None)


async def stop_pomodoro(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user_id).first()
        if not db_user:
            await update.message.reply_text("Сначала выполните /start для регистрации.")
            return

        # 1. Отменяем фоновые задачи: pomodoro_job и break_job (если были)
        pomodoro_job = context.chat_data.get("pomodoro_job")
        if pomodoro_job:
            pomodoro_job.schedule_removal()
            context.chat_data.pop("pomodoro_job", None)

        break_job = context.chat_data.get("break_job")
        if break_job:
            break_job.schedule_removal()
            context.chat_data.pop("break_job", None)

        # 2. Находим последнюю активную PomodoroSession
        session = (
            db.query(PomodoroSession)
            .filter(PomodoroSession.user_id == db_user.id, PomodoroSession.status == "start")
            .order_by(PomodoroSession.start_time.desc())
            .first()
        )
        if not session:
            await update.message.reply_text("Нет активной Pomodoro-сессии для остановки.")
            return

        session.status = "stopped"
        session.end_time = func.now()
        db.commit()

        await update.message.reply_text("⏹ Pomodoro остановлен досрочно.")
    except Exception:
        await update.message.reply_text("Не удалось остановить Pomodoro 🛑")
    finally:
        db.close()
