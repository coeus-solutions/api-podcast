#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Running database migrations..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run migrations using Alembic
alembic upgrade head

echo "Migrations completed successfully!" 