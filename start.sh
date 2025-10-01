#!/usr/bin/env bash

echo "🚀 Starting ISRO Backend Server..."

cd backend

# Wait for database to be ready (with timeout)
echo "⏳ Waiting for database connection..."
for i in {1..30}; do
    if python manage.py check --database default 2>/dev/null; then
        echo "✅ Database connection established!"
        break
    else
        echo "⏳ Waiting for database... ($i/30)"
        sleep 2
        if [ $i -eq 30 ]; then
            echo "⚠️ Database not ready, starting server anyway..."
        fi
    fi
done

# Run any pending migrations
echo "🗃️ Applying database migrations..."
python manage.py migrate --no-input 2>/dev/null || echo "⚠️ Migrations failed, continuing..."

# Start the server
echo "🌐 Starting Gunicorn server..."
exec gunicorn backend.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} \
    --workers 2 \
    --timeout 120 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --preload \
    --log-level info \
    --access-logfile - \
    --error-logfile -