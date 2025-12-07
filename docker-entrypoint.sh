set -e

echo "=========================================="
echo "  LogPuls Backend Starting..."
echo "=========================================="
echo ""

echo "Waiting for MongoDB..."
until python -c "import pymongo; pymongo.MongoClient('mongodb://${MONGODB_HOST}:${MONGODB_PORT}', serverSelectionTimeoutMS=2000).admin.command('ping')" 2>/dev/null; do
    echo "  MongoDB not ready, waiting..."
    sleep 2
done
echo "✓ MongoDB is ready!"
echo ""

echo "Checking log collector service..."
if curl -s --connect-timeout 2 http://${LOG_COLLECTOR_HOST}:${LOG_COLLECTOR_PORT}/health > /dev/null 2>&1; then
    echo "✓ Log collector service is available!"
else
    echo "⚠ WARNING: Log collector service not found at ${LOG_COLLECTOR_HOST}:${LOG_COLLECTOR_PORT}"
    echo "  Log collection may not work until the service is running."
fi
echo ""

echo "Starting FastAPI application..."
exec "$@"
