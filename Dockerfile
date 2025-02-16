# Use Python 3.11 as base image
FROM python:3.11-slim

# Set timezone
ENV TZ=Asia/Hong_Kong
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Set non-root user
RUN useradd -m -r -u 1000 appuser

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/appuser/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and example config
COPY src/ src/
COPY data/config.example.json data/config.json

# Create necessary directories and set permissions
RUN mkdir -p logs data_export \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# HTTP service port
EXPOSE 5050

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5050/ || exit 1

# Start application
CMD ["python", "src/app.py"] 