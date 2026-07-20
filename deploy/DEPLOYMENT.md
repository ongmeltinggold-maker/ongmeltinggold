# คู่มือติดตั้ง Production — ระบบร้านทอง ONG หลอมทอง
### Docker + PostgreSQL + Nginx + สำรองข้อมูลอัตโนมัติ

เอกสารนี้อธิบายการนำระบบขึ้นเซิร์ฟเวอร์จริง ตั้งแต่ศูนย์จนใช้งานได้ รวมการย้ายข้อมูลเดิม (Phase 3), HTTPS, สำรอง/กู้คืน และการต่อเครื่องอ่านบัตร

---

## 1. ภาพรวมสถาปัตยกรรม

```
                    (อินเทอร์เน็ต / วง LAN ร้าน)
                              │  HTTPS
                       ┌──────▼───────┐
                       │    nginx     │  :80 /:443  (reverse proxy, เสิร์ฟ static/media)
                       └──────┬───────┘
                              │  proxy
                       ┌──────▼───────┐   ┌───────────────┐
                       │  web (Django │   │  backup       │  pg_dump + media ทุกวัน
                       │  + gunicorn) │   │  (postgres)   │
                       └──────┬───────┘   └──────┬────────┘
                              │  psycopg          │
                       ┌──────▼───────────────────▼──────┐
                       │        db (PostgreSQL 16)        │  volume: pgdata
                       └──────────────────────────────────┘

เครื่องอ่านบัตร: รันแยกที่ "เครื่อง POS หน้าร้าน" (bridge/card_reader.py) — ไม่อยู่ใน Docker
```

4 บริการใน Docker: **db** (PostgreSQL), **web** (Django+gunicorn), **nginx** (proxy+static), **backup** (สำรองอัตโนมัติ)

---

## 2. สิ่งที่ต้องเตรียม (Prerequisites)

