from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum, Count

from catalog.models import MetalType, GoldPrice
from customers.models import Customer
from inventory.models import StockMovement
from sales.models import BillHead
from consignment.models import ConsignmentContract


@login_required
def dashboard(request):
    today = timezone.localdate()
    gold = GoldPrice.objects.order_by("-date").first()

    sales_today = BillHead.objects.filter(bill_type=BillHead.SELL, date=today).aggregate(
        s=Sum("total_amount"))["s"] or Decimal("0")
    buy_today = BillHead.objects.filter(bill_type=BillHead.BUY, date=today).aggregate(
        s=Sum("total_amount"))["s"] or Decimal("0")
    new_customers = Customer.objects.filter(created_at__date=today).count()

    stock = [{"metal": m.name_th, "g": StockMovement.balance_for(m)}
             for m in MetalType.objects.all()]

    pawn_due = ConsignmentContract.objects.filter(
        status=ConsignmentContract.ACTIVE).order_by("due_date")[:5]

    return render(request, "dashboard.html", {
        "active_feature": "dashboard",
        "gold": gold,
        "sales_today": sales_today,
        "buy_today": buy_today,
        "new_customers": new_customers,
        "total_customers": Customer.objects.count(),
        "stock": stock,
        "pawn_due": pawn_due,
    })
