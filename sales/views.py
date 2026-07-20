from decimal import Decimal, InvalidOperation
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from catalog.models import MetalType, GoldPrice, DocumentNumber, Company
from customers.models import Customer
from inventory.models import StockMovement, StockLot
from inventory.services import consume_fifo
from core.models import Feature
from core.pdf import render_pdf
from .models import BillHead, BillDetail, Payment
from . import services


def _dec(v, default="0"):
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return Decimal(default)


def _feature_guard(request, code):
    """คืน True ถ้าเปิดใช้งาน + บทบาทมีสิทธิ์ (กันเข้าตรงผ่าน URL)"""
    from core.access import can_access
    return can_access(request.user, code)


# ============ รับซื้อเข้าร้าน (BUY) ============
@login_required
def buy(request):
    if not _feature_guard(request, "buy"):
        messages.error(request, "เมนู 'รับซื้อเข้าร้าน' ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")

    if request.method == "POST":
        return _save_buy(request)

    ctx = _txn_context("buy")
    return render(request, "sales/buy.html", ctx)


@login_required
def buy_calc(request):
    """HTMX: คำนวณสดตอนกรอก"""
    metal = get_object_or_404(MetalType, pk=request.GET.get("metal"))
    purity = _dec(request.GET.get("purity"), "0")
    weight = _dec(request.GET.get("weight"), "0")
    is_vip = request.GET.get("is_vip") == "1"
    base = request.GET.get("base_price") or None
    fee = request.GET.get("fee_percent") or None
    result, used_base, used_fee = services.compute_buy(metal, purity, weight, is_vip, base, fee)
    return render(request, "sales/_buy_calc.html", {"r": result, "base": used_base, "fee": used_fee,
                                                    "metal": metal, "weight": weight})


@transaction.atomic
def _save_buy(request):
    metal = get_object_or_404(MetalType, pk=request.POST.get("metal"))
    purity = _dec(request.POST.get("purity"))
    weight = _dec(request.POST.get("weight"))
    is_vip = request.POST.get("is_vip") == "1"
    base = request.POST.get("base_price") or None
    fee = request.POST.get("fee_percent") or None
    customer_id = request.POST.get("customer") or None

    if weight <= 0 or purity <= 0:
        messages.error(request, "กรุณากรอกน้ำหนักและ% ให้ถูกต้อง")
        return redirect("buy")

    result, used_base, used_fee = services.compute_buy(metal, purity, weight, is_vip, base, fee)
    today = timezone.localdate()
    customer = Customer.objects.filter(pk=customer_id).first() if customer_id else None

    bill = BillHead.objects.create(
        bill_type=BillHead.BUY, doc_no=DocumentNumber.next("RC", today),
        date=today, time=timezone.localtime().time(),
        customer=customer, gold_price_ref=used_base,
        total_amount=result.final, created_by=request.user)
    detail = BillDetail.objects.create(
        bill=bill, metal=metal, purity_percent=purity, weight_gram=weight,
        price_per_gram=result.price_per_gram,
        fee_applied=result.fee_applied, fee_percent=result.fee_percent,
        subtotal=result.subtotal, amount=result.final)
    Payment.objects.create(bill=bill, method=Payment.CASH, amount=result.final)

    # สต็อกเข้า + สร้างล็อตต้นทุน (FIFO)
    StockMovement.objects.create(metal=metal, date=today, direction=StockMovement.IN,
                                 weight_gram=weight, note=f"รับซื้อ {bill.doc_no}")
    unit_cost = (result.final / weight) if weight else Decimal("0")
    StockLot.objects.create(metal=metal, received_date=today, source_detail=detail,
                            weight_gram=weight, remaining_gram=weight,
                            unit_cost=unit_cost.quantize(Decimal("0.01")))

    messages.success(request, f"บันทึกรับซื้อ {bill.doc_no} — ยอด {result.final:,.2f} บาท เพิ่มสต็อก {weight} ก.")
    return redirect("bill_view", pk=bill.pk)


