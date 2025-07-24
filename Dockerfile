FROM python:3.13-slim

# Install system dependencies including hexdump and other tools needed by testssl.sh
RUN apt-get update && apt-get install -y \
    curl \
    git \
    build-essential \
    bsdmainutils \
    dnsutils \
    net-tools \
    procps \
    openssl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install testssl.sh from official repository
RUN git clone --depth 1 https://github.com/testssl/testssl.sh.git /opt/testssl.sh && \
    chmod +x /opt/testssl.sh/testssl.sh

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs results

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]