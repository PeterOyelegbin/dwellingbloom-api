#!/bin/bash
# Exit on error
set -o errexit

# Install Python dependencies
# echo "Installing dependencies..."
# make install-deps

# Apply any outstanding database migrations
echo "Applying database migrations..."
make run-migration

# start celery worker
echo "Starting Celery worker..."
make start-celery

echo "Build completed successfully!"
