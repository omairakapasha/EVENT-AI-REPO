#!/bin/bash
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI server..."
exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-5000} --workers 2
