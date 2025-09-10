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
# FFmpeg Compression
# -------------------------
def compress_gif(input_path: Path, output_path: Path):
    """Compress GIF to try and keep under 8MB using ffmpeg."""
    try:
        cmd = [
            "ffmpeg",
            "-y",  # overwrite
            "-i", str(input_path),
            "-vf", "fps=15,scale=480:-1:flags=lanczos",  # lower fps + scale
            "-gifflags", "+transdiff",
            str(output_path)
        ]
        subprocess.run(cmd, check=True)
        logger.info(f"✅ Compressed GIF saved: {output_path}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ GIF compression failed: {e}")
        return False

# -------------------------
# Upload to Catbox
# -------------------------
def upload_to_catbox(file_path: Path) -> str:
    """Upload a file to Catbox.moe and return the URL."""
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
# Start Command
# -------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"User {update.effective_user.id} started the bot.")
    await update.message.reply_text("👋 Hi! Send me a GIF or video, and I'll process it.")

# -------------------------
# GIF / Video Handler
# -------------------------
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message or update.edited_message
        if not message:
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
        # Download file from Telegram
        # -------------------------
        bot = context.bot
        file = await bot.get_file(file_id)

        temp_dir = tempfile.mkdtemp()
        input_path = Path(temp_dir) / "input.gif"
        output_path = Path(temp_dir) / "output.gif"

        await file.download_to_drive(input_path)
        logger.info(f"✅ File saved locally: {input_path}")

        # -------------------------
        # Compress if needed
        # -------------------------
        if input_path.stat().st_size > 8 * 1024 * 1024:  # > 8MB
            logger.info("⚠️ File too large, compressing...")
            compress_success = compress_gif(input_path, output_path)
            final_path = output_path if compress_success else input_path
        else:
            final_path = input_path

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
        logger.exception(f"❌ Error handling GIF: {e}")
        await update.message.reply_text("⚠️ Something went wrong while processing your GIF.")

# -------------------------
# Main Function
# -------------------------
def main():
    logger.info("🚀 Starting Telegram GIF Export Bot...")

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.ANIMATION | filters.VIDEO, handle_gif))

    logger.info("📡 Bot is now running and polling for updates...")
    app.run_polling(drop_pending_updates=True)

# -------------------------
# Entry Point
# -------------------------
if __name__ == "__main__":
    main()
