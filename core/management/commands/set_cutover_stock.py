"""ตั้งสต็อกยกยอด (opening) ให้ตรงกับยอดตัดระบบ (cutover) จากระบบเดิม

ใช้ตอน go-live:
    python manage.py set_cutover_stock migration/cutover_stock.json [--dry-run]

อ่านไฟล์ {"as_of_date","stock_gram":{metal_code: weight}}:
- ลบ opening movement/lot เดิม (note='ยกยอดตั้งต้น' / lot ที่ไม่มี source_detail) ของแต่ละวัสดุ
- สร้าง StockMovement (IN) + StockLot ยกยอดใหม่ตามน้ำหนัก cutover
- ต้นทุนต่อกรัมยกยอดใช้ค่าประมาณเดิม (ปรับได้ภายหลังใน Admin)

หมายเหตุ: ยอด cutover ควรผ่านการ 'ตรวจนับจริง' (physical count) ยืนยันก่อนใช้
"""
import json
from datetime import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import MetalType, GoldPrice, MetalPriceSetting
from inventory.models import StockMovement, StockLot
from pricing.engine import floor_decimal


class Command(BaseCommand):
    help = "ตั้งสต็อกยกยอดให้ตรงยอดตัดระบบ (cutover)"

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--dry-run", action="store_true")

    def _opening_cost(self, code):
        """ต้นทุนต่อกรัมยกยอด (ประมาณ) — ปรับได้ภายหลัง"""
        gp = GoldPrice.objects.order_by("-date").first()
        bar_buy = gp.bar_buy if gp else Decimal("63850")
        if code == "gold":
            return floor_decimal(bar_buy * Decimal("0.0656") * Decimal("0.965"))
        if code == "nak":
            return floor_decimal(bar_buy * Decimal("0.0656") * Decimal("0.50"))
        mps = MetalPriceSetting.objects.filter(metal__code=code).first()
        base = mps.base_price_per_gram if mps else Decimal("0")
        return floor_decimal(base * Decimal("0.95"))

    def handle(self, *args, **opts):
        try:
            with open(opts["path"], encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"อ่านไฟล์ไม่ได้: {e}")

        as_of = data.get("as_of_date")
        stock = data.get("stock_gram", {})
        on_date = datetime.strptime(as_of, "%Y-%m-%d").date() if as_of else None
        dry = opts["dry_run"]

        for code, g in stock.items():
            metal = MetalType.objects.filter(code=code).first()
            if not metal:
                self.stderr.write(self.style.WARNING(f"  ⚠ ไม่พบโลหะ code={code} — ข้าม"))
                continue
            weight = Decimal(str(g))
            cost = self._opening_cost(code)
            cur = StockMovement.balance_for(metal)
            if dry:
                self.stdout.write(
                    f"  (ทดลอง) {metal.name_th}: {cur} → {weight} ก. (ต้นทุนยกยอด {cost}/ก.)")
                continue
            with transaction.atomic():
                # ลบ opening เดิม (ยกยอดตั้งต้น + ล็อตยกยอดที่ไม่มีต้นทาง)
                StockMovement.objects.filter(metal=metal, note="ยกยอดตั้งต้น").delete()
                StockLot.objects.filter(metal=metal, source_detail__isnull=True).delete()
                StockMovement.objects.create(
                    metal=metal, date=on_date, direction=StockMovement.IN,
                    weight_gram=weight, note="ยกยอดตั้งต้น")
                StockLot.objects.create(
                    metal=metal, received_date=on_date, weight_gram=weight,
                    remaining_gram=weight, unit_cost=cost)
            self.stdout.write(self.style.SUCCESS(
                f"  ✔ {metal.name_th}: ตั้งยกยอด {weight} ก. (ต้นทุน {cost}/ก.)"))

        mode = "(ทดลอง) " if dry else ""
        self.stdout.write(self.style.SUCCESS(f"{mode}ตั้งสต็อกยกยอด cutover เรียบร้อย ({as_of})"))
