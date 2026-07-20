#!/bin/sh
# สำรองข้อมูล: pg_dump (ฐานข้อมูล) + tar (media รูปบัตร/ชิ้นงาน)
# เก็บใน /backups หมุนเวียนตาม BACKUP_KEEP_DAYS
set -e

TS=$(TZ=Asia/Bangkok date +%Y%m%d_%H%M%S)
OUT=/backups
KEEP=${BACKUP_KEEP_DAYS:-14}
mkdir -p "$OUT"

echo "[backup] $TS เริ่มสำรองข้อมูล ..."

# 1) ฐานข้อมูล (custom format, บีบอัด, กู้ด้วย pg_restore)
export PGPASSWORD="$POSTGRES_PASSWORD"
pg_dump -h "${POSTGRES_HOST:-db}" -p "${POSTGRES_PORT:-5432}" \
        -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
        -f "$OUT/db_${TS}.dump"
echo "[backup] ✔ ฐานข้อมูล -> db_${TS}.dump"

# 2) media (ถ้ามี)
if [ -d /app/media ] && [ "$(ls -A /app/media 2>/dev/null)" ]; then
  tar -czf "$OUT/media_${TS}.tar.gz" -C /app media
  echo "[backup] ✔ media -> media_${TS}.tar.gz"
fi

# 3) หมุนเวียน ลบไฟล์เก่ากว่า KEEP วัน
find "$OUT" -name 'db_*.dump' -mtime +"$KEEP" -delete 2>/dev/null || true
find "$OUT" -name 'media_*.tar.gz' -mtime +"$KEEP" -delete 2>/dev/null || true

echo "[backup] เสร็จ. ไฟล์ปัจจุบัน:"
ls -lh "$OUT" | tail -n +2
