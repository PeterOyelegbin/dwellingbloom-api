#!/bin/bash
# Exit on error
set -o errexit

# Install Python dependencies
echo "Installing dependencies..."
make install-deps

# Apply any outstanding database migrations
make run-migration

echo "Build completed successfully!"
