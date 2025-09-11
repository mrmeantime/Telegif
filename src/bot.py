import os
import logging
import tempfile
import asyncio
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

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

# Initialize bot
try:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    logger.info("✅ Bot initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize bot: {e}")
    bot = None
    telegram_app = None

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
        if not bot or not telegram_app:
            logger.error("Bot not initialized")
            return "Bot not initialized", 500
            
        # Get the JSON data from Telegram
        json_data = request.get_json()
        
        if not json_data:
            return "No data", 400
            
        logger.info(f"Received webhook: {json_data.get('message', {}).get('text', 'media')}")
        
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
        return f"Error: {str(e)}", 500

@app.route('/set_webhook')
def set_webhook():
    """Endpoint to set up the webhook"""
    try:
        if not bot:
            return {"error": "Bot not initialized", "token_set": bool(TELEGRAM_BOT_TOKEN)}, 500
        
        # Try different ways to get the service URL
        service_url = None
        
        # Method 1: Render environment variable
        service_url = os.environ.get('RENDER_EXTERNAL_URL')
        
        # Method 2: Construct from request
        if not service_url:
            service_url = f"https://{request.host}"
            
        # Method 3: Hard-code for your service
        if not service_url or 'localhost' in service_url:
            service_url = "https://telegif.onrender.com"
        
        webhook_url = f"{service_url}/webhook"
        
        logger.info(f"Setting webhook to: {webhook_url}")
        
        # Set webhook with better error handling
        result = bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True  # Clear any pending updates
        )
        
        logger.info(f"Webhook setup result: {result}")
        
        return {
            "success": True,
            "webhook_url": webhook_url,
            "result": result,
            "service_url_source": "constructed" if not os.environ.get('RENDER_EXTERNAL_URL') else "env_var"
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
        if not bot:
            return {"error": "Bot not initialized"}, 500
            
        webhook_info = bot.get_webhook_info()
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
        if not bot:
            return {"error": "Bot not initialized"}, 500
            
        me = bot.get_me()
        return {
            "bot_username": me.username,
            "bot_name": me.first_name,
            "bot_id": me.id,
            "token_working": True
        }, 200
    except Exception as e:
        logger.error(f"Bot test failed: {e}")
        return {"error": str(e), "token_working": False}, 500

# Your existing handler functions here...
async def handle_gif(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'GIF' messages - simplified for now"""
    try:
        message = update.message
        await message.reply_text("🔄 GIF processing is working! (Webhook successful)")
        logger.info(f"Successfully processed message from {message.from_user.id}")
    except Exception as e:
        logger.error(f"Error in handle_gif: {e}")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    welcome_text = """
🎬 **Telegram GIF Converter Bot**

✅ Webhook mode active!
Send me a GIF to test the conversion.
    """
    await update.message.reply_text(welcome_text)

if __name__ == "__main__":
    # Add handlers to telegram app
    if telegram_app:
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(MessageHandler(
            filters.ANIMATION | filters.VIDEO | filters.Document.VIDEO | filters.TEXT, 
            handle_gif
        ))
    
    # Run Flask app
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting webhook server on port {port}")
    logger.info(f"Bot token set: {bool(TELEGRAM_BOT_TOKEN)}")
    app.run(host='0.0.0.0', port=port, debug=False)
