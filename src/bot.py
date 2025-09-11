import os
import logging
import tempfile
import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
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

# Global variables for bot and event loop
bot = None
telegram_app = None
bot_loop = None
executor = ThreadPoolExecutor(max_workers=1)

def run_in_bot_thread(coro):
    """Run coroutine in the dedicated bot thread with proper event loop"""
    future = asyncio.run_coroutine_threadsafe(coro, bot_loop)
    return future.result(timeout=30)  # 30 second timeout

def init_bot():
    """Initialize bot in a separate thread with its own event loop"""
    global bot, telegram_app, bot_loop
    
    def bot_thread():
        global bot, telegram_app, bot_loop
        try:
            # Create new event loop for this thread
            bot_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(bot_loop)
            
            # Initialize bot and app
            bot = Bot(token=TELEGRAM_BOT_TOKEN)
            telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers
            telegram_app.add_handler(CommandHandler("start", start_command))
            telegram_app.add_handler(CommandHandler("help", help_command))
            telegram_app.add_handler(MessageHandler(
                filters.ANIMATION | filters.VIDEO | filters.Document.VIDEO | filters.TEXT, 
                handle_message
            ))
            
            logger.info("✅ Bot initialized successfully in dedicated thread")
            
            # Keep the event loop running
            bot_loop.run_forever()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize bot: {e}")
    
    # Start bot in separate thread
    bot_thread_obj = threading.Thread(target=bot_thread, daemon=True)
    bot_thread_obj.start()
    
    # Wait a moment for initialization
    import time
    time.sleep(2)

@app.route('/')
def health_check():
    return "🤖 Telegram GIF Bot is running with webhooks!", 200

@app.route('/health')
def health():
    bot_status = "connected" if bot else "error"
    return {
        "status": "healthy", 
        "service": "telegram-gif-bot", 
        "mode": "webhook",
        "bot_status": bot_status,
        "token_set": bool(TELEGRAM_BOT_TOKEN)
    }, 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhook from Telegram"""
    try:
        if not bot or not telegram_app or not bot_loop:
            logger.error("Bot not initialized")
            return "Bot not initialized", 500
            
        # Get the JSON data from Telegram
        json_data = request.get_json()
        
        if not json_data:
            return "No data", 400
            
        logger.info(f"Received webhook data")
        
        # Create Update object
        update = Update.de_json(json_data, bot)
        
        # Process the update in bot thread
        run_in_bot_thread(telegram_app.process_update(update))
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        return f"Error: {str(e)}", 500

@app.route('/set_webhook')
def set_webhook():
    """Endpoint to set up the webhook"""
    try:
        if not bot or not bot_loop:
            return {"error": "Bot not initialized", "token_set": bool(TELEGRAM_BOT_TOKEN)}, 500
        
        # Construct webhook URL
        service_url = "https://telegif.onrender.com"
        webhook_url = f"{service_url}/webhook"
        
        logger.info(f"Setting webhook to: {webhook_url}")
        
        # Set webhook using bot thread
        result = run_in_bot_thread(bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True
        ))
        
        logger.info(f"Webhook setup result: {result}")
        
        return {
            "success": True,
            "webhook_url": webhook_url,
            "result": result
        }, 200
        
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}", exc_info=True)
        return {
            "error": str(e),
            "token_set": bool(TELEGRAM_BOT_TOKEN),
            "bot_initialized": bool(bot)
        }, 500

@app.route('/webhook_info')
def webhook_info():
    """Get current webhook information"""
    try:
        if not bot or not bot_loop:
            return {"error": "Bot not initialized"}, 500
            
        webhook_info = run_in_bot_thread(bot.get_webhook_info())
        return {
            "url": webhook_info.url,
            "has_custom_certificate": webhook_info.has_custom_certificate,
            "pending_update_count": webhook_info.pending_update_count,
            "last_error_date": str(webhook_info.last_error_date) if webhook_info.last_error_date else None,
            "last_error_message": webhook_info.last_error_message,
            "max_connections": webhook_info.max_connections,
            "allowed_updates": webhook_info.allowed_updates
        }, 200
    except Exception as e:
        logger.error(f"Error getting webhook info: {e}")
        return {"error": str(e)}, 500

@app.route('/test_bot')
def test_bot():
    """Test if bot token is working"""
    try:
        if not bot or not bot_loop:
            return {"error": "Bot not initialized"}, 500
            
        me = run_in_bot_thread(bot.get_me())
        return {
            "bot_username": me.username,
            "bot_name": me.first_name,
            "bot_id": me.id,
            "token_working": True
        }, 200
    except Exception as e:
        logger.error(f"Bot test failed: {e}")
        return {"error": str(e), "token_working": False}, 500

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages - GIFs, videos, and text"""
    try:
        message = update.message
        
        # Handle text messages
        if message.text:
            if message.text.startswith('/'):
                return  # Let command handlers deal with commands
            await message.reply_text(f"✅ Webhook working! You said: {message.text}")
            return
        
        # Handle media messages (GIFs, videos, etc.)
        if message.animation or message.video or (message.document and message.document.mime_type and "video" in message.document.mime_type):
            await handle_gif(update, context)
        else:
            await message.reply_text("❌ Please send a GIF, video, or animation to convert!")
            
    except Exception as e:
        logger.error(f"Error in handle_message: {e}", exc_info=True)

async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'GIF' messages (actually MP4) and convert to real GIF"""
    try:
        message = update.message
        logger.info(f"Received media from user {message.from_user.id}")
        
        # Determine file type and get file object
        if message.animation:
            file_obj = message.animation
            logger.info(f"Received animation: {file_obj.file_name}, size: {file_obj.file_size} bytes")
        elif message.video:
            file_obj = message.video  
            logger.info(f"Received video: size: {file_obj.file_size} bytes")
        elif message.document and message.document.mime_type and "video" in message.document.mime_type:
            file_obj = message.document
            logger.info(f"Received document: {file_obj.file_name}, type: {file_obj.mime_type}")
        else:
            await message.reply_text("❌ Please send a GIF, video, or animation to convert!")
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
    # Initialize bot in separate thread
    init_bot()
    
    # Run Flask app
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting webhook server on port {port}")
    logger.info(f"Bot token set: {bool(TELEGRAM_BOT_TOKEN)}")
    app.run(host='0.0.0.0', port=port, debug=False)
