"""นำเข้าสัญญาขายฝากที่ยังค้าง (active) จากระบบเดิม (แผน B — scrape)

ใช้:
    python manage.py import_legacy_contracts pawn_contracts_legacy.json [--dry-run]

รูปแบบไฟล์ (list ของ):
    {"doc_no","date"(YYYY-MM-DD),"customer_national_id","metal_code",
     "weight_gram","cost_assessment","principal","interest_rate",
     "duration_months","due_date"(YYYY-MM-DD),"status"}
- dedup ด้วย doc_no (มีอยู่แล้ว = ข้าม)
- ลูกค้าต้อง import มาก่อน (จับคู่ด้วย national_id) — ถ้าไม่พบจะข้ามพร้อมเตือน
- interest_rate / duration_months ต้องมีใน master data (seed แล้ว) — ถ้าไม่พบจะสร้างให้อัตโนมัติ
"""
import json
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from customers.models import Customer
from catalog.models import MetalType, InterestRate, Duration
from consignment.models import ConsignmentContract


def _date(s):
    return datetime.strptime(s, "%Y-%m-%d").date() if s else None


class Command(BaseCommand):
    help = "นำเข้าสัญญาขายฝากค้าง (active) จากระบบเดิม"

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true", help="ทดลอง ไม่บันทึกจริง")

    def handle(self, *args, **opts):
        try:
            with open(opts["path"], encoding="utf-8") as f:
                rows = json.load(f)
        except Exception as e:
            raise CommandError(f"อ่านไฟล์ไม่ได้: {e}")

        created = skipped = errors = 0
        dry = opts["dry_run"]

        for r in rows:
            doc_no = (r.get("doc_no") or "").strip()
            nid = (r.get("customer_national_id") or "").strip()

            if doc_no and ConsignmentContract.objects.filter(doc_no=doc_no).exists():
                self.stdout.write(f"  ข้าม (มีอยู่แล้ว): {doc_no}")
                skipped += 1
                continue

            cust = Customer.objects.filter(national_id=nid).first()
            if not cust:
                self.stderr.write(self.style.WARNING(
                    f"  ⚠ ไม่พบลูกค้า national_id={nid} สำหรับสัญญา {doc_no} — ข้าม (โปรด import ลูกค้าก่อน)"))
                errors += 1
                continue

            metal = MetalType.objects.filter(code=r.get("metal_code", "gold")).first()
            if not metal:
                self.stderr.write(self.style.WARNING(
                    f"  ⚠ ไม่พบโลหะ code={r.get('metal_code')} สำหรับ {doc_no} — ข้าม"))
                errors += 1
                continue

            rate = Decimal(str(r.get("interest_rate", "0")))
            interest, _ = InterestRate.objects.get_or_create(rate=rate)
            months = int(r.get("duration_months", 0))
            duration, _ = Duration.objects.get_or_create(months=months)

            if dry:
                self.stdout.write(
                    f"  (ทดลอง) จะสร้าง {doc_no}: {cust.name_th} · {metal.name_th} "
                    f"{r.get('weight_gram')}ก. · เงินต้น {r.get('principal')} · "
                    f"ดอกเบี้ย {rate}%/ด. × {months}ด. · ครบ {r.get('due_date')}")
                created += 1
                continue

            with transaction.atomic():
                ConsignmentContract.objects.create(
                    doc_no=doc_no,
                    date=_date(r.get("date")),
                    customer=cust,
                    metal=metal,
                    weight_gram=Decimal(str(r.get("weight_gram", "0"))),
                    cost_assessment=Decimal(str(r.get("cost_assessment", "0"))),
                    principal=Decimal(str(r.get("principal", "0"))),
                    interest=interest,
                    duration=duration,
                    due_date=_date(r.get("due_date")),
                    status=r.get("status", ConsignmentContract.ACTIVE),
                )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"  ✔ สร้าง {doc_no} — {cust.name_th}"))

        mode = "(ทดลอง) " if dry else ""
        self.stdout.write(self.style.SUCCESS(
            f"{mode}นำเข้าสัญญาขายฝาก: สร้าง {created} · ข้าม {skipped} · ผิดพลาด {errors} · ทั้งหมด {len(rows)}"))
        if not dry and created:
            self.stdout.write(self.style.WARNING(
                "  หมายเหตุ: ระบบเดิมคิดค่าธรรมเนียม 0.75%/เดือน แยกจากดอกเบี้ย — "
                "บันทึกตอนไถ่ถอนผ่านฟิลด์ Redeem.fee_received"))
