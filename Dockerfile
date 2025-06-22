# 🔒 PROPRIETARY SOFTWARE - NewsBot Docker Image
# 
# This is proprietary software for private use only.
# Unauthorized copying, distribution, or use is strictly prohibited.
# 
# Copyright (c) 2025 NewsBot Project. All rights reserved.
# Syrian Discord News Aggregation Bot - CONFIDENTIAL

# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-production.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-production.txt

# Create non-root user for security
RUN groupadd -r newsbot && useradd -r -g newsbot newsbot

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p logs data/cache data/sessions && \
    chown -R newsbot:newsbot /app

# Switch to non-root user
USER newsbot

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health', timeout=5)" || exit 1

# Expose health check port
EXPOSE 8080

# Run the application
CMD ["python", "run.py"] 