import os
import logging
import tempfile
import requests
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CATBOX_URL = "https://catbox.moe/user/api.php"
MAX_FILE_SIZE = 8 * 1024 * 1024  # 8MB for final output only

# --- Convert to GIF with size control ---
def convert_to_gif(input_path: str, output_path: str) -> str:
    """Convert any video to GIF and compress until <= 8MB."""
    logging.info("Converting to GIF: %s", input_path)

    # Start with high quality
    fps = 20
    scale = 640

    while True:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-vf", f"fps={fps},scale={scale}:-1:flags=lanczos",
            "-c:v", "gif",
            output_path
        ], check=True)

        size = os.path.getsize(output_path)
        logging.info("GIF size: %.2f MB", size / (1024 * 1024))

        if size <= MAX_FILE_SIZE:
            break

        # Reduce quality progressively until <8MB
        logging.warning("GIF too large, reducing quality...")
        if fps > 12:
            fps -= 2
        elif scale > 360:
            scale -= 80
        else:
            logging.error("Cannot compress GIF below 8MB without ruining quality.")
            break

    return output_path

# --- Upload to Catbox ---
def upload_to_catbox(file_path: str) -> str:
    """Uploads the GIF to Catbox and returns the direct link."""
    logging.info("Uploading GIF to Catbox: %s", file_path)

    with open(file_path, "rb") as f:
        response = requests.post(
            CATBOX_URL,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": f}
        )

    if response.status_code == 200:
        return response.text.strip()
    else:
        logging.error("Catbox upload failed: %s", response.text)
        raise Exception("Catbox upload failed")

# --- Handle Telegram media ---
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.message
        file = None

        # Telegram wraps GIFs as MP4 animations, but we also accept videos/docs
        if message.animation:
            file = await message.animation.get_file()
        elif message.video:
            file = await message.video.get_file()
        elif message.document:
            file = await message.document.get_file()
        else:
            await message.reply_text("⚠️ Unsupported file type.")
            return

        # Download the file to a temp folder
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "input")
            output_path = os.path.join(tmpdir, "output.gif")
            await file.download_to_drive(input_path)

            # Convert input → GIF
            gif_path = convert_to_gif(input_path, output_path)

            # Upload GIF to Catbox
            catbox_url = upload_to_catbox(gif_path)

            # Send Catbox link back
            await message.reply_text(f"✅ GIF uploaded:\n{catbox_url}")

    except Exception as e:
        logging.error("Error handling GIF: %s", e)
        await update.message.reply_text("❌ Failed to process GIF. Please try again later.")

# --- Start bot ---
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(
        filters.VIDEO | filters.Document.VIDEO | filters.ANIMATION,
        handle_gif
    ))
    logging.info("Starting Telegram GIF Bot...")
    app.run_polling()
