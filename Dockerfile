# Use slim Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Ensure start.sh is executable
RUN chmod +x /app/start.sh

# Install dependencies if you need any (optional for debug)
# RUN pip install -r requirements.txt

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Run start.sh
CMD ["/app/start.sh"]
