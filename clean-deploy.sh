#!/bin/bash
# Clean deployment script - removes everything and starts fresh

set -e

echo "🧹 TestSSL Web Portal - Clean Deployment"
echo "===================================="

# Check for Docker
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "❌ Docker Compose not found"
    exit 1
fi

echo "⚠️  This will remove all existing data!"
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

echo "1. Stopping all services..."
$DC down -v

echo "2. Removing old directories..."
rm -rf logs results sessions
rm -f .env

echo "3. Cleaning Docker artifacts..."
docker system prune -f

echo "4. Creating fresh .env file..."
cp .env.example .env
SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || echo "default-secret-key-$(date +%s)")
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env
else
    sed -i "s/your-secret-key-here-use-openssl-rand-hex-32/$SECRET_KEY/" .env
fi

# Prompt for secure database password
echo ""
echo "🔐 Database Password Setup"
echo "========================="
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
            echo "✅ Database password set successfully"
            break
        fi
    fi
done

echo "5. Creating directories..."
mkdir -p logs results

echo "6. Building fresh images..."
$DC build --no-cache

echo "7. Starting services..."
$DC up -d

echo "8. Waiting for services to be ready..."
sleep 15

echo "9. Checking service health..."
$DC ps

echo "10. Testing API..."
sleep 5
curl -s http://localhost:8000/api/health | jq . || echo "API not ready yet"

echo ""
echo "✅ Clean deployment complete!"
echo ""
echo "Access points:"
echo "  Web UI: http://localhost:3000"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "⚙️  Configuration Options:"
echo "  The .env file contains several configurable options:"
echo "  - WORKER_CONCURRENCY: Number of concurrent scans (default: 2)"
echo "  - SCAN_TIMEOUT: Timeout per scan in seconds (default: 300)"
echo "  - MAX_CONCURRENT_SCANS_PER_IP: Limit per IP (default: 2)"
echo "  - And more... see .env for all options"
echo ""
echo "  To modify settings:"
echo "  1. Edit .env file"
echo "  2. Restart services: docker compose restart"
echo ""
echo "Run ./debug.sh to check system status"