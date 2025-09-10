import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from src.ffmpeg_utils import convert_to_gif, get_filesize_mb
from src.uploader import upload_file
from src.config import TELEGRAM_BOT_TOKEN, MAX_FILESIZE_MB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set. Please configure it in Render.")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = await update.message.video.get_file()
        file_path = f"/tmp/{file.file_id}.mp4"
        gif_path = f"/tmp/{file.file_id}.gif"

        # Download MP4
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded video: {file_path}")

        # Convert to GIF
        convert_to_gif(file_path, gif_path)

        # Check size
        size = get_filesize_mb(gif_path)
        if size > MAX_FILESIZE_MB:
            await update.message.reply_text("❌ GIF too large (>8MB). Try a shorter video.")
            return

        # Upload to server
        hosted_url = upload_file(gif_path)
        if hosted_url:
            await update.message.reply_text(f"✅ Your GIF is ready!\n{hosted_url}")
        else:
            await update.message.reply_text("❌ Failed to upload GIF.")

        # Clean up
        os.remove(file_path)
        os.remove(gif_path)

    except Exception as e:
        logger.error(f"Error handling video: {e}")
        await update.message.reply_text("⚠️ Error converting your GIF.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    logger.info("Telegram GIF Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
