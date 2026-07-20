"""Context ที่ทุกหน้าใช้ร่วมกัน: เมนู (ตาม Feature Toggle), บริษัท, ราคาทองวันนี้"""
from django.urls import reverse, NoReverseMatch
from core.models import Feature

# map รหัสฟังก์ชัน → ชื่อ url (เฉพาะที่มีหน้าจริงใน Phase 1; ที่เหลือ → '#')
FEATURE_URL = {
    "buy": "buy",
    "sell": "sell",
    "pawn": "pawn",
    "redeem": "redeem",
    "customer": "customer_list",
    "report_customer_newold": "report_customer",
    "report_accounting_masked": "report_accounting",
    "report_summary": "report_summary",
    "report_sales": "report_sales",
    "report_purchase": "report_purchase",
    "report_finance": "report_finance",
}


def _href(code):
    name = FEATURE_URL.get(code)
    if not name:
        return "#"
    try:
        return reverse(name)
    except NoReverseMatch:
        return "#"


def site_context(request):
    from core.access import can_access
    menu = {"transaction": [], "data": [], "report": [], "setting": []}
    try:
        user = getattr(request, "user", None)
        for f in Feature.menu():
            # แสดงเฉพาะเมนูที่บทบาทของผู้ใช้เข้าถึงได้
            if user and user.is_authenticated and not can_access(user, f.code):
                continue
            f.href = _href(f.code)
            menu.setdefault(f.group, []).append(f)
    except Exception:
        pass  # ก่อน migrate

    company = gold = None
    try:
        from catalog.models import Company, GoldPrice
        company = Company.objects.first()
        gold = GoldPrice.objects.order_by("-date").first()
    except Exception:
        pass

    return {
        "menu_transaction": menu.get("transaction", []),
        "menu_data": menu.get("data", []),
        "menu_report": menu.get("report", []),
        "menu_setting": menu.get("setting", []),
        "site_company": company,
        "site_gold": gold,
    }
