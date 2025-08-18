FROM python:3.11-slim

WORKDIR /app
RUN mkdir -p /app 

# Install system dependencies
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p templates static logs utils

# Copy application files
COPY app/log_viewer.py ./app/
COPY app/templates/ ./app/templates/
COPY app/static/ ./app/static/
#COPY utils/logging_config.py ./utils/ --файл остался в ./bot/utils


# Create non-root user for security
RUN useradd -m -u 1000 logviewer && \
    chown -R logviewer:logviewer /app
USER logviewer

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "app/log_viewer.py"]