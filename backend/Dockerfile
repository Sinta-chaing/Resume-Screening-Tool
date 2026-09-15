# Use official Python base image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies for PDF/OCR (PyMuPDF, rapidocr, onnxruntime)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libxml2 \
    curl \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy project code
COPY . .

# Wait-for-db helper: exits when PostgreSQL accepts connections (up to 60s)
COPY scripts/docker-wait-for-db.sh /usr/local/bin/wait-for-db
RUN chmod +x /usr/local/bin/wait-for-db

# Collect static files if needed (optional)
# RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run the app with Gunicorn (waits for DB, migrates, then serves)
CMD ["/bin/sh", "-c", "wait-for-db && python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --timeout 600 --workers 2 --worker-class gthread --threads 4"]