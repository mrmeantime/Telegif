#!/bin/bash
set -e

echo "Running debug script..."
echo "Current directory: $(pwd)"
echo "Files in current directory:"
ls -la

# Use relative path instead of absolute
exec python3 src/debug.py
