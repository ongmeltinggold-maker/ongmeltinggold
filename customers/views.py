from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render, redirect

from core.access import can_access
from .models import Customer, MemberRank, CustomerImage


@login_required
def customer_list(request):
    if not can_access(request.user, "customer"):
        messages.error(request, "เมนู 'ลูกค้า/KYC' ถูกปิดใช้งาน หรือคุณไม่มีสิทธิ์")
        return redirect("dashboard")
    q = request.GET.get("q", "").strip()
    customers = Customer.objects.all()
    if q:
        customers = customers.filter(
            Q(name_th__icontains=q) | Q(national_id__icontains=q) | Q(tel__icontains=q))
    return render(request, "customers/list.html", {
        "active_feature": "customer", "customers": customers[:200], "q": q,
        "total": Customer.objects.count(),
    })


@login_required
def customer_add(request):
    if not can_access(request.user, "customer"):
        return redirect("dashboard")
    if request.method == "POST":
        nid = request.POST.get("national_id", "").strip()
        name = request.POST.get("name_th", "").strip()
        if not nid or not name:
            messages.error(request, "กรุณากรอกเลขบัตรและชื่อ-นามสกุล")
            return redirect("customer_add")
        if Customer.objects.filter(national_id=nid).exists():
            messages.error(request, "มีลูกค้าเลขบัตรนี้อยู่แล้ว")
            return redirect("customer_add")
        rank_id = request.POST.get("member_rank") or None
        cust = Customer.objects.create(
            national_id=nid, name_th=name,
            name_en=request.POST.get("name_en", ""),
            birthday=request.POST.get("birthday", ""),
            religion=request.POST.get("religion", ""),
            address=request.POST.get("address", ""),
            tel=request.POST.get("tel", ""),
            member_rank_id=rank_id,
            is_vip=request.POST.get("is_vip") == "1",
        )
        for f in request.FILES.getlist("images"):
            CustomerImage.objects.create(customer=cust, image=f, kind="id_card")
        messages.success(request, f"เพิ่มลูกค้า {cust.name_th} เรียบร้อย")
        return redirect("customer_list")

    return render(request, "customers/add.html", {
        "active_feature": "customer", "ranks": MemberRank.objects.all(),
    })
