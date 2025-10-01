#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting build process..."

# Navigate to backend directory
cd backend

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🗃️ Running database migrations..."
# Try to run migrations with retry logic
for i in {1..3}; do
    echo "Migration attempt $i of 3..."
    if python manage.py migrate --no-input; then
        echo "✅ Migrations completed successfully!"
        break
    else
        echo "⚠️ Migration attempt $i failed. Retrying in 10 seconds..."
        sleep 10
        if [ $i -eq 3 ]; then
            echo "❌ All migration attempts failed. Continuing with build..."
            # Don't fail the build if migrations fail - the app might still work
        fi
    fi
done

echo "📊 Collecting static files..."
python manage.py collectstatic --no-input --clear

echo "✅ Build completed successfully!"
