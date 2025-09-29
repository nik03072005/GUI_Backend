#!/usr/bin/env bash
# exit on error
set -o errexit

echo "🚀 Starting build process..."

# Navigate to backend directory
cd backend

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "🗃️ Running database migrations..."
python manage.py migrate --no-input

echo "📊 Collecting static files..."
python manage.py collectstatic --no-input --clear

echo "✅ Build completed successfully!"
