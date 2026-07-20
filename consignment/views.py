import calendar
from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from catalog.models import MetalType, InterestRate, Duration, DocumentNumber, Company
from customers.models import Customer
from core.access import can_access
from core.pdf import render_pdf
from pricing.engine import floor_decimal
from .models import ConsignmentContract, Redeem


def _dec(v, d="0"):
    try:
        return Decimal(str(v))
    except (InvalidOperation, TypeError):
        return Decimal(d)


def _add_months(d, months):
    m = d.month - 1 + int(months)
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def _interest(principal, rate_percent, months):
    return floor_decimal(principal * (_dec(rate_percent) / 100) * int(months))


# ============ ขายฝาก (PAWN) ============
@login_required
def pawn(request):
    if not can_access(request.user, "pawn"):
        messages.error(request, "เมนู 'ขายฝาก' ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    if request.method == "POST":
        return _save_pawn(request)
    return render(request, "consignment/pawn.html", {
        "active_feature": "pawn",
        "customers": Customer.objects.all()[:500],
        "metals": MetalType.objects.all(),
        "rates": InterestRate.objects.filter(is_active=True),
        "durations": Duration.objects.filter(is_active=True),
    })


@login_required
def pawn_calc(request):
    principal = _dec(request.GET.get("principal"))
    rate = _dec(request.GET.get("rate"))
    months = request.GET.get("months") or 0
    interest = _interest(principal, rate, months)
    due = _add_months(timezone.localdate(), months) if months else None
    return render(request, "consignment/_pawn_calc.html", {
        "principal": principal, "interest": interest, "total": principal + interest,
        "rate": rate, "months": months, "due": due,
    })


@transaction.atomic
def _save_pawn(request):
    customer = get_object_or_404(Customer, pk=request.POST.get("customer"))
    metal = get_object_or_404(MetalType, pk=request.POST.get("metal"))
    rate = get_object_or_404(InterestRate, pk=request.POST.get("rate"))
    duration = get_object_or_404(Duration, pk=request.POST.get("duration"))
    weight = _dec(request.POST.get("weight"))
    assess = _dec(request.POST.get("cost_assessment"))
    principal = _dec(request.POST.get("principal"))
    if weight <= 0 or principal <= 0:
        messages.error(request, "กรุณากรอกน้ำหนักและเงินต้นให้ถูกต้อง")
        return redirect("pawn")

    today = timezone.localdate()
    contract = ConsignmentContract.objects.create(
        doc_no=DocumentNumber.next("J", today), date=today, customer=customer, metal=metal,
        weight_gram=weight, cost_assessment=assess, principal=principal,
        interest=rate, duration=duration, due_date=_add_months(today, duration.months),
        status=ConsignmentContract.ACTIVE)
    interest = _interest(principal, rate.rate, duration.months)
    messages.success(request,
        f"บันทึกสัญญาขายฝาก {contract.doc_no} — เงินต้น {principal:,.2f} · ดอกเบี้ยเมื่อครบ {interest:,.2f} · ครบกำหนด {contract.due_date}")
    return redirect("contract_view", pk=contract.pk)


# ============ ไถ่ออก (REDEEM) ============
@login_required
def redeem(request):
    if not can_access(request.user, "redeem"):
        messages.error(request, "เมนู 'ไถ่ออก' ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    if request.method == "POST":
        return _save_redeem(request)
    return render(request, "consignment/redeem.html", {
        "active_feature": "redeem",
        "contracts": ConsignmentContract.objects.filter(
            status=ConsignmentContract.ACTIVE).select_related("customer", "interest", "duration"),
    })


@login_required
def redeem_detail(request):
    """HTMX: เลือกสัญญา → แสดงเงินต้น+ดอกเบี้ย+รวม"""
    c = get_object_or_404(ConsignmentContract, pk=request.GET.get("contract"))
    interest = c.interest_amount()
    fee = _dec(request.GET.get("fee"), "0")
    return render(request, "consignment/_redeem_detail.html", {
        "c": c, "interest": interest, "fee": fee, "total": c.principal + interest + fee,
    })


@transaction.atomic
def _save_redeem(request):
    c = get_object_or_404(ConsignmentContract, pk=request.POST.get("contract"))
    if c.status != ConsignmentContract.ACTIVE:
        messages.error(request, "สัญญานี้ไถ่ถอน/ปิดไปแล้ว")
        return redirect("redeem")
    fee = _dec(request.POST.get("fee"), "0")
    interest = c.interest_amount()
    today = timezone.localdate()
    rd = Redeem.objects.create(
        doc_no=DocumentNumber.next("RD", today), date=today, contract=c,
        principal=c.principal, interest_received=interest, fee_received=fee)
    c.status = ConsignmentContract.REDEEMED
    c.save(update_fields=["status"])
    total = c.principal + interest + fee
    messages.success(request,
        f"ไถ่ถอนสัญญา {c.doc_no} สำเร็จ — รับเงิน {total:,.2f} (เงินต้น {c.principal:,.2f} + ดอกเบี้ย {interest:,.2f})")
    return redirect("redeem_view", pk=rd.pk)


# ============ พิมพ์ PDF (สัญญา / ใบไถ่ถอน) ============
@login_required
def contract_view(request, pk):
    c = get_object_or_404(ConsignmentContract, pk=pk)
    return render(request, "consignment/contract_done.html", {"c": c, "interest": c.interest_amount()})


@login_required
def contract_pdf(request, pk):
    c = get_object_or_404(ConsignmentContract, pk=pk)
    interest = c.interest_amount()
    return render_pdf(request, "print/contract.html", {
        "c": c, "interest": interest, "total": c.principal + interest,
        "company": Company.objects.first()}, filename=c.doc_no or f"contract{c.pk}")


@login_required
def redeem_view(request, pk):
    rd = get_object_or_404(Redeem, pk=pk)
    return render(request, "consignment/redeem_done.html", {"rd": rd})


@login_required
def redeem_pdf(request, pk):
    rd = get_object_or_404(Redeem, pk=pk)
    return render_pdf(request, "print/redeem.html", {
        "rd": rd, "company": Company.objects.first()}, filename=rd.doc_no or f"redeem{rd.pk}")
