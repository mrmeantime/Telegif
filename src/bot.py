import os
import logging
import aiohttp
import tempfile
import asyncio
import subprocess
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from src.ffmpeg_utils import convert_to_gif, get_filesize_mb

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

MAX_GIF_SIZE_MB = 8
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"


# ------------------- START COMMAND -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎥 Send me a GIF or Telegram GIF (MP4) and I'll convert, compress, "
        "host it on Catbox, and give you a link!"
    )


# ------------------- UPLOAD TO CATBOX -------------------
async def upload_to_catbox(file_path: str) -> str:
    async with aiohttp.ClientSession() as session:
        with open(file_path, "rb") as f:
            data = {
                "reqtype": "fileupload"
            }
            files = {
                "fileToUpload": f
            }
            async with session.post(CATBOX_UPLOAD_URL, data=data, files=files) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    logging.error(f"Catbox upload failed: {resp.status}")
                    return None


# ------------------- HANDLE GIF/MP4 -------------------
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        if not message:
            return

        # Prefer video/mp4 documents (Telegram GIFs)
        file = None
        if message.document and message.document.mime_type == "video/mp4":
            file = message.document
        elif message.animation:
            file = message.animation
        else:
            await message.reply_text("⚠️ Unsupported file format! Send me a GIF or Telegram GIF.")
            return

        # Download file into a temporary dir
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.file_name)

        tg_file = await file.get_file()
        await tg_file.download_to_drive(file_path)

        logging.info(f"Downloaded file: {file_path}")

        # Convert to GIF
        gif_path = os.path.join(temp_dir, os.path.splitext(file.file_name)[0] + ".gif")
        await convert_to_gif(file_path, gif_path)

        # Check size and compress if needed
        size_mb = get_filesize_mb(gif_path)
        if size_mb > MAX_GIF_SIZE_MB:
            logging.info(f"GIF {size_mb:.2f}MB too large, compressing...")
            compressed_gif = os.path.join(temp_dir, "compressed.gif")

            cmd = [
                "ffmpeg",
                "-i", gif_path,
                "-vf", "scale=iw/2:ih/2:flags=lanczos",
                "-b:v", "800k",
                "-loop", "0",
                compressed_gif
            ]
            subprocess.run(cmd, check=True)

            gif_path = compressed_gif
            size_mb = get_filesize_mb(gif_path)

        logging.info(f"Final GIF size: {size_mb:.2f}MB")

        # Upload to Catbox
        link = await upload_to_catbox(gif_path)
        if not link:
            await message.reply_text("🚨 Failed to upload GIF to Catbox.")
            return

        # Reply with link
        await message.reply_text(f"✅ Here's your hosted GIF:\n{link}")

    except Exception as e:
        logging.error(f"Error handling GIF: {e}")
        await update.message.reply_text("⚠️ Something went wrong while processing your GIF.")
    finally:
        # Cleanup temp files
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except:
            pass


# ------------------- MAIN ENTRYPOINT -------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.VIDEO | filters.ANIMATION,
        handle_gif
    ))

    logging.info("🚀 Bot started successfully...")
    app.run_polling()
