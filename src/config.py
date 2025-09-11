import os
import logging
import sys

logging.basicConfig(level=logging.INFO)

print("=== ENVIRONMENT DEBUG ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Check for bot token with both possible names
token1 = os.environ.get("TELEGRAM_BOT_TOKEN")
token2 = os.environ.get("TELEGRAM_TOKEN")

if token1:
    logging.info("✅ TELEGRAM_BOT_TOKEN is set")
    logging.info(f"First 10 chars: {token1[:10]}... (length={len(token1)})")
elif token2:
    logging.info("✅ TELEGRAM_TOKEN is set") 
    logging.info(f"First 10 chars: {token2[:10]}... (length={len(token2)})")
else:
    logging.error("❌ Neither TELEGRAM_BOT_TOKEN nor TELEGRAM_TOKEN is set!")
    logging.error("Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'TELEGRAM' in key.upper() or 'TOKEN' in key.upper():
            logging.error(f"  {key}: {os.environ[key][:10]}...")

print("=== DEBUG COMPLETE ===")

# Keep container alive for debugging
import time
logging.info("Keeping container alive for 60 seconds...")
time.sleep(60)
logging.info("Debug session complete.")
