FROM python:3.10-slim

WORKDIR /app

# Install dependencies first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY DMbotfly.py .
#COPY GTbotfly.py . # if you want to run the bot in a private group

# Run the bot
CMD ["python", "DMbotfly.py"]
#CMD ["python", "GTbotfly.py"] # if you want to run the bot in a private group
