"""รายงาน — นับลูกค้าเก่า/ใหม่ + รายงานบัญชีปิดเลขบัตร (PDPA)"""
import calendar
from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.shortcuts import render, redirect
from django.utils import timezone

from core.access import can_access
from core.pdf import render_pdf
from catalog.models import Company
from customers.models import Customer
from sales.models import BillHead


def _period_range(period, ref: date):
    """คืน (start_date, end_date, label) ตามช่วง day/month/year"""
    if period == "day":
        return ref, ref, ref.strftime("%d/%m/%Y")
    if period == "year":
        return date(ref.year, 1, 1), date(ref.year, 12, 31), f"ปี {ref.year + 543}"
    # month (default)
    last = calendar.monthrange(ref.year, ref.month)[1]
    return date(ref.year, ref.month, 1), date(ref.year, ref.month, last), ref.strftime("%m/%Y")


def _parse_ref(request):
    period = request.GET.get("period", "month")
    raw = request.GET.get("ref")
    ref = timezone.localdate()
    if raw:
        try:
            ref = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            pass
    return period, ref


# ============ รายงานลูกค้าเก่า/ใหม่ ============
@login_required
def report_customer(request):
    if not can_access(request.user, "report_customer_newold"):
        messages.error(request, "รายงานนี้ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    period, ref = _parse_ref(request)
    start, end, label = _period_range(period, ref)
    start_dt = timezone.make_aware(datetime.combine(start, time.min))
    end_dt = timezone.make_aware(datetime.combine(end, time.max))

    # ลูกค้าใหม่ = สร้างในช่วง
    new_qs = Customer.objects.filter(created_at__gte=start_dt, created_at__lte=end_dt)
    new_count = new_qs.count()

    # ลูกค้าที่มาทำรายการในช่วง (มีบิล)
    bills = BillHead.objects.filter(date__gte=start, date__lte=end, customer__isnull=False)
    active_ids = set(bills.values_list("customer_id", flat=True))
    new_ids = set(new_qs.values_list("id", flat=True))
    # เก่า(กลับมา) = ทำรายการในช่วง แต่สมัครก่อนช่วงนี้
    returning_ids = active_ids - new_ids
    returning_count = len(returning_ids)

    return render(request, "reports/customer.html", {
        "active_feature": "report_customer_newold",
        "period": period, "ref": ref.isoformat(), "label": label,
        "new_count": new_count, "returning_count": returning_count,
        "active_count": len(active_ids),
        "new_list": new_qs.order_by("-created_at")[:100],
        "total_customers": Customer.objects.count(),
    })


# ============ รายงานบัญชีปิดเลขบัตร (PDPA) ============
def _accounting_rows(period, ref):
    start, end, label = _period_range(period, ref)
    # "ลูกค้ามาขาย" = ร้านรับซื้อ (bill_type = BUY)
    bills = (BillHead.objects.filter(bill_type=BillHead.BUY, date__gte=start, date__lte=end)
             .select_related("customer").order_by("date", "id"))
    total = bills.aggregate(s=Sum("total_amount"))["s"] or Decimal("0")
    return bills, total, label


@login_required
def report_accounting(request):
    if not can_access(request.user, "report_accounting_masked"):
        messages.error(request, "รายงานนี้ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    period, ref = _parse_ref(request)
    bills, total, label = _accounting_rows(period, ref)
    return render(request, "reports/accounting.html", {
        "active_feature": "report_accounting_masked",
        "period": period, "ref": ref.isoformat(), "label": label,
        "bills": bills, "total": total,
    })


@login_required
def report_accounting_pdf(request):
    period, ref = _parse_ref(request)
    bills, total, label = _accounting_rows(period, ref)
    return render_pdf(request, "print/accounting.html", {
        "bills": bills, "total": total, "label": label,
        "company": Company.objects.first(),
    }, filename=f"accounting_{label.replace('/', '-')}")


# ============ รายงานยอดขาย / ยอดซื้อ ============
def _txn_report(request, bill_type, code, title, doc_prefix, feature):
    if not can_access(request.user, feature):
        messages.error(request, "รายงานนี้ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    period, ref = _parse_ref(request)
    start, end, label = _period_range(period, ref)
    bills = (BillHead.objects.filter(bill_type=bill_type, date__gte=start, date__lte=end)
             .select_related("customer").order_by("date", "id"))
    agg = bills.aggregate(n=Count("id"), total=Sum("total_amount"), vat=Sum("vat_amount"))
    ym = "%02d%02d" % (ref.month, (ref.year + 543) % 100)   # สรุปเดือน MMYY
    return render(request, "reports/report_txn.html", {
        "active_feature": feature, "title": title, "doc_no": f"{doc_prefix}-{ym}",
        "period": period, "ref": ref.isoformat(), "label": label,
        "bills": bills, "count": agg["n"] or 0,
        "total": agg["total"] or Decimal("0"), "vat": agg["vat"] or Decimal("0"),
    })


@login_required
def report_sales(request):
    return _txn_report(request, BillHead.SELL, "sales", "รายงานยอดขาย", "MS", "report_sales")


@login_required
def report_purchase(request):
    return _txn_report(request, BillHead.BUY, "purchase", "รายงานยอดซื้อ", "MB", "report_purchase")


# ============ รายงานการเงิน (แยกช่องทางชำระ) ============
@login_required
def report_finance(request):
    if not can_access(request.user, "report_finance"):
        messages.error(request, "รายงานนี้ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    from sales.models import Payment
    period, ref = _parse_ref(request)
    start, end, label = _period_range(period, ref)
    pays = Payment.objects.filter(bill__date__gte=start, bill__date__lte=end)
    by_method = (pays.values("method").annotate(total=Sum("amount"), fee=Sum("fee"), n=Count("id"))
                 .order_by("-total"))
    method_names = dict(Payment.METHOD_CHOICES)
    rows = [{"name": method_names.get(m["method"], m["method"]), "total": m["total"] or 0,
             "fee": m["fee"] or 0, "n": m["n"]} for m in by_method]
    grand = pays.aggregate(t=Sum("amount"), f=Sum("fee"))
    return render(request, "reports/report_finance.html", {
        "active_feature": "report_finance", "period": period, "ref": ref.isoformat(),
        "label": label, "rows": rows,
        "grand_total": grand["t"] or Decimal("0"), "grand_fee": grand["f"] or Decimal("0"),
    })


# ============ สรุปยอด (ขาย+ซื้อ ประจำเดือน) ============
@login_required
def report_summary(request):
    if not can_access(request.user, "report_summary"):
        messages.error(request, "รายงานนี้ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    period, ref = _parse_ref(request)
    start, end, label = _period_range(period, ref)
    ym = "%02d%02d" % (ref.month, (ref.year + 543) % 100)
    sell = BillHead.objects.filter(bill_type=BillHead.SELL, date__gte=start, date__lte=end).aggregate(
        n=Count("id"), t=Sum("total_amount"), v=Sum("vat_amount"))
    buy = BillHead.objects.filter(bill_type=BillHead.BUY, date__gte=start, date__lte=end).aggregate(
        n=Count("id"), t=Sum("total_amount"))
    return render(request, "reports/report_summary.html", {
        "active_feature": "report_summary", "period": period, "ref": ref.isoformat(), "label": label,
        "ms_no": f"MS-{ym}", "mb_no": f"MB-{ym}",
        "sell_n": sell["n"] or 0, "sell_total": sell["t"] or Decimal("0"), "sell_vat": sell["v"] or Decimal("0"),
        "buy_n": buy["n"] or 0, "buy_total": buy["t"] or Decimal("0"),
    })
