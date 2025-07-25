#!/bin/bash
# Deploy script for TestSSL Web Portal

set -e

echo "🚀 TestSSL Web Portal - Deployment Script"
echo "====================================="

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

# Check for Docker Compose
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "❌ Docker Compose is not installed"
    exit 1
fi

# Create .env file if needed
if [ ! -f .env ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    
    # Generate secret key
    SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "default-secret-key-$(date +%s)")
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env
    else
        sed -i "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env
    fi
fi

# Check database password
source .env
if [ -z "$DB_PASSWORD" ] || [ "$DB_PASSWORD" = "changeme" ] || [ "$DB_PASSWORD" = "changeme123" ]; then
    echo ""
    echo "⚠️  Insecure database password detected!"
    echo "Please enter a secure database password (minimum 12 characters):"
    while true; do
        read -s -p "Password: " DB_PASSWORD_NEW
        echo
        if [ ${#DB_PASSWORD_NEW} -lt 12 ]; then
            echo "❌ Password must be at least 12 characters long. Try again."
        else
            read -s -p "Confirm password: " DB_PASSWORD_CONFIRM
            echo
            if [ "$DB_PASSWORD_NEW" != "$DB_PASSWORD_CONFIRM" ]; then
                echo "❌ Passwords don't match. Try again."
            else
                # Update .env file
                if [[ "$OSTYPE" == "darwin"* ]]; then
                    sed -i '' "s/^DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD_NEW/" .env
                else
                    sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$DB_PASSWORD_NEW/" .env
                fi
                echo "✅ Database password updated successfully"
                break
            fi
        fi
    done
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p logs results

# Build and start services
echo "🐳 Building services..."
$DC build

echo "🚀 Starting services..."
$DC up -d

# Wait for services
echo "⏳ Waiting for services to start..."
sleep 10

# Check health
echo "🔍 Checking service health..."
$DC ps

# Test API
echo "🧪 Testing API..."
curl -s http://localhost:8000/api/health | jq . || echo "API test failed"

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Access points:"
echo "   Web Interface: http://localhost:3000"
echo "   API: http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "📋 Commands:"
echo "   View logs: $DC logs -f"
echo "   Stop: $DC down"
echo "   Restart: $DC restart"
echo ""
echo "⚙️  Configuration Options:"
echo "   The .env file contains several configurable options:"
echo "   - WORKER_CONCURRENCY: Number of concurrent scans (default: 2)"
echo "   - SCAN_TIMEOUT: Timeout per scan in seconds (default: 600)"
echo "   - MAX_CONCURRENT_SCANS_PER_IP: Limit per IP (default: 2)"
echo "   - And more... see .env for all options"
echo ""
echo "   To modify settings:"
echo "   1. Edit .env file"
echo "   2. Restart services: $DC restart"
echo ""
echo "🔒 To scan a host:"
echo "   1. Open http://localhost:3000"
echo "   2. Enter hostname and port"
echo "   3. Click 'Start Scan'"