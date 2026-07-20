"""แจ้งเตือนสัญญาขายฝากใกล้ครบกำหนด (ตั้งเป็น cron รายวัน)

    python manage.py send_pawn_reminders
- หาสัญญา active ที่ due_date อยู่ภายใน reminder_days_before วัน
- ส่ง LINE (ถ้าตั้งค่า+จับคู่แล้ว) มิฉะนั้นบันทึกเป็น skipped
"""
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone

from consignment.models import ConsignmentContract
from notifications.models import LineConfig
from notifications.services import push_line


class Command(BaseCommand):
    help = "ส่งแจ้งเตือนขายฝากใกล้ครบกำหนดผ่าน LINE"

    def handle(self, *args, **opts):
        cfg = LineConfig.objects.first()
        days = cfg.reminder_days_before if cfg else 3
        today = timezone.localdate()
        limit = today + timedelta(days=days)

        contracts = ConsignmentContract.objects.filter(
            status=ConsignmentContract.ACTIVE, due_date__gte=today, due_date__lte=limit
        ).select_related("customer")

        sent = skipped = 0
        for c in contracts:
            total = c.redeem_total()
            msg = (f"แจ้งเตือนขายฝาก: สัญญา {c.doc_no} ครบกำหนด {c.due_date} "
                   f"ยอดไถ่ถอน {total:,.2f} บาท (เงินต้น {c.principal:,.0f} + ดอกเบี้ย)")
            status = push_line(c.customer, msg)
            if status == "sent":
                sent += 1
            else:
                skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f"แจ้งเตือนขายฝาก ({today}→{limit}): พบ {contracts.count()} สัญญา · ส่ง {sent} · ค้าง/ข้าม {skipped}"))
