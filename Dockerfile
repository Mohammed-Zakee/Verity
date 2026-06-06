FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set python stdout/stderr unbuffered
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy requirements from backend directory
COPY backend/requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code to app directory
COPY backend/ .

# Expose port (Railway will set PORT env var, but EXPOSE is good practice)
ENV PORT=5000
EXPOSE 5000

# Set start command using sh -c to guarantee environment variable expansion
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout 120"]
