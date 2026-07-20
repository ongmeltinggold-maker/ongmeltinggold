"""RBAC — ควบคุมสิทธิ์เข้าถึง feature ตามบทบาท + Feature Toggle"""
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

from core.models import Feature

OWNER = "owner"; MANAGER = "manager"; SALES = "sales"; ACCOUNT = "account"
ALL = {OWNER, MANAGER, SALES, ACCOUNT}

# บทบาทที่เข้าถึงได้ต่อ feature (ไม่ระบุ = ทุกบทบาท)
FEATURE_ROLES = {
    # ธุรกรรม — พนักงานขาย/ผู้จัดการ/เจ้าของ
    "sell": {SALES, MANAGER, OWNER}, "buy": {SALES, MANAGER, OWNER},
    "pawn": {SALES, MANAGER, OWNER}, "redeem": {SALES, MANAGER, OWNER},
    "sell_ws": {MANAGER, OWNER}, "buy_ws": {MANAGER, OWNER},
    "other_expenses": {MANAGER, OWNER}, "finance_adjust": {MANAGER, OWNER},
    # ข้อมูล
    "customer": {SALES, MANAGER, OWNER},
    # รายงาน — ผู้จัดการ/เจ้าของ/บัญชี (พนักงานขายไม่เห็น)
    "report_summary": {MANAGER, OWNER, ACCOUNT}, "report_sales": {MANAGER, OWNER, ACCOUNT},
    "report_purchase": {MANAGER, OWNER, ACCOUNT}, "report_finance": {MANAGER, OWNER, ACCOUNT},
    "report_stock": {MANAGER, OWNER}, "report_sumbill": {MANAGER, OWNER, ACCOUNT},
    "report_customer_newold": {MANAGER, OWNER}, "report_accounting_masked": {MANAGER, OWNER, ACCOUNT},
}


def user_role(user):
    """คืนบทบาทหลักของผู้ใช้ (superuser = owner)"""
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return OWNER
    prof = getattr(user, "profile", None)
    if prof and prof.role:
        return prof.role
    for g in user.groups.values_list("name", flat=True):
        if g in ALL:
            return g
    return SALES


def can_access(user, code):
    """เข้าถึง feature นี้ได้ไหม = เปิดใช้งาน (toggle) + บทบาทมีสิทธิ์"""
    if not Feature.enabled(code):
        return False
    if user.is_superuser:
        return True
    roles = FEATURE_ROLES.get(code)
    if roles is None:
        return True
    return user_role(user) in roles


def feature_required(code):
    """decorator: กันเข้า view ถ้าเมนูปิด หรือบทบาทไม่มีสิทธิ์"""
    def deco(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not can_access(request.user, code):
                messages.error(request, "คุณไม่มีสิทธิ์เข้าถึงเมนูนี้ หรือเมนูถูกปิดใช้งาน")
                return redirect("dashboard")
            return view(request, *args, **kwargs)
        return wrapper
    return deco
