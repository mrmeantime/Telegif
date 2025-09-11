import os
import logging
from telegram.ext import ApplicationBuilder, MessageHandler, filters

logging.basicConfig(level=logging.INFO)

# Use the same variable name as config.py
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN is missing! Set it in Render → Environment → Env Vars")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def echo(update, context):
    await update.message.reply_text("Bot is alive!")

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

if __name__ == "__main__":
    app.run_polling()
