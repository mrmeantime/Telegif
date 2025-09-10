FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot code
COPY src/ src/

# Copy start script
COPY start.sh .
RUN chmod +x start.sh

# Start bot
CMD ["./start.sh"]
