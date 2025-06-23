# bot/handlers/auth.py
import bcrypt
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, ConversationHandler, MessageHandler, filters
from db.database import get_db
from db.models import User, Role
from bot.handlers.utils import log_activity

(Reg_ASK_USERNAME, Reg_ASK_PASSWORD, Login_ASK_USERNAME, Login_ASK_PASSWORD) = range(4)

@log_activity("register_start")
async def register_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("👤 Регистрация. Введите email (логин):")
    return Reg_ASK_USERNAME

@log_activity("register_username")
async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    context.user_data["reg_username"] = username
    with get_db() as db:
        if db.query(User).filter(User.username == username).first():
            await update.message.reply_text("❌ Такой email уже зарегистрирован.")
            return Reg_ASK_USERNAME
    await update.message.reply_text("Введите пароль (минимум 8 символов):")
    return Reg_ASK_PASSWORD

@log_activity("register_password")
async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    if len(password) < 8:
        await update.message.reply_text("❌ Пароль слишком короткий.")
        return Reg_ASK_PASSWORD

    username = context.user_data["reg_username"]
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    with get_db() as db:
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
        f"✅ Зарегистрированы как <code>{username}</code>, роль: client.", parse_mode="HTML"
    )
    return ConversationHandler.END

@log_activity("login_start")
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("🔑 Вход. Введите логин:")
    return Login_ASK_USERNAME

@log_activity("login_username")
async def login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text.strip()
    context.user_data["login_username"] = username
    with get_db() as db:
        if not db.query(User).filter(User.username == username).first():
            await update.message.reply_text("Пользователь не найден.")
            return ConversationHandler.END
    await update.message.reply_text("Введите пароль:")
    return Login_ASK_PASSWORD

@log_activity("login_password")
async def login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    password = update.message.text.strip()
    username = context.user_data["login_username"]
    with get_db() as db:
        user_obj = db.query(User).filter(User.username == username).first()
        if user_obj and bcrypt.checkpw(password.encode(), user_obj.password_hash.encode()):
            if user_obj.telegram_id is None:
                user_obj.telegram_id = update.effective_user.id
                db.add(user_obj)
                db.commit()
            context.user_data["is_authenticated"] = True
            context.user_data.update({
                "user_id": user_obj.id,
                "username": user_obj.username,
                "role": db.query(Role).filter(Role.id == user_obj.role_id).first().name
            })
            await update.message.reply_text(
                f"✅ Вы вошли как <code>{username}</code>. Роль: <b>{context.user_data['role']}</b>.",
                parse_mode="HTML"
            )
        else:
            await update.message.reply_text("❌ Неверный пароль.")
    return ConversationHandler.END

@log_activity("cancel_registration")
async def cancel_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена регистрации.")
    return ConversationHandler.END

@log_activity("cancel_login")
async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отмена входа.")
    return ConversationHandler.END

@log_activity("logout")
async def logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("is_authenticated"):
        context.user_data.clear()
        await update.message.reply_text("Вы вышли из системы.")
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
