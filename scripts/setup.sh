#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
.venv/bin/python -m app.cli init-db
[ "$1" = "--demo" ] && .venv/bin/python -m app.cli seed-demo
cd ../frontend && npm install
