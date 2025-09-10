#!/usr/bin/env python3
import logging
import os
import sys
import tempfile
import requests
import subprocess
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
# Logging Setup
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
# FFMPEG UTILITIES
# -------------------------
def convert_to_gif(input_path: Path, output_path: Path):
    """Convert MP4 or other video to GIF using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-vf", "fps=15,scale=480:-1:flags=lanczos",
            str(output_path)
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Converted video to GIF: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Video to GIF conversion failed: {e}")
        return False

def compress_gif(input_path: Path, output_path: Path):
    """Compress GIF to stay under 8MB using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_path),
            "-vf", "fps=12,scale=360:-1:flags=lanczos",
            str(output_path)
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Compressed GIF saved: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ GIF compression failed: {e}")
        return False

# -------------------------
# UPLOAD TO CATBOX
# -------------------------
def upload_to_catbox(file_path: Path) -> str:
    """Upload a file to Catbox.moe and return the hosted URL."""
    try:
        url = "https://catbox.moe/user/api.php"
        with open(file_path, "rb") as f:
            response = requests.post(
                url,
                data={"reqtype": "fileupload"},
                files={"fileToUpload": f}
            )
        if response.status_code == 200:
            hosted_url = response.text.strip()
            logger.info(f"✅ Uploaded to Catbox: {hosted_url}")
            return hosted_url
        else:
            logger.error(f"❌ Catbox upload failed: {response.text}")
            return None
    except Exception as e:
        logger.exception(f"❌ Error uploading to Catbox: {e}")
        return None

# -------------------------
# START COMMAND
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi! Send me a GIF or short video.\n"
        "I'll convert it, compress if needed, upload it to Catbox, "
        "and send you a direct link under 8MB."
    )

# -------------------------
# GIF / VIDEO HANDLER
# -------------------------
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.edited_message
        if not message:
            return

        # -------------------------
        # Identify File Type
        # -------------------------
        if message.animation:
            file_id = message.animation.file_id
            original_name = message.animation.file_name or "file.gif"
            logger.info(f"🎞️ Animation received: {original_name}")
        elif message.video:
            file_id = message.video.file_id
            original_name = message.video.file_name or "file.mp4"
            logger.info(f"📹 Video received: {original_name}")
        else:
            await update.message.reply_text("⚠️ Please send a GIF or video.")
            return

        # -------------------------
        # Download File from Telegram
        # -------------------------
        bot = context.bot
        file = await bot.get_file(file_id)

        temp_dir = tempfile.mkdtemp()
        input_path = Path(temp_dir) / original_name
        gif_path = Path(temp_dir) / "converted.gif"
        compressed_path = Path(temp_dir) / "compressed.gif"

        await file.download_to_drive(input_path)
        logger.info(f"✅ File downloaded: {input_path}")

        # -------------------------
        # Convert MP4 to GIF if needed
        # -------------------------
        if input_path.suffix.lower() == ".mp4":
            logger.info("🔄 Converting MP4 to GIF...")
            if not convert_to_gif(input_path, gif_path):
                await update.message.reply_text("❌ Failed to convert video to GIF.")
                return
        else:
            gif_path = input_path

        # -------------------------
        # Compress if output > 8MB
        # -------------------------
        final_path = gif_path
        if gif_path.stat().st_size > 8 * 1024 * 1024:
            logger.info("⚠️ GIF too large, compressing...")
            if compress_gif(gif_path, compressed_path):
                final_path = compressed_path

        # -------------------------
        # Upload to Catbox
        # -------------------------
        hosted_url = upload_to_catbox(final_path)
        if hosted_url:
            await update.message.reply_text(
                f"✅ Your GIF is ready!\n\n🔗 {hosted_url}\n\n📌 Copy and paste this link anywhere."
            )
        else:
            await update.message.reply_text("❌ Failed to upload GIF. Please try again later.")

    except Exception as e:
        logger.exception(f"❌ Error handling media: {e}")
        await update.message.reply_text("⚠️ Something went wrong. Please try again later.")

# -------------------------
# MAIN ENTRY POINT
# -------------------------
def main():
    logger.info("🚀 Starting Telegram GIF Export Bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ANIMATION | filters.VIDEO, handle_media))

    logger.info("📡 Bot is now running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
