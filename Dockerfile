FROM python:3.12
WORKDIR /app

# Copy application files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port for health checks
EXPOSE 8000

# Set environment variables for better stability
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=UTF-8

# Run the bot with auto-restart on failure
CMD ["sh", "-c", "while true; do python bot.py; echo 'Bot crashed, restarting in 5 seconds...'; sleep 5; done"]