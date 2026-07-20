from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.db import connection
from django.http import JsonResponse

from core import views as core_views
from sales import views as sales_views
from customers import views as cust_views
from consignment import views as pawn_views
from reports import views as report_views


def healthz(request):
    """health check — ตรวจการเชื่อมต่อฐานข้อมูล (ใช้โดย docker/nginx)"""
    try:
        with connection.cursor() as c:
            c.execute("SELECT 1")
            c.fetchone()
        return JsonResponse({"status": "ok"})
    except Exception as e:  # pragma: no cover
        return JsonResponse({"status": "error", "detail": str(e)}, status=503)


urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    path("", core_views.dashboard, name="dashboard"),

    # ธุรกรรม
    path("buy/", sales_views.buy, name="buy"),
    path("buy/calc/", sales_views.buy_calc, name="buy_calc"),
    path("sell/", sales_views.sell, name="sell"),
    path("sell/calc/", sales_views.sell_calc, name="sell_calc"),
    path("bill/<int:pk>/", sales_views.bill_view, name="bill_view"),
    path("bill/<int:pk>/pdf/", sales_views.bill_pdf, name="bill_pdf"),

    # ขายฝาก / ไถ่ออก
    path("pawn/", pawn_views.pawn, name="pawn"),
    path("pawn/calc/", pawn_views.pawn_calc, name="pawn_calc"),
    path("pawn/<int:pk>/", pawn_views.contract_view, name="contract_view"),
    path("pawn/<int:pk>/pdf/", pawn_views.contract_pdf, name="contract_pdf"),
    path("redeem/", pawn_views.redeem, name="redeem"),
    path("redeem/detail/", pawn_views.redeem_detail, name="redeem_detail"),
    path("redeem/<int:pk>/", pawn_views.redeem_view, name="redeem_view"),
    path("redeem/<int:pk>/pdf/", pawn_views.redeem_pdf, name="redeem_pdf"),

    # ลูกค้า
    path("customers/", cust_views.customer_list, name="customer_list"),
    path("customers/add/", cust_views.customer_add, name="customer_add"),

    # รายงาน
    path("reports/customers/", report_views.report_customer, name="report_customer"),
    path("reports/accounting/", report_views.report_accounting, name="report_accounting"),
    path("reports/accounting/pdf/", report_views.report_accounting_pdf, name="report_accounting_pdf"),
    path("reports/summary/", report_views.report_summary, name="report_summary"),
    path("reports/sales/", report_views.report_sales, name="report_sales"),
    path("reports/purchase/", report_views.report_purchase, name="report_purchase"),
    path("reports/finance/", report_views.report_finance, name="report_finance"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
