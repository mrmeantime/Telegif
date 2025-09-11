import os

# Read token from environment variable (Render dashboard)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Catbox.moe is free and doesn't need API keys
CATBOX_UPLOAD_URL = "https://catbox.moe/user/api.php"

# GIF size limit (for Telegram compatibility)  
MAX_FILESIZE_MB = 8

# Temp directory for processing
TEMP_DIR = "/tmp" if os.path.exists("/tmp") else "./temp"
