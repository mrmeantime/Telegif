import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)
from src.ffmpeg_utils import convert_to_gif, get_filesize_mb

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message

        # Debug: Log what Telegram actually sent
        logging.info(f"Received message type: {message}")

        # Handle different possible media types
        file = None
        if message.animation:
            file = await message.animation.get_file()
        elif message.video:
            file = await message.video.get_file()
        elif message.document:
            file = await message.document.get_file()
        else:
            await message.reply_text("⚠️ Please send a GIF or video.")
            return

        # Download file
        file_path = f"/tmp/{file.file_path.split('/')[-1]}"
        await file.download_to_drive(file_path)
        logging.info(f"Downloaded: {file_path}")

        # Convert + compress if needed
        gif_path = await convert_to_gif(file_path)
        size_mb = get_filesize_mb(gif_path)
        logging.info(f"Final GIF size: {size_mb:.2f} MB")

        if size_mb > 8:
            await message.reply_text(
                "⚠️ Sorry, I couldn’t compress below 8 MB. Try a shorter clip."
            )
            return

        # Send optimized GIF back
        with open(gif_path, "rb") as gif_file:
            await message.reply_document(document=gif_file)

    except Exception as e:
        logging.exception("Error processing media")
        await update.message.reply_text("⚠️ Something went wrong, please try again later.")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    # Listen for videos, GIFs, and documents
    media_filter = filters.ANIMATION | filters.VIDEO | filters.Document.ALL
    app.add_handler(MessageHandler(media_filter, handle_media))

    logging.info("🚀 Bot started. Waiting for GIFs or videos...")
    app.run_polling()

if __name__ == "__main__":
    main()
