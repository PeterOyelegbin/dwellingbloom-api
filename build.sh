#!/bin/bash
# Exit on error
set -o errexit

# Install Python dependencies
echo "Installing dependencies..."
make install-deps

# # Try to install setuptools separately if needed
# pip install setuptools

# # Collect static files
# echo "Collecting static files..."
# python manage.py collectstatic --noinput --clear

# # Create the output directory Vercel expects
# mkdir -p dist

# # Optionally copy static files to dist if needed
# cp -r staticfiles/* dist/ 2>/dev/null || true

# Apply any outstanding database migrations
make run-migrations

# Start celery worker
make start-celery

echo "Build completed successfully!"
