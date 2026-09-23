#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

host="${HOST:-127.0.0.1}"
port="${PORT:-8000}"
echo "API: http://${host}:${port}"

if command -v uv >/dev/null 2>&1; then
  exec uv run uvicorn main:app --reload --host "$host" --port "$port"
fi

exec uvicorn main:app --reload --host "$host" --port "$port"
