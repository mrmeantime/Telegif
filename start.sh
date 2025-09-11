#!/bin/bash
set -e

echo "Starting Telegram GIF Bot..."
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Run the actual bot instead of debug script
exec python3 src/bot.py
