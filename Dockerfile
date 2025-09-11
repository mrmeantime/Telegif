FROM python:3.11-slim

# Install ffmpeg for GIF/MP4 processing
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependencies and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run bot
CMD ["python3", "src/debug_startup.py"]
