FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including cron
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    cron \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set env vars
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application code FIRST
COPY . /app/

# Create log directory AFTER copying
RUN mkdir -p /app/logs

COPY start.sh /start.sh
RUN chmod +x /start.sh

EXPOSE 8000

# Set the command to our new script
CMD ["/start.sh"]