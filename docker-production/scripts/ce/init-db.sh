#!/bin/bash
set -euo pipefail

export PGPASSWORD=prodpass

until psql -h postgres -p 5432 -U produser -d postgres -c 'SELECT 1' >/dev/null 2>&1; do
  echo 'Waiting for postgres to be ready...'
  sleep 2
done

if ! psql -h postgres -p 5432 -U produser -d postgres -tAc \
  "SELECT 1 FROM pg_database WHERE datname = 'feiyu-ce'" | grep -q 1; then
  psql -h postgres -p 5432 -U produser -d postgres \
    -c 'CREATE DATABASE "feiyu-ce";'
fi

exec uvicorn feiyu_app.app:app --port 8423 --host 0.0.0.0
