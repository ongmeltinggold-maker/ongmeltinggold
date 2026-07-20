"""Seed ข้อมูลจริงจากระบบเดิม + master data ตาม requirement"""
from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from catalog.models import (Company, MetalType, GoldPrice, MetalPriceSetting,
                            ServiceFeeSetting, InterestRate, Duration, ProductItem,
                            VatSetting, Supplier)
from customers.models import MemberRank, Customer
from inventory.models import StockMovement, StockLot
from pricing.engine import floor_decimal


class Command(BaseCommand):
    help = "ใส่ข้อมูลตั้งต้น (master data + ตัวอย่าง) จากระบบเดิม"

    def handle(self, *args, **opts):
        # บริษัท
        Company.objects.get_or_create(
            name="โอเอ็นจี หลอมทอง",
            defaults=dict(address="156/7 ถนนพังงา ต.ตลาดใหญ่ อ.เมืองภูเก็ต จ.ภูเก็ต 83000",
                          tax_id="3839900461751", tel="0654249514", station="(สำนักงานใหญ่)"))

        # ประเภทโลหะ + สูตร (ลูกค้าแก้เองได้ภายหลังผ่าน Admin)
        BAR = MetalType.SOURCE_GOLD_BAR; MAN = MetalType.SOURCE_MANUAL
        G = MetalType.FORMULA_GOLD; F = MetalType.FORMULA_FLAT
        # code: (ชื่อ, method, order, price_source, apply_fee, threshold)
        metals = {
            "gold":     ("ทอง", G, 1, BAR, True, Decimal("90")),
            "silver":   ("เงิน", F, 2, MAN, False, Decimal("0")),
            "nak":      ("นาก", G, 3, BAR, True, Decimal("90")),
            "platinum": ("ทองคำขาว (แพลทตินั่ม)", F, 4, MAN, False, Decimal("0")),
        }
        mt = {}
        for code, (name, formula, order, src, fee, thr) in metals.items():
            mt[code], _ = MetalType.objects.update_or_create(
                code=code, defaults=dict(name_th=name, formula=formula, order=order,
                                         price_source=src, apply_service_fee=fee,
                                         fee_threshold_percent=thr, factor=Decimal("0.0656")))

        # ราคาตั้งเอง เงิน/แพลทตินั่ม (ตัวอย่างจากลูกค้า)
        MetalPriceSetting.objects.get_or_create(metal=mt["silver"],
                                                defaults=dict(base_price_per_gram=Decimal("46")))
        MetalPriceSetting.objects.get_or_create(metal=mt["platinum"],
                                                defaults=dict(base_price_per_gram=Decimal("700")))

        # ราคาทองวันนี้ (จากระบบเดิม)
        GoldPrice.objects.get_or_create(
            date=date(2026, 7, 18),
            defaults=dict(bar_sell=Decimal("64050"), bar_buy=Decimal("63850"),
                          jewelry_buy=Decimal("60658")))

        # ค่าบริการ
        ServiceFeeSetting.objects.get_or_create(
            defaults=dict(fee_percent=Decimal("3"), gold_factor=Decimal("0.0656"),
                          fee_threshold_percent=Decimal("90")))

        # VAT (7% คิดจากส่วนต่าง)
        VatSetting.objects.get_or_create(defaults=dict(rate_percent=Decimal("7")))

        # ร้านส่ง/คู่ค้า (ตัวอย่างจากระบบเดิม)
        Supplier.objects.get_or_create(name="โอเอ็นจี บ้านหลอม",
                                       defaults=dict(tax_id="3839900461751", tel="0654249514"))

        # ดอกเบี้ยขายฝาก + ระยะเวลา (ตรงกับระบบเดิม: 9 อัตรา 1.00–3.00%/เดือน)
        for r in ["3.00", "2.75", "2.50", "2.25", "2.00", "1.75", "1.50", "1.25", "1.00"]:
            InterestRate.objects.get_or_create(rate=Decimal(r))
        for m in [1, 2, 3, 4, 5]:
            Duration.objects.get_or_create(months=m)

        # เมนูสินค้าเพชร (%กำไร 25)
        for name in ["กำไลเพชร", "จี้เพชร", "ต่างหูเพชร", "สร้อยข้อมือเพชร",
                     "สร้อยคอเพชร", "แหวนเพชร", "กำไลเพชรซีก"]:
            ProductItem.objects.get_or_create(metal=mt["gold"], name=name,
                                              defaults=dict(diamond_profit_percent=Decimal("25")))

        # ยศสมาชิก
        MemberRank.objects.get_or_create(name="ทั่วไป", defaults=dict(no_service_fee=False, order=1))
        MemberRank.objects.get_or_create(name="VIP", defaults=dict(no_service_fee=True, order=2))

        # สต็อกตั้งต้น (จากระบบเดิม) + ล็อตต้นทุนยกยอด (ประมาณการ — ปรับได้)
        bar_buy = Decimal("63850")
        stock = {"gold": "1117.730", "silver": "4587.030", "nak": "290.400", "platinum": "4.990"}
        # ต้นทุนต่อกรัมยกยอด (ประมาณ): ทอง=ราคาแท่ง×0.0656×96.5%, นาก≈50%, เงิน=46×95%, Pt=700×90%
        opening_cost = {
            "gold": floor_decimal(bar_buy * Decimal("0.0656") * Decimal("0.965")),
            "nak": floor_decimal(bar_buy * Decimal("0.0656") * Decimal("0.50")),
            "silver": floor_decimal(Decimal("46") * Decimal("0.95")),
            "platinum": floor_decimal(Decimal("700") * Decimal("0.90")),
        }
        for code, g in stock.items():
            if not StockMovement.objects.filter(metal=mt[code]).exists():
                StockMovement.objects.create(metal=mt[code], date=date(2026, 7, 18),
                                             direction=StockMovement.IN,
                                             weight_gram=Decimal(g), note="ยกยอดตั้งต้น")
            if not StockLot.objects.filter(metal=mt[code]).exists():
                StockLot.objects.create(metal=mt[code], received_date=date(2026, 7, 18),
                                        weight_gram=Decimal(g), remaining_gram=Decimal(g),
                                        unit_cost=opening_cost[code])

        # ลูกค้าตัวอย่าง
        vip = MemberRank.objects.get(name="VIP")
        Customer.objects.get_or_create(
            national_id="1119900000001",
            defaults=dict(name_th="นาย ธีรยุทธ ด้วงเพชร",
                          address="165 ม.3 ต.ท่างิ้ว อ.ห้วยยอด จ.ตรัง",
                          tel="0610725832"))
        Customer.objects.get_or_create(
            national_id="1119900000002",
            defaults=dict(name_th="น.ส. กานต์รวี จันทร์อ่อน (VIP)",
                          address="67/153 ม.1 ต.ฉลอง อ.เมืองภูเก็ต จ.ภูเก็ต",
                          tel="0927972569", member_rank=vip, is_vip=True))

        # ตั้งค่า LINE / e-Tax (ปิดไว้ก่อน — กรอก token/cert เมื่อพร้อม)
        from notifications.models import LineConfig
        from etax.models import ETaxConfig
        LineConfig.objects.get_or_create(defaults=dict(reminder_days_before=3, enabled=False))
        comp = Company.objects.first()
        ETaxConfig.objects.get_or_create(defaults=dict(
            seller_name=comp.name if comp else "", seller_tax_id=comp.tax_id if comp else "",
            address=comp.address if comp else "", enabled=False))

        self.stdout.write(self.style.SUCCESS("✔ seed ข้อมูลตั้งต้นเรียบร้อย"))
