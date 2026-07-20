"""Seed รายการเมนู/ฟังก์ชันทั้งหมด (ให้ Super Admin เปิด-ปิดได้)"""
from django.core.management.base import BaseCommand
from core.models import Feature

FEATURES = [
    # (code, name_th, group, icon, order)
    # --- ธุรกรรม ---
    ("sell", "ขายออกหน้าร้าน", "transaction", "🧾", 1),
    ("buy", "รับซื้อเข้าร้าน", "transaction", "🛒", 2),
    ("pawn", "ขายฝาก", "transaction", "🤝", 3),
    ("redeem", "ไถ่ออก", "transaction", "💰", 4),
    ("sell_ws", "ขายของเก่าให้ร้านส่ง", "transaction", "📤", 5),
    ("buy_ws", "ซื้อของใหม่จากร้านส่ง", "transaction", "📥", 6),
    ("other_expenses", "ค่าใช้จ่ายอื่นๆ", "transaction", "🧮", 7),
    ("finance_adjust", "ปรับปรุงการเงิน/ธนาคาร", "transaction", "🏦", 8),
    # --- ข้อมูล ---
    ("customer", "ลูกค้า / KYC", "data", "👤", 1),
    # --- รายงาน ---
    ("report_summary", "สรุปยอด", "report", "📊", 1),
    ("report_sales", "รายงานยอดขาย", "report", "📈", 2),
    ("report_purchase", "รายงานยอดซื้อ", "report", "📉", 3),
    ("report_finance", "รายงานการเงิน", "report", "🏦", 4),
    ("report_stock", "สต็อกคงเหลือ", "report", "📦", 5),
    ("report_sumbill", "รวมบิล", "report", "🧾", 6),
    ("report_customer_newold", "นับลูกค้าเก่า/ใหม่ (วัน/เดือน/ปี)", "report", "🆕", 7),
    ("report_accounting_masked", "รายงานบัญชี (ปิดเลขบัตร)", "report", "🔒", 8),
    # --- ตั้งค่า ---
    ("setting_company", "ข้อมูลบริษัท", "setting", "🏢", 1),
    ("setting_gold_price", "ราคาทองวันนี้", "setting", "🥇", 2),
    ("setting_metal_price", "ราคาเงิน/แพลทตินั่ม (ตั้งเอง)", "setting", "⚖️", 3),
    ("setting_service_fee", "ค่าบริการ (1–10%)", "setting", "％", 4),
    ("setting_interest", "อัตราดอกเบี้ยขายฝาก", "setting", "📅", 5),
    ("setting_duration", "ระยะเวลาขายฝาก", "setting", "⏱️", 6),
    ("setting_product_type", "ประเภทสินค้า/เมนู", "setting", "🏷️", 7),
    ("setting_supplier", "ร้านส่ง/คู่ค้า", "setting", "🚚", 8),
    ("setting_vat", "ตั้งค่า VAT", "setting", "🧾", 9),
    ("setting_member_rank", "ยศสมาชิก / VIP", "setting", "⭐", 10),
    ("setting_roles", "บทบาท/สิทธิ์ผู้ใช้", "setting", "🛡️", 11),
]


class Command(BaseCommand):
    help = "ใส่รายการเมนู/ฟังก์ชันทั้งหมดสำหรับระบบเปิด-ปิด (ไม่ทับค่าที่ตั้งไว้แล้ว)"

    def handle(self, *args, **opts):
        created = 0
        for code, name, group, icon, order in FEATURES:
            _, made = Feature.objects.get_or_create(
                code=code,
                defaults=dict(name_th=name, group=group, icon=icon, order=order, is_enabled=True))
            created += 1 if made else 0
        self.stdout.write(self.style.SUCCESS(
            f"✔ seed เมนู/ฟังก์ชัน — ใหม่ {created} รายการ (ทั้งหมด {Feature.objects.count()})"))
