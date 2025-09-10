import os
import requests
import subprocess
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB Telegram limit

logging.basicConfig(level=logging.INFO)

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document and not update.message.animation:
        await update.message.reply_text("Please send me a GIF!")
        return

    # Detect if GIF is from document or animation
    file = update.message.document or update.message.animation

    # Download the file from Telegram
    file_path = await context.bot.get_file(file.file_id)
    original_path = f"downloads/{file.file_name}"
    os.makedirs("downloads", exist_ok=True)
    await file_path.download_to_drive(original_path)

    logging.info(f"Downloaded GIF: {original_path}")

    # Compress GIF using ffmpeg if bigger than 8MB
    compressed_path = f"downloads/compressed_{file.file_name}"
    file_size = os.path.getsize(original_path)

    if file_size > MAX_FILE_SIZE:
        logging.info(f"Compressing GIF {file.file_name} ({file_size} bytes)")
        cmd = [
            "ffmpeg", "-y",
            "-i", original_path,
            "-vf", "scale=480:-1:flags=lanczos",
            "-b:v", "900k",
            compressed_path
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        compressed_path = original_path

    # Upload GIF to catbox.moe
    logging.info("Uploading GIF to catbox.moe...")
    with open(compressed_path, "rb") as f:
        response = requests.post(
            CATBOX_URL,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f}
        )

    if response.status_code == 200:
        catbox_url = response.text.strip()
        logging.info(f"GIF hosted at: {catbox_url}")

        # Send back the permanent link
        await update.message.reply_text(f"✅ Your GIF is ready:\n{catbox_url}")
    else:
        logging.error(f"Catbox upload failed: {response.text}")
        await update.message.reply_text("❌ Failed to upload GIF to catbox.moe.")

    # Cleanup
    try:
        os.remove(original_path)
        if os.path.exists(compressed_path) and compressed_path != original_path:
            os.remove(compressed_path)
    except Exception as e:
        logging.warning(f"Cleanup failed: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a GIF, and I'll host it on catbox.moe!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.Animation.ALL, handle_gif))
    app.run_polling()
