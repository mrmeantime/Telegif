import os
import requests
import subprocess
import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB Telegram limit
ABSOLUTE_MAX_SIZE = 100 * 1024 * 1024  # Hard safety limit, 100MB

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Ensure downloads dir exists
os.makedirs("downloads", exist_ok=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a GIF and I'll compress + host it on catbox.moe!")

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        file = message.document or message.animation

        # Skip unsupported files
        if not file:
            await message.reply_text("⚠️ Please send me a valid GIF or animation.")
            return

        # Check file size early
        if file.file_size > ABSOLUTE_MAX_SIZE:
            await message.reply_text("❌ File too large (limit 100MB). Please send a smaller GIF.")
            return

        # Download the file
        telegram_file = await context.bot.get_file(file.file_id)
        original_path = f"downloads/{file.file_name}"
        await telegram_file.download_to_drive(original_path)
        logging.info(f"Downloaded: {original_path} ({os.path.getsize(original_path)} bytes)")

        # Compress if bigger than Telegram limit
        compressed_path = f"downloads/compressed_{file.file_name}"
        if os.path.getsize(original_path) > MAX_FILE_SIZE:
            logging.info("Compressing GIF using ffmpeg...")
            cmd = [
                "ffmpeg", "-y",
                "-i", original_path,
                "-vf", "scale=480:-1:flags=lanczos",
                "-b:v", "900k",
                compressed_path
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=90)
            except asyncio.TimeoutError:
                proc.kill()
                await message.reply_text("⏳ Compression timed out. Try a smaller GIF.")
                _cleanup(original_path, compressed_path)
                return
        else:
            compressed_path = original_path

        # Upload to catbox
        logging.info("Uploading to catbox.moe...")
        try:
            with open(compressed_path, "rb") as f:
                response = requests.post(
                    CATBOX_URL,
                    data={"reqtype": "fileupload"},
                    files={"fileToUpload": f},
                    timeout=30
                )
        except requests.RequestException as e:
            logging.error(f"Catbox upload error: {e}")
            response = None

        if response and response.status_code == 200 and response.text.startswith("https://"):
            catbox_url = response.text.strip()
            await message.reply_text(f"✅ Uploaded to Catbox:\n{catbox_url}")
        else:
            # Fallback: Send via Telegram directly
            logging.warning("Catbox failed, falling back to Telegram upload.")
            with open(compressed_path, "rb") as f:
                await context.bot.send_document(
                    chat_id=message.chat_id,
                    document=f,
                    caption="⚠️ Catbox upload failed — sending directly."
                )

        # Clean up temp files
        _cleanup(original_path, compressed_path)

    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        await update.message.reply_text("❌ Something went wrong. Please try again.")

def _cleanup(original_path, compressed_path):
    """Remove temp files safely"""
    for path in [original_path, compressed_path]:
        try:
            if os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logging.warning(f"Failed to delete {path}: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).concurrent_updates(True).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Animation.ALL, handle_gif))
    logging.info("Bot is running...")
    app.run_polling()
