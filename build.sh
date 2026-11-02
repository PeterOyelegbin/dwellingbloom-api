#!/bin/bash
# Exit on error
set -o errexit

# Create a virtual environment in the project directory
python3 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate

# Install Python dependencies
echo "Installing dependencies..."
uv pip install --system -r requirements.txt

# Apply any outstanding database migrations
echo "Applying database migrations..."
make run-migration

# start celery worker
echo "Starting Celery worker..."
make start-celery

echo "Build completed successfully!"
