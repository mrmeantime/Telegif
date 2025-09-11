import os
import logging

logging.basicConfig(level=logging.INFO)

token = os.environ.get("TELEGRAM_TOKEN")

if token:
    logging.info("✅ TELEGRAM_TOKEN is set")
    logging.info(f"First 10 chars: {token[:10]}... (length={len(token)})")
else:
    logging.error("❌ TELEGRAM_TOKEN is missing!")

# Keep container alive for debugging
import time
while True:
    time.sleep(30)
