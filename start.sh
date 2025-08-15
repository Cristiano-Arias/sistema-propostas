#!/usr/bin/env bash
set -e
export FLASK_APP=wsgi.py
echo "[start] Running database migrations..."
set +e
flask db upgrade
if [ $? -ne 0 ]; then
  echo "[start] No migrations found; initializing Alembic."
  flask db init
  flask db migrate -m "init schema"
  flask db upgrade
fi
set -e
echo "[start] Starting gunicorn..."
exec gunicorn wsgi:app
