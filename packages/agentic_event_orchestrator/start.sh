#!/bin/bash
set -e

echo "Running AI database migrations..."
uv run python run_migrations.py

echo "Starting AI Orchestrator server..."
exec uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
