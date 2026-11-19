#!/usr/bin/env bash
cd "$(dirname "$0")/../backend" && .venv/bin/python -m pytest -v && cd ../frontend && npm run typecheck
