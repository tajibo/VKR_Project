from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Бот запущен ✅")

if __name__ == "__main__":
    app = ApplicationBuilder().token("7542036376:AAEeWEqZUfUTboVJhw_ASZDDomMsRiwrVQA").build()
    app.add_handler(CommandHandler("start", start))
    print("Бот запускается…")
    app.run_polling()
