"""นำเข้าข้อมูลลูกค้าเดิม (จากไฟล์ JSON ที่ scrape มาจากระบบ AGALIGOLD)

ใช้:
    python manage.py import_legacy customers.json
รูปแบบไฟล์: [{"national_id","name_th","name_en","birthday","religion",
              "address","tel","card_issue_date","card_expire_date"}, ...]
- dedup ด้วย national_id (มีอยู่แล้ว = ข้าม)
- national_id ว่าง = สร้าง key ชั่วคราวจากชื่อ (เพื่อไม่ชน) พร้อมทำเครื่องหมาย
"""
import json
from django.core.management.base import BaseCommand, CommandError
from customers.models import Customer


class Command(BaseCommand):
    help = "นำเข้าลูกค้าเดิมจากไฟล์ JSON"

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true", help="ทดลอง ไม่บันทึกจริง")

    def handle(self, *args, **opts):
        try:
            with open(opts["path"], encoding="utf-8") as f:
                rows = json.load(f)
        except Exception as e:
            raise CommandError(f"อ่านไฟล์ไม่ได้: {e}")

        created = skipped = 0
        for i, r in enumerate(rows, 1):
            nid = (r.get("national_id") or "").strip()
            name = (r.get("name_th") or "").strip()
            if not name:
                continue
            key = nid or f"LEGACY{i:05d}"     # ไม่มีเลขบัตร → key ชั่วคราว
            if Customer.objects.filter(national_id=key).exists():
                skipped += 1
                continue
            if not opts["dry_run"]:
                Customer.objects.create(
                    national_id=key, name_th=name,
                    name_en=r.get("name_en", "") or "",
                    birthday=r.get("birthday", "") or "",
                    religion=r.get("religion", "") or "",
                    address=r.get("address", "") or "",
                    tel=r.get("tel", "") or "",
                    card_issue_date=r.get("card_issue_date", "") or "",
                    card_expire_date=r.get("card_expire_date", "") or "")
            created += 1

        mode = "(ทดลอง) " if opts["dry_run"] else ""
        self.stdout.write(self.style.SUCCESS(
            f"{mode}นำเข้าลูกค้า: สร้าง {created} · ข้าม(ซ้ำ) {skipped} · ทั้งหมด {len(rows)}"))
