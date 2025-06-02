# bot/handlers/auth.py

import bcrypt
from telegram import Update
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters
)
from db.database import SessionLocal
from db.models import User, Role
from bot.handlers.utils import log_activity

(Reg_ASK_USERNAME, Reg_ASK_PASSWORD, Login_ASK_USERNAME, Login_ASK_PASSWORD) = range(4)

@log_activity("register_start")
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👤 Регистрация нового пользователя.\nВведите email (логин):"
    )
    return Reg_ASK_USERNAME

@log_activity("register_username")
async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    context.user_data["reg_username"] = username

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == username).first():
            await update.message.reply_text(
                "❌ Такой email уже зарегистрирован.\nПопробуйте другой или выполните /login."
            )
            return Reg_ASK_USERNAME
        else:
            await update.message.reply_text("Введите пароль (минимум 8 символов):")
            return Reg_ASK_PASSWORD
    finally:
        db.close()

@log_activity("register_password")
async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    if len(password) < 8:
        await update.message.reply_text("❌ Пароль слишком короткий. Введите минимум 8 символов:")
        return Reg_ASK_PASSWORD

    username = context.user_data.get("reg_username")
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    db = SessionLocal()
    try:
        role_obj = db.query(Role).filter(Role.name == "client").first()
        if not role_obj:
            role_obj = Role(name="client")
            db.add(role_obj)
            db.commit()
            db.refresh(role_obj)

        new_user = User(
            username=username,
            password_hash=hashed,
            role_id=role_obj.id,
            telegram_id=update.effective_user.id
        )
        db.add(new_user)
        db.commit()

        await update.message.reply_text(
            f"✅ Регистрация завершена! Логин: <code>{username}</code>\n"
            "Роль: client.\n"
            "Используйте /dashboard для просмотра кабинета.",
            parse_mode="HTML"
        )
    except Exception:
        db.rollback()
        await update.message.reply_text("❗ Ошибка при регистрации. Попробуйте позже.")
    finally:
        db.close()

    return ConversationHandler.END

@log_activity("login_start")
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🔑 Вход. Введите ваш логин (email):")
    return Login_ASK_USERNAME

@log_activity("login_username")
async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    context.user_data["login_username"] = username

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == username).first():
            await update.message.reply_text(
                "Пользователь не найден. Попробуйте /login заново или /register."
            )
            return ConversationHandler.END
        else:
            await update.message.reply_text("Введите пароль:")
            return Login_ASK_PASSWORD
    finally:
        db.close()

@log_activity("login_password")
async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    username = context.user_data.get("login_username")

    db = SessionLocal()
    try:
        user_obj = db.query(User).filter(User.username == username).first()
        if user_obj and bcrypt.checkpw(password.encode("utf-8"), user_obj.password_hash.encode("utf-8")):
            if user_obj.telegram_id is None:
                user_obj.telegram_id = update.effective_user.id
                db.add(user_obj)
                db.commit()

            context.user_data["is_authenticated"] = True
            context.user_data["user_id"] = user_obj.id
            context.user_data["username"] = user_obj.username
            context.user_data["role"] = db.query(Role).filter(Role.id == user_obj.role_id).first().name

            await update.message.reply_text(
                f"✅ Вы вошли как <code>{username}</code>.\nРоль: <b>{context.user_data['role']}</b>.",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ Неверный пароль. Попробуйте /login ещё раз.")
    finally:
        db.close()

    return ConversationHandler.END

@log_activity("cancel_registration")
async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена регистрации.")
    return ConversationHandler.END

@log_activity("cancel_login")
async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена логина.")
    return ConversationHandler.END

@log_activity("logout")
async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("is_authenticated"):
        context.user_data.clear()
        await update.message.reply_text("Вы вышли из системы. До встречи!")
    else:
        await update.message.reply_text("Вы не были авторизованы.")

register_handler = ConversationHandler(
    entry_points=[CommandHandler("register", register_start)],
    states={
        Reg_ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
        Reg_ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel_registration)],
    allow_reentry=True,
)

login_handler = ConversationHandler(
    entry_points=[CommandHandler("login", login_start)],
    states={
        Login_ASK_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_username)],
        Login_ASK_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, login_password)],
    },
    fallbacks=[CommandHandler("cancel", cancel_login)],
    allow_reentry=True,
)
