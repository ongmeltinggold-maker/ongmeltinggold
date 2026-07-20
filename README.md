# ongmeltinggold — ระบบบริหารร้านทอง โอเอ็นจี หลอมทอง

ระบบจัดการร้านทอง (ซื้อ/ขาย/ขายฝาก/ไถ่ถอน + สต็อก + รายงาน + ออกใบเสร็จ PDF) สร้างด้วย Django
แทนระบบสำเร็จรูปเดิม รองรับ deploy บน **Railway** (Docker + PostgreSQL)

## Stack
- Django 5.1 + Django REST Framework · PostgreSQL (prod) / SQLite (dev)
- HTMX + Django templates · WeasyPrint (ใบเสร็จ/สัญญา PDF A4/A5, ฟอนต์ไทย)
- Pricing Engine (Decimal, สูตรกำหนดเองต่อโลหะ) · FIFO ต้นทุน-กำไร · RBAC · Feature toggle
- เครื่องอ่านบัตรประชาชน (bridge แยกที่เครื่อง POS)

## รันบนเครื่อง (dev)
> WeasyPrint ต้องมี system libs: (Ubuntu) `apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 libcairo2 fonts-thai-tlwg` · (macOS) `brew install pango gdk-pixbuf libffi`
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data && python manage.py setup_roles && python manage.py seed_features
python manage.py createsuperuser
python manage.py runserver          # http://127.0.0.1:8000/
```

## Deploy
- **Railway:** ดู `deploy/RAILWAY.md` (build จาก `deploy/Dockerfile` ตาม `railway.json`)
- **VPS/self-host (Docker Compose):** ดู `deploy/DEPLOYMENT.md`

## ย้ายข้อมูลเดิม (Migration)
`import_legacy`, `import_legacy_contracts`, `set_cutover_stock` — ดู `deploy/DEPLOYMENT.md`
> ไฟล์ข้อมูลลูกค้าจริงไม่อยู่ใน repo (PDPA) — วางแยกตอน deploy

## ทดสอบ
```bash
pytest -q
```
