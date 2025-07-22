#!/bin/bash
# Data cleanup script for SSL Test Portal
# This script removes historical scan data from the database
# FOR ADMINISTRATIVE USE ONLY - NOT EXPOSED IN UI/API

set -e

echo "🧹 SSL Test Portal - Data Cleanup Script"
echo "========================================"
echo "⚠️  WARNING: This will permanently delete scan history!"
echo ""

# Check for Docker Compose
if docker compose version &> /dev/null; then
    DC="docker compose"
elif command -v docker-compose &> /dev/null; then
    DC="docker-compose"
else
    echo "❌ Docker Compose not found"
    exit 1
fi

# Parse command line arguments
DAYS_TO_KEEP=30
DELETE_ALL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --all)
            DELETE_ALL=true
            shift
            ;;
        --days)
            DAYS_TO_KEEP="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --all           Delete ALL scan history (dangerous!)"
            echo "  --days N        Keep scans from last N days (default: 30)"
            echo "  --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                    # Keep last 30 days of scans"
            echo "  $0 --days 7           # Keep last 7 days of scans"
            echo "  $0 --all              # Delete all scan history"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Show what will be deleted
echo "Current database statistics:"
$DC exec postgres psql -U ssluser -d ssltestportal -t -c "SELECT COUNT(*) as total_scans FROM scans;" | xargs echo "Total scans:"

if [ "$DELETE_ALL" = true ]; then
    echo ""
    echo "🔴 You are about to DELETE ALL scan history!"
    $DC exec postgres psql -U ssluser -d ssltestportal -t -c "SELECT COUNT(*) FROM scans;" | xargs echo "Scans to delete:"
else
    echo ""
    echo "📅 Keeping scans from the last $DAYS_TO_KEEP days"
    $DC exec postgres psql -U ssluser -d ssltestportal -t -c "SELECT COUNT(*) FROM scans WHERE created_at < NOW() - INTERVAL '$DAYS_TO_KEEP days';" | xargs echo "Scans to delete:"
    $DC exec postgres psql -U ssluser -d ssltestportal -t -c "SELECT COUNT(*) FROM scans WHERE created_at >= NOW() - INTERVAL '$DAYS_TO_KEEP days';" | xargs echo "Scans to keep:"
fi

echo ""
read -p "Continue with cleanup? (yes/NO) " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Cleanup cancelled"
    exit 0
fi

# Perform cleanup
echo ""
echo "🗑️  Cleaning up data..."

if [ "$DELETE_ALL" = true ]; then
    # Delete all scans
    $DC exec postgres psql -U ssluser -d ssltestportal -c "DELETE FROM scans;"
    echo "✅ All scans deleted"
    
    # Clean up result files
    if [ -d "results" ]; then
        rm -f results/*.json
        echo "✅ Result files cleaned"
    fi
else
    # Get IDs of scans to delete
    echo "Finding old scans..."
    OLD_SCAN_IDS=$($DC exec postgres psql -U ssluser -d ssltestportal -t -A -c "SELECT id FROM scans WHERE created_at < NOW() - INTERVAL '$DAYS_TO_KEEP days';")
    
    if [ -n "$OLD_SCAN_IDS" ]; then
        # Delete old scans from database
        $DC exec postgres psql -U ssluser -d ssltestportal -c "DELETE FROM scans WHERE created_at < NOW() - INTERVAL '$DAYS_TO_KEEP days';"
        echo "✅ Old database records deleted"
        
        # Clean up corresponding result files
        if [ -d "results" ]; then
            echo "$OLD_SCAN_IDS" | while read -r scan_id; do
                if [ -n "$scan_id" ]; then
                    rm -f "results/${scan_id}.json"
                fi
            done
            echo "✅ Old result files cleaned"
        fi
    else
        echo "ℹ️  No old scans to delete"
    fi
fi

# Vacuum the database to reclaim space
echo ""
echo "🔧 Optimizing database..."
$DC exec postgres psql -U ssluser -d ssltestportal -c "VACUUM ANALYZE scans;"

# Show final statistics
echo ""
echo "📊 Final database statistics:"
$DC exec postgres psql -U ssluser -d ssltestportal -t -c "SELECT COUNT(*) as remaining_scans FROM scans;" | xargs echo "Remaining scans:"

# Show disk usage
echo ""
echo "💾 Disk usage:"
if [ -d "results" ]; then
    du -sh results/ | awk '{print "Result files: " $1}'
fi

echo ""
echo "✅ Cleanup completed!"