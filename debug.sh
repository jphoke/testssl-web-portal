#!/bin/bash
# Debug script for TestSSL Web Portal

echo "🔍 TestSSL Web Portal Debug Script"
echo "==============================="

# Check if Docker Compose is available
if docker compose version &> /dev/null; then
    DC="docker compose"
else
    DC="docker-compose"
fi

echo "1. Checking running services..."
$DC ps

echo -e "\n2. Checking worker logs (last 50 lines)..."
$DC logs worker --tail 50

echo -e "\n3. Checking for scan results..."
if [ -d "results" ]; then
    echo "Results directory contents:"
    ls -la results/
    
    # Show a sample JSON file if exists
    if ls results/*.json 1> /dev/null 2>&1; then
        echo -e "\nSample JSON result (first file):"
        FIRST_JSON=$(ls results/*.json | head -1)
        echo "File: $FIRST_JSON"
        if [ -f "$FIRST_JSON" ]; then
            echo "First 100 lines:"
            head -100 "$FIRST_JSON" | jq . 2>/dev/null || cat "$FIRST_JSON" | head -100
        fi
    fi
else
    echo "No results directory found"
fi

echo -e "\n4. Testing testssl.sh directly in container..."
$DC exec worker /opt/testssl.sh/testssl.sh --version 2>/dev/null || echo "Failed to run testssl.sh"

echo -e "\n5. Checking database for recent scans..."
$DC exec postgres psql -U ssluser -d ssltestportal -c "SELECT id, host, port, status, grade, created_at FROM scans ORDER BY created_at DESC LIMIT 5;" 2>/dev/null || echo "Failed to query database"

echo -e "\n6. Checking API health..."
curl -s http://localhost:8000/api/health | jq . 2>/dev/null || echo "API not responding"

echo -e "\n7. Container resource usage..."
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"