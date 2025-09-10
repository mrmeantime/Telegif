import os

# Read token from environment variable (Render dashboard)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Server details for uploading GIFs
UPLOAD_SERVER = "https://your-upload-api.render.com"
CAT_HOST = "https://cat.yourdomain.com"  # Change this to your CAT hosting URL
MAX_FILESIZE_MB = 8
