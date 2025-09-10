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

logging.basicConfig(level=logging.DEBUG)

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get file from Telegram
        file = await update.message.document.get_file()
        file_path = f"/tmp/{file.file_path.split('/')[-1]}"
        await file.download_to_drive(file_path)

        logging.info(f"Downloaded file: {file_path}")

        # Convert & compress GIF if necessary
        gif_path = await convert_to_gif(file_path)

        size_mb = get_filesize_mb(gif_path)
        logging.info(f"Final GIF size: {size_mb:.2f} MB")

        if size_mb > 8:
            await update.message.reply_text(
                "⚠️ Could not compress below 8 MB. Please try a shorter clip."
            )
            return

        # Send optimized GIF back to user
        await update.message.reply_document(document=open(gif_path, "rb"))

    except Exception as e:
        logging.exception("Error processing media")
        await update.message.reply_text("⚠️ Something went wrong, please try again later.")

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.Document.ALL, handle_media))
    app.run_polling()

if __name__ == "__main__":
    main()
