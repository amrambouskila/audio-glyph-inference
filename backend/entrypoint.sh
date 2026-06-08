#!/bin/sh
set -e

echo "Running database migrations (alembic upgrade head)..."
alembic upgrade head

echo "Starting uvicorn..."
exec uvicorn src.api.main:app --host 0.0.0.0 --port 8000
