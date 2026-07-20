# Deploy บน Railway — ระบบร้านทอง ONG หลอมทอง
### สำหรับ UAT (ให้ลูกค้าทดลอง) และ Production

Railway จะ build จาก `deploy/Dockerfile` (ตั้งไว้ใน `railway.json` แล้ว) ใช้ PostgreSQL ของ Railway,
ใส่ `DATABASE_URL` + `PORT` ให้อัตโนมัติ (โค้ดเรารองรับแล้ว) — ไม่ต้องแก้โค้ด

> โค้ดพร้อมแล้ว: รองรับ `DATABASE_URL`, `PORT`, WhiteNoise เสิร์ฟ static (ไม่ต้องใช้ nginx บน Railway),
> healthcheck `/healthz/`

---

## 0. เตรียม
- บัญชี Railway (สมัครด้วย Gmail แล้ว) · ติดตั้ง **Railway CLI**
  ```bash
  npm i -g @railway/cli      # หรือ: brew install railway
  railway --version
  ```
- โฟลเดอร์โปรเจกต์ `ong_system/` (จาก `ONG_NewSystem_Phase3.tar.gz`)

---

## 1. สร้างโปรเจกต์ + ฐานข้อมูล

```bash
railway login                 # เปิดเบราว์เซอร์ยืนยัน
cd ong_system
railway init                  # ตั้งชื่อ เช่น ong-goldshop  → ได้ project
railway add --database postgres    # เพิ่มบริการ PostgreSQL
```

---

## 2. ตั้งค่า Environment Variables (บริการ web)

สร้าง SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

ตั้งตัวแปร (แก้ค่าให้เป็นของจริง):
```bash
railway variables \
  --set "DJANGO_SECRET_KEY=<คีย์ที่สร้าง>" \
  --set "DJANGO_DEBUG=False" \
  --set "DJANGO_ALLOWED_HOSTS=.up.railway.app" \
  --set "DJANGO_CSRF_TRUSTED_ORIGINS=https://*.up.railway.app" \
  --set "DATABASE_URL=\${{Postgres.DATABASE_URL}}" \
  --set "RUN_SEED=1"
```

- `DJANGO_ALLOWED_HOSTS=.up.railway.app` — จุดนำหน้า = ครอบทุก subdomain ของ Railway (โดเมนจริงค่อยเพิ่มทีหลัง)
- `DATABASE_URL=${{Postgres.DATABASE_URL}}` — อ้างอิงค่าจากบริการ Postgres อัตโนมัติ
- `RUN_SEED=1` — ให้ seed master data รอบแรก (**ลบออกหลัง deploy รอบแรกสำเร็จ**)

---

## 3. Deploy

```bash
railway up      # build จาก deploy/Dockerfile → migrate + collectstatic + seed → gunicorn
```

ดู log:
```bash
railway logs
```

เปิดโดเมนสาธารณะ:
```bash
railway domain      # สร้าง URL เช่น https://ong-goldshop-production.up.railway.app
```
เปิด `https://<domain>/healthz/` → เห็น `{"status":"ok"}` = พร้อม

> หลัง deploy รอบแรกสำเร็จ:  `railway variables --set "RUN_SEED=0"`

---

## 4. เก็บไฟล์รูปบัตร/ชิ้นงานถาวร (Volume)

รูปที่อัปโหลดต้องอยู่บน volume ไม่งั้นหายตอน deploy ใหม่:
- Railway dashboard → บริการ web → **Variables/Settings → Volumes → Add Volume**
- Mount path: `/app/media`

---

## 5. สร้างผู้ใช้ผู้ดูแล + ย้ายข้อมูลเดิม

**สร้าง superuser** (รันคำสั่งบนฐานข้อมูล production ผ่าน CLI):
```bash
railway run python manage.py createsuperuser
```

**ย้ายข้อมูลลูกค้า/สัญญา/สต็อก** — `railway run` จะรันในเครื่องเราแต่ต่อ `DATABASE_URL` ของ Railway
(ข้อมูล PII อยู่ในเครื่องเรา ไม่ฝังใน image — ปลอดภัยตาม PDPA):
```bash
railway run python manage.py import_legacy migration/customers_legacy.json
railway run python manage.py import_legacy_contracts migration/pawn_contracts_legacy.json
railway run python manage.py set_cutover_stock migration/cutover_stock.json
```
> ต้องมี Python + `pip install -r requirements.txt` ในเครื่องที่รัน (ใช้ venv เดิมได้)
> ถ้า `railway run` ต่อ DB ไม่ได้ (บาง network) ใช้ค่า **DATABASE_PUBLIC_URL** ของบริการ Postgres แทน:
> `DATABASE_URL="<public url>" python manage.py import_legacy migration/customers_legacy.json`

---

## 6. ส่งให้ลูกค้าทดลอง (UAT)
- ส่ง URL + บัญชีผู้ใช้ (สร้างผ่าน Admin/`setup_roles` ตามบทบาท เจ้าของ/ผู้จัดการ/ขาย/บัญชี)
- ให้ทดลอง 1–2 สัปดาห์คู่กับระบบเดิม (parallel run) ตามแบบฟอร์มใน `ONG_Phase3_Migration_Reconcile`
- เครื่องอ่านบัตร: รัน `bridge/card_reader.py` ที่เครื่อง POS หน้าร้าน (ไม่เกี่ยวกับ Railway)

---

## 7. ต่อโดเมนจริง + HTTPS (ตอนขึ้น production)
- Railway dashboard → web → Settings → **Custom Domain** → ใส่โดเมนร้าน → ตั้ง CNAME ตามที่ Railway บอก
- Railway ออกใบรับรอง HTTPS ให้อัตโนมัติ
- เพิ่มโดเมนใน env:
  ```bash
  railway variables \
    --set "DJANGO_ALLOWED_HOSTS=.up.railway.app,ong.example.com" \
    --set "DJANGO_CSRF_TRUSTED_ORIGINS=https://ong.example.com"
  ```

---

## 8. สำรองข้อมูล
- Railway Postgres มี backup อัตโนมัติ (ดู/กู้ในแท็บ Postgres → Backups)
- **แนะนำเพิ่ม**: ดึง dump มาเก็บนอก Railway เป็นระยะ
  ```bash
  railway run pg_dump "$DATABASE_URL" -Fc -f backup_$(date +%Y%m%d).dump
  ```
- คัดลอกไฟล์ media จาก volume เก็บสำรองด้วย (ผ่าน dashboard หรือ CLI)

---

## 9. อัปเดตระบบรอบใหม่
แก้โค้ด → `railway up` อีกครั้ง (migrate/collectstatic รันอัตโนมัติใน entrypoint)
หรือเชื่อม GitHub repo เพื่อ auto-deploy ทุก push (Railway → Settings → Connect Repo)

---

## หมายเหตุค่าใช้จ่าย (ประมาณ)
- ทดลอง: credit ฟรี $5 (Free/Hobby)
- ร้านเดียวใช้จริง: ~$5–15/เดือน (usage-based ตาม CPU/RAM/volume ที่ใช้)
- ปรับ `WEB_CONCURRENCY` (จำนวน gunicorn worker) ได้ผ่าน env ถ้าต้องประหยัด/เพิ่มพลัง
