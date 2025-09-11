import os
import logging
import tempfile
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from src.ffmpeg_utils import convert_to_gif
from src.uploader import upload_to_catbox

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get bot token from environment
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN is missing!")

# Create Flask app
app = Flask(__name__)

# Initialize bot and application
bot = Bot(token=TELEGRAM_BOT_TOKEN)
telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

@app.route('/')
def health_check():
    return "🤖 Telegram GIF Bot is running with webhooks!", 200

@app.route('/health')
def health():
    return {"status": "healthy", "service": "telegram-gif-bot", "mode": "webhook"}, 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook from Telegram"""
    try:
        # Get the JSON data from Telegram
        json_data = request.get_json()
        
        if not json_data:
            return "No data", 400
            
        logger.info(f"Received webhook data: {json_data}")
        
        # Create Update object
        update = Update.de_json(json_data, bot)
        
        # Process the update asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(telegram_app.process_update(update))
        loop.close()
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return "Error", 500

@app.route('/set_webhook')
def set_webhook():
    """Endpoint to set up the webhook"""
    try:
        # Get the service URL from Render environment
        service_url = os.environ.get('RENDER_EXTERNAL_URL')
        if not service_url:
            return {"error": "RENDER_EXTERNAL_URL not found"}, 400
            
        webhook_url = f"{service_url}/webhook"
        
        # Set webhook
        result = bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook setup result: {result}")
        
        return {
            "success": True,
            "webhook_url": webhook_url,
            "result": result
        }, 200
        
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")
        return {"error": str(e)}, 500

@app.route('/webhook_info')
def webhook_info():
    """Get current webhook information"""
    try:
        webhook_info = bot.get_webhook_info()
        return {
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": webhook_info.last_error_date,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates
        }, 200
    except Exception as e:
        return {"error": str(e)}, 500

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'GIF' messages (actually MP4) and convert to real GIF"""
    try:
        message = update.message
        logger.info(f"Received message from user {message.from_user.id}")
        
        # Check if it's a GIF/animation (which Telegram stores as MP4)
        if message.animation:
            file_obj = message.animation
            logger.info(f"Received animation: {file_obj.file_name}, size: {file_obj.file_size} bytes")
        elif message.video:
            file_obj = message.video  
            logger.info(f"Received video: size: {file_obj.file_size} bytes")
        elif message.document and message.document.mime_type:
            if "video" in message.document.mime_type or "gif" in message.document.mime_type:
                file_obj = message.document
                logger.info(f"Received document: {file_obj.file_name}, type: {file_obj.mime_type}")
            else:
                await message.reply_text("❌ Please send a GIF, video, or animation to convert!")
                return
        else:
            await message.reply_text("❌ Please send a GIF or video to convert!")
            return

        # Check file size (Telegram max is 50MB for bots)
        if file_obj.file_size > 50 * 1024 * 1024:
            await message.reply_text("❌ File too large! Please send a file smaller than 50MB.")
            return

        await message.reply_text("🔄 Converting to GIF and uploading to Catbox...")
        
        # Download file
        file = await context.bot.get_file(file_obj.file_id)
        
        # Create temporary file for input
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_input_path = temp_file.name
            
        # Download to temp file
        await file.download_to_drive(temp_input_path)
        logger.info(f"Downloaded file to: {temp_input_path}")
        
        # Convert to GIF (this will ensure it's under 8MB)
        logger.info("Converting MP4 to GIF...")
        gif_path = await convert_to_gif(temp_input_path)
        
        # Check final GIF size
        gif_size_mb = os.path.getsize(gif_path) / (1024 * 1024)
        logger.info(f"GIF created: {gif_path}, size: {gif_size_mb:.2f}MB")
        
        # Upload to Catbox
        logger.info("Uploading to Catbox.moe...")
        catbox_url = upload_to_catbox(gif_path)
        
        if catbox_url:
            await message.reply_text(f"✅ **GIF converted and uploaded!**\n\n🔗 {catbox_url}")
            logger.info(f"Successfully uploaded to: {catbox_url}")
        else:
            await message.reply_text("❌ Upload to Catbox failed. Please try again later.")
        
        # Cleanup temp files
        try:
            os.unlink(temp_input_path)
            os.unlink(gif_path)
            logger.info("Cleaned up temporary files")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            
    except Exception as e:
        logger.error(f"Error processing GIF: {e}", exc_info=True)
        await message.reply_text("❌ Sorry, there was an error converting your GIF. Please try again.")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    logger.info(f"Start command from user {update.message.from_user.id}")
    welcome_text = """
🎬 **Telegram GIF Converter Bot**

Send me a GIF (or video) and I'll convert it to a real GIF file and upload it to Catbox!

📝 **How it works:**
1. Send me a GIF/video
2. I convert it to optimized GIF (under 8MB)  
3. Upload to Catbox.moe
4. Get your permanent link!

🚀 **Just send me a GIF to get started!**
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
ℹ️ **Help**

**Supported formats:**
• GIFs (Telegram animations)
• MP4 videos  
• Other video formats

**Limits:**
• Max input size: 50MB
• Output GIF: Under 8MB (automatically optimized)

**Commands:**
/start - Welcome message
/help - This help message

Just send me any GIF or video to convert! 🎬
    """
    await update.message.reply_text(help_text)

if __name__ == "__main__":
    # Add handlers to telegram app
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(MessageHandler(
        filters.ANIMATION | filters.VIDEO | filters.Document.VIDEO, 
        handle_gif
    ))
    
    # Run Flask app
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting webhook server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
