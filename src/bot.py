from telegram.ext import ApplicationBuilder, MessageHandler, filters

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file = None

        # Check what was sent
        if update.message.video:
            file = await update.message.video.get_file()
            logger.info("Received video")
        elif update.message.animation:  # GIF wrapped in MP4
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

        # Download file
        await file.download_to_drive(file_path)
        logger.info(f"Downloaded: {file_path}")

        # Convert to GIF
        from src.ffmpeg_utils import convert_to_gif, get_filesize_mb
        gif_path = convert_to_gif(file_path, gif_path)

        if not gif_path:
            await update.message.reply_text("❌ Failed to convert video to GIF.")
            return

        # Check size
        size = get_filesize_mb(gif_path)
        if size > 8:
            await update.message.reply_text("⚠️ GIF too large (>8MB). Trying compression...")
        
        # Upload GIF to server
        from src.uploader import upload_file
        hosted_url = upload_file(gif_path)

        if hosted_url:
            await update.message.reply_text(f"✅ Your GIF is ready!\n{hosted_url}")
        else:
            await update.message.reply_text("❌ Failed to upload GIF.")

        # Cleanup temp files
        os.remove(file_path)
        os.remove(gif_path)

    except Exception as e:
        logger.exception("Error in handle_media")
        await update.message.reply_text("⚠️ Something went wrong, please try again later.")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Handle videos, animations, and MP4 documents
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.ANIMATION | filters.Document.VIDEO,
        handle_media
    ))

    logger.info("Telegram GIF Bot is running...")
    app.run_polling()