# ============ ขายออกหน้าร้าน (SELL) ============
@login_required
def sell(request):
    if not _feature_guard(request, "sell"):
        messages.error(request, "เมนู 'ขายออกหน้าร้าน' ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    if request.method == "POST":
        return _save_sell(request)
    ctx = _txn_context("sell")
    return render(request, "sales/sell.html", ctx)


@login_required
def sell_calc(request):
    gold = GoldPrice.objects.order_by("-date").first()
    bar_sell = _dec(request.GET.get("bar_sell") or (gold.bar_sell if gold else 0))
    weight = _dec(request.GET.get("weight"), "0")
    labor = _dec(request.GET.get("labor"), "0")
    r = services.compute_sell(bar_sell, weight, labor)
    return render(request, "sales/_sell_calc.html", {"r": r})


@transaction.atomic
def _save_sell(request):
    metal = get_object_or_404(MetalType, pk=request.POST.get("metal"))
    weight = _dec(request.POST.get("weight"))
    labor = _dec(request.POST.get("labor"))
    bar_sell = _dec(request.POST.get("bar_sell"))
    customer_id = request.POST.get("customer") or None
    if weight <= 0:
        messages.error(request, "กรุณากรอกน้ำหนักให้ถูกต้อง")
        return redirect("sell")

    r = services.compute_sell(bar_sell, weight, labor)
    today = timezone.localdate()
    customer = Customer.objects.filter(pk=customer_id).first() if customer_id else None

    bill = BillHead.objects.create(
        bill_type=BillHead.SELL, doc_no=DocumentNumber.next("IV", today),
        date=today, time=timezone.localtime().time(), customer=customer,
        gold_price_ref=bar_sell, total_amount=r["total"], vat_amount=r["vat"],
        created_by=request.user)
    detail = BillDetail.objects.create(
        bill=bill, metal=metal, purity_percent=Decimal("96.5"), weight_gram=weight,
        labor_cost=labor, vat_base=r["vat_base"], vat_amount=r["vat"],
        subtotal=r["gold_value"] + labor, amount=r["total"])
    # ตัดล็อตต้นทุนแบบ FIFO + คิดกำไร (กำไร = ยอดก่อน VAT − ต้นทุน)
    cost_basis, shortfall = consume_fifo(detail, metal, weight)
    detail.cost_basis = cost_basis
    detail.profit = (r["gold_value"] + labor) - cost_basis
    detail.save(update_fields=["cost_basis", "profit"])

    Payment.objects.create(bill=bill, method=Payment.CASH, amount=r["total"])
    StockMovement.objects.create(metal=metal, date=today, direction=StockMovement.OUT,
                                 weight_gram=weight, note=f"ขายออก {bill.doc_no}")

    msg = f"บันทึกการขาย {bill.doc_no} — ยอด {r['total']:,.2f} บาท (VAT {r['vat']:,.2f}) · กำไร {detail.profit:,.2f}"
    if shortfall > 0:
        msg += f" · ⚠️ สต็อกล็อตไม่พอ {shortfall} ก. (ต้นทุนบางส่วนไม่ครบ)"
    messages.success(request, msg)
    return redirect("bill_view", pk=bill.pk)


# ============ ใบเสร็จ (preview + PDF) ============
@login_required
def bill_view(request, pk):
    bill = get_object_or_404(BillHead, pk=pk)
    return render(request, "sales/bill_done.html", {"bill": bill})


@login_required
def bill_pdf(request, pk):
    bill = get_object_or_404(BillHead.objects.prefetch_related("details", "payments"), pk=pk)
    subtotal = bill.total_amount - bill.vat_amount
    return render_pdf(request, "print/receipt.html", {
        "bill": bill, "subtotal": subtotal, "company": Company.objects.first(),
    }, filename=bill.doc_no or f"bill{bill.pk}")


# ---------- helper context ----------
def _txn_context(active):
    gold = GoldPrice.objects.order_by("-date").first()
    fee_default, _, _ = services.fee_setting()
    return {
        "active_feature": active,
        "metals": MetalType.objects.all(),
        "customers": Customer.objects.all()[:500],
        "gold": gold,
        "fee_default": fee_default,
    }