- เซิร์ฟเวอร์ Linux (Ubuntu 22.04+ แนะนำ) หรือเครื่องในร้านที่เปิดตลอด · RAM ≥ 2GB · ดิสก์ ≥ 20GB
- ติดตั้ง **Docker Engine + Docker Compose plugin** ([docs.docker.com/engine/install](https://docs.docker.com/engine/install/))
- (ถ้าเปิดออกอินเทอร์เน็ต) โดเมน + ใบรับรอง TLS (Let's Encrypt ฟรี)
- ไฟล์โปรเจกต์ `ong_system/` (จาก `ONG_NewSystem_Phase3.tar.gz`)
- ไฟล์ข้อมูลย้าย (ถ้าจะ migrate): `customers_legacy.json`, `pawn_contracts_legacy.json`, `cutover_stock.json` วางใน `ong_system/migration/`

---

## 3. ติดตั้งครั้งแรก (Quick start)

```bash
# 1) แตกไฟล์โปรเจกต์
tar -xzf ONG_NewSystem_Phase3.tar.gz
cd ong_system

# 2) สร้างไฟล์ตั้งค่า
cp deploy/.env.example deploy/.env

# 3) สร้าง SECRET_KEY แล้วนำไปใส่ใน deploy/.env
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
#   แก้ deploy/.env:  DJANGO_SECRET_KEY, POSTGRES_PASSWORD, DJANGO_ALLOWED_HOSTS, โดเมน
#   ครั้งแรกให้ตั้ง RUN_SEED=1 (เพื่อ seed master data อัตโนมัติ)

# 4) build + start
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build

# 5) ดูสถานะ + log
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f web
```

เปิดเบราว์เซอร์ที่ `http://<ip-เซิร์ฟเวอร์>/` → เข้าหน้า login ได้ = สำเร็จ

> หลังรันครั้งแรกเสร็จ ให้ตั้ง `RUN_SEED=0` ใน `.env` เพื่อไม่ให้ seed ซ้ำทุกครั้งที่รีสตาร์ท

### สร้างผู้ใช้ผู้ดูแล (superuser)
```bash
docker compose -f deploy/docker-compose.yml exec web python manage.py createsuperuser
```

---

## 4. ย้ายข้อมูลเดิม (Migration — Phase 3)

วางไฟล์ข้อมูลใน `ong_system/migration/` แล้วรัน (อ่านรายละเอียดใน `ONG_Phase3_Migration_Reconcile`):

```bash
CMD="docker compose -f deploy/docker-compose.yml exec web python manage.py"
$CMD import_legacy migration/customers_legacy.json          # ลูกค้า 197 ราย
$CMD import_legacy_contracts migration/pawn_contracts_legacy.json   # สัญญาขายฝากค้าง
$CMD set_cutover_stock migration/cutover_stock.json         # สต็อกยกยอด
```

ทุกคำสั่งมี `--dry-run` ให้ทดลองก่อน · **ก่อน go-live จริง**: ดึงยอดสต็อก + นับจริงวัน cutover แล้วแก้ `cutover_stock.json`

---

## 5. เปิด HTTPS (แนะนำมากถ้าเข้าถึงจากนอกวง LAN)

**ตัวเลือก A — Let's Encrypt (ฟรี, ต่ออายุอัตโนมัติ):** ใช้ certbot ออกใบรับรอง แล้ววางที่ `deploy/nginx/certs/` (`fullchain.pem`, `privkey.pem`)

**ตัวเลือก B — ใบรับรองที่มีอยู่:** วางไฟล์ทั้งสองใน `deploy/nginx/certs/`

จากนั้น:
```bash
cp deploy/nginx/nginx-https.conf.example deploy/nginx/nginx.conf   # แก้ server_name เป็นโดเมนจริง
# เปิด HSTS ใน .env เมื่อ HTTPS นิ่งแล้ว:  DJANGO_HSTS_SECONDS=2592000
docker compose -f deploy/docker-compose.yml restart nginx web
```

---

## 6. สำรองข้อมูล & กู้คืน

### อัตโนมัติ
บริการ `backup` ทำ `pg_dump` (ฐานข้อมูล) + `tar` (media รูปบัตร/ชิ้นงาน) **ทุกวันเวลา `BACKUP_HOUR`** (Asia/Bangkok) เก็บใน `deploy/backups/` และลบไฟล์เก่ากว่า `BACKUP_KEEP_DAYS` อัตโนมัติ

### สำรองด้วยมือ (ทันที)
```bash
docker compose -f deploy/docker-compose.yml exec backup sh /backup.sh
```

### กู้คืน (⚠ เขียนทับข้อมูลปัจจุบัน — สำรองก่อนเสมอ)
```bash
sh deploy/scripts/restore.sh deploy/backups/db_YYYYMMDD_HHMMSS.dump \
   deploy/backups/media_YYYYMMDD_HHMMSS.tar.gz
```

> **สำคัญ:** คัดลอกไฟล์ใน `deploy/backups/` ไปเก็บนอกเครื่อง (cloud/ฮาร์ดดิสก์แยก) เป็นระยะ — กันเซิร์ฟเวอร์เสีย

---

## 7. เครื่องอ่านบัตรประชาชน (Card Reader Bridge)

เครื่องอ่านบัตรต่อ USB ที่ **เครื่อง POS หน้าร้าน** (ไม่ใช่ในเซิร์ฟเวอร์/Docker) — ดู `bridge/README.md`:
```bash
# บนเครื่อง POS (Windows/Mac/Linux)
pip install pyscard
python bridge/card_reader.py          # เปิดบริการที่ localhost:8765
# ทดสอบไม่มีเครื่องจริง:  python bridge/card_reader.py --mock
```
หน้า KYC มีปุ่ม "🪪 อ่านบัตร" เรียกอ่านชิปมาเติมฟอร์มอัตโนมัติ

---

## 8. งานดูแลประจำ (Operations)

| งาน | คำสั่ง |
|---|---|
| ดู log | `docker compose -f deploy/docker-compose.yml logs -f web` |
| รีสตาร์ท | `docker compose -f deploy/docker-compose.yml restart web` |
| อัปเดตโค้ดใหม่ | แทนที่ไฟล์ → `... up -d --build web` |
| เข้า shell จัดการ | `docker compose ... exec web python manage.py shell` |
| ตรวจสุขภาพระบบ | เปิด `http://<host>/healthz/` → `{"status":"ok"}` |
| หยุดทั้งหมด | `docker compose -f deploy/docker-compose.yml down` (ข้อมูลใน volume ยังอยู่) |

**ก่อนแก้ระบบทุกครั้ง:** สำรองข้อมูลก่อน · **อย่า** ตั้ง `DJANGO_DEBUG=True` บน production · จำกัด `DJANGO_ALLOWED_HOSTS` เป็นโดเมนจริง

---

## 9. Checklist ความปลอดภัย / PDPA

- ☐ `DJANGO_DEBUG=False` + `DJANGO_SECRET_KEY` สุ่มใหม่ (ไม่ใช้ค่า default)
- ☐ `POSTGRES_PASSWORD` แข็งแรง · port ของ db ไม่ publish ออกนอก (ตั้งไว้แล้วใน compose)
- ☐ เปิด HTTPS (ข้อ 5) ถ้าเข้าถึงจากนอกวง
- ☐ ไฟล์ `.env` และ `migration/*.json` (ข้อมูลลูกค้าจริง) จำกัดสิทธิ์ + ไม่ commit ลง git (มีใน `.dockerignore`)
- ☐ ตั้งสำรองข้อมูล + ทดสอบกู้คืนจริงอย่างน้อย 1 ครั้ง
- ☐ รายงานบัญชีปิดเลขบัตร (แสดง 4 ตัวท้าย) ตาม PDPA — มีในระบบแล้ว
- ☐ ลบไฟล์ข้อมูลกลางทางหลัง import สำเร็จ

---

## 10. แก้ปัญหาเบื้องต้น (Troubleshooting)

| อาการ | สาเหตุ/วิธีแก้ |
|---|---|
| web restart วน / เชื่อม DB ไม่ได้ | ตรวจ `POSTGRES_*` ใน `.env` ตรงกัน · `docker compose logs db` |
| หน้าเว็บไม่มี CSS | `collectstatic` ยังไม่รัน → ดู log web · ตรวจ volume `static` |
| CSRF error ตอน login | ตั้ง `DJANGO_CSRF_TRUSTED_ORIGINS=https://โดเมน` ให้ตรง |
| PDF ใบเสร็จฟอนต์ไทยเพี้ยน | ตรวจว่า image ติดตั้ง `fonts-thai-tlwg` แล้ว (มีใน Dockerfile) |
| อัปโหลดรูปบัตรไม่ได้ (ใหญ่) | เพิ่ม `client_max_body_size` ใน nginx.conf |
```
