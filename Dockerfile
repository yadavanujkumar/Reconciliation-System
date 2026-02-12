# NeuroRecon Dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY neurorecon/ ./neurorecon/
COPY data/ ./data/
COPY main.py .
COPY config.yaml .

# Create necessary directories
RUN mkdir -p data/input data/output logs

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV NEURORECON_ENV=production

# Expose port (if needed for future API)
EXPOSE 8000

# Set entrypoint
CMD ["python", "main.py"]
