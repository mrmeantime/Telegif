import os
import sys
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    logging.error("❌ TELEGRAM_TOKEN is missing! Set it in Render → Environment → Secret Files or Env Vars")
    sys.exit(1)

if ":" not in TELEGRAM_TOKEN:
    logging.error("❌ TELEGRAM_TOKEN format invalid. Double-check with BotFather.")
    sys.exit(1)

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is alive!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.ALL, echo))
    logging.info("🚀 Bot started...")
    app.run_polling()
