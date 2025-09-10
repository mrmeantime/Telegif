import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters,
)
from src.ffmpeg_utils import convert_to_gif, get_filesize_mb
from src.uploader import upload_file
from src.config import TELEGRAM_BOT_TOKEN

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG  # Enable full debug logging
)
logger = logging.getLogger(__name__)

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN not set. Please configure it in Render.")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = None

        # Check file type
        if update.message.video:
            file = await update.message.video.get_file()
            logger.info("Received video")
        elif update.message.animation:  # GIF-style MP4s
            file = await update.message.animation.get_file()
            logger.info("Received GIF animation")
        elif update.message.document and update.message.document.mime_type == "video/mp4":
            file = await update.message.document.get_file()
            logger.info("Received MP4 as document")
        else:
            await update.message.reply_text("⚠️ Please send an MP4 or GIF file.")
            return

        # Prepare paths
        file_path = f"/tmp/{file.file_id}.mp4"
        gif_path = f"/tmp/{file.file_id}.gif"

        # Download MP4/GIF to tmp
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded: {file_path}")

        # Convert to GIF (auto-compress)
        gif_path = convert_to_gif(file_path, gif_path)
        if not gif_path:
            await update.message.reply_text("❌ Failed to convert video to GIF.")
            return

        # Check GIF size
        size = get_filesize_mb(gif_path)
        if size > 8:
            await update.message.reply_text("⚠️ Final GIF is too large (>8MB). Trying compression...")
            logger.warning(f"Final GIF size: {size} MB")

        # Upload GIF to hosting server
        hosted_url = upload_file(gif_path)
        if hosted_url:
            await update.message.reply_text(f"✅ Your GIF is ready!\n{hosted_url}")
        else:
            await update.message.reply_text("❌ Failed to upload GIF.")

        # Clean up temporary files
        os.remove(file_path)
        os.remove(gif_path)

    except Exception as e:
        logger.exception("Error in handle_media")
        await update.message.reply_text("⚠️ Something went wrong, please try again later.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Accept MP4 videos, Telegram GIFs, and MP4 documents
    app.add_handler(
        MessageHandler(
            filters.VIDEO | filters.ANIMATION | filters.Document.VIDEO,
            handle_media
        )
    )

    logger.info("🚀 Telegram GIF Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
