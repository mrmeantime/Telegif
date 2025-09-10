#!/usr/bin/env python3
import logging
import os
import sys
import tempfile
import requests
from pathlib import Path
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# -------------------------
# Logging Setup (Full Debug)
# -------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

# -------------------------
# Environment Variables
# -------------------------
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is not set!")
    sys.exit(1)

# -------------------------
# Start Command
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot.")
    await update.message.reply_text("👋 Hi! Send me a GIF and I'll process it.")

# -------------------------
# GIF / Video Handler
# -------------------------
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.edited_message
        if not message:
            logger.warning("⚠️ Received update without message.")
            return

        if message.animation:
            file_id = message.animation.file_id
            logger.info(f"🎞️ GIF received: file_id={file_id}")
        elif message.video:
            file_id = message.video.file_id
            logger.info(f"📹 Video received: file_id={file_id}")
        else:
            await update.message.reply_text("⚠️ Please send a GIF or video.")
            return

        # -------------------------
        # Get File Info from Telegram
        # -------------------------
        bot = context.bot
        file = await bot.get_file(file_id)
        logger.debug(f"📥 Downloading file from {file.file_path}")

        # Download to temp directory
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / "input.gif"
        await file.download_to_drive(temp_path)
        logger.info(f"✅ File saved: {temp_path}")

        # -------------------------
        # TODO: Process GIF (FFmpeg)
        # -------------------------
        # Placeholder for GIF compression/export logic
        # We'll add ffmpeg processing later

        await update.message.reply_text("✅ GIF received and saved! Processing soon...")

    except Exception as e:
        logger.exception(f"❌ Error handling GIF: {e}")
        await update.message.reply_text("⚠️ Something went wrong while processing your GIF.")

# -------------------------
# Main Function
# -------------------------
def main():
    logger.info("🚀 Starting Telegram GIF Export Bot...")

    # Build app with polling
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # Handle GIFs & videos
    app.add_handler(MessageHandler(filters.ANIMATION | filters.VIDEO, handle_gif))

    # Start polling
    logger.info("📡 Bot is running and polling for updates...")
    app.run_polling(drop_pending_updates=True)

# -------------------------
# Entry Point
# -------------------------
if __name__ == "__main__":
    main()
