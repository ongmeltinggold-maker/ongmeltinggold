#!/bin/sh
# entrypoint — เตรียมระบบก่อนรัน web (idempotent, รันซ้ำได้ปลอดภัย)
set -e

# รอ PostgreSQL พร้อม (รองรับทั้ง DATABASE_URL และ POSTGRES_* ผ่าน Django connection)
if [ -n "$DATABASE_URL" ] || [ -n "$POSTGRES_DB" ]; then
  echo "[entrypoint] รอ PostgreSQL ..."
  i=0
  until python -c "
import django, sys
django.setup()
from django.db import connection
try:
    connection.ensure_connection()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    i=$((i+1))
    if [ "$i" -ge 30 ]; then echo "[entrypoint] เชื่อม DB ไม่ได้ (timeout)"; exit 1; fi
    sleep 2
  done
  echo "[entrypoint] DB พร้อม"
fi

echo "[entrypoint] migrate ..."
python manage.py migrate --noinput

echo "[entrypoint] collectstatic ..."
python manage.py collectstatic --noinput

# seed master data ครั้งแรก (idempotent — get_or_create/update_or_create)
if [ "${RUN_SEED:-0}" = "1" ]; then
  echo "[entrypoint] seed master data + roles + features ..."
  python manage.py seed_data
  python manage.py setup_roles
  python manage.py seed_features
fi

echo "[entrypoint] เริ่มบริการ: $*"
exec "$@"
