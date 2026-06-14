#!/usr/bin/env bash
set -euo pipefail

export APP_ENV="${APP_ENV:-production}"
export RUN_STARTUP_SEEDERS="${RUN_STARTUP_SEEDERS:-false}"
export ENABLE_IN_PROCESS_WORKER="${ENABLE_IN_PROCESS_WORKER:-false}"

python -m alembic upgrade head
python scripts/validate_migrations.py
python -m uvicorn app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
