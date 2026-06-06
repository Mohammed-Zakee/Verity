FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set python stdout/stderr unbuffered
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application files
COPY . .

# Gunicorn start command binding to PORT environment variable
CMD gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
