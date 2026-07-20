#!/bin/sh
# กู้คืนข้อมูลจากไฟล์สำรอง
# ใช้ (รันบนเครื่อง host จากโฟลเดอร์ ong_system/):
#   sh deploy/scripts/restore.sh deploy/backups/db_YYYYMMDD_HHMMSS.dump [deploy/backups/media_....tar.gz]
#
# *** คำเตือน: จะเขียนทับข้อมูลปัจจุบันทั้งหมด — ทำตอนปิดใช้งาน + สำรองก่อนเสมอ ***
set -e

DUMP="$1"
MEDIA="$2"
if [ -z "$DUMP" ]; then
  echo "ใช้: sh restore.sh <db_dump> [media_tar.gz]"; exit 1
fi

COMPOSE="docker compose -f deploy/docker-compose.yml --env-file deploy/.env"

echo "[restore] คัดลอกไฟล์ dump เข้า container db ..."
$COMPOSE cp "$DUMP" db:/tmp/restore.dump

echo "[restore] ปิดการเชื่อมต่อ + สร้างฐานข้อมูลใหม่ ..."
$COMPOSE exec -T db sh -c '
  export PGPASSWORD="$POSTGRES_PASSWORD"
  psql -U "$POSTGRES_USER" -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='"'"'$POSTGRES_DB'"'"' AND pid<>pg_backend_pid();"
  dropdb -U "$POSTGRES_USER" --if-exists "$POSTGRES_DB"
  createdb -U "$POSTGRES_USER" "$POSTGRES_DB"
  pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner /tmp/restore.dump
  rm -f /tmp/restore.dump
'
echo "[restore] ✔ กู้ฐานข้อมูลสำเร็จ"

if [ -n "$MEDIA" ] && [ -f "$MEDIA" ]; then
  echo "[restore] กู้ media ..."
  $COMPOSE cp "$MEDIA" web:/tmp/media.tar.gz
  $COMPOSE exec -T web sh -c 'cd /app && tar -xzf /tmp/media.tar.gz && rm -f /tmp/media.tar.gz'
  echo "[restore] ✔ กู้ media สำเร็จ"
fi

echo "[restore] รีสตาร์ท web ..."
$COMPOSE restart web
echo "[restore] เสร็จสมบูรณ์"
