#!/usr/bin/env bash
cd "$(dirname "$0")/.."
(cd backend && DATABASE_URL="${DEV_DATABASE_URL:-sqlite:///./agriconnect.db}" .venv/bin/python -m app.cli init-db && DATABASE_URL="${DEV_DATABASE_URL:-sqlite:///./agriconnect.db}" SEED_DEMO="${DEV_SEED_DEMO:-true}" BILLING_ENABLED="${DEV_BILLING_ENABLED:-false}" .venv/bin/python -m uvicorn app.main:app --reload --port 8000) &
B=$!; trap "kill $B" EXIT
cd frontend && npm run dev
