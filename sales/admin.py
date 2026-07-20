from django.contrib import admin
from . import models


class BillDetailInline(admin.TabularInline):
    model = models.BillDetail
    extra = 1


class PaymentInline(admin.TabularInline):
    model = models.Payment
    extra = 1


@admin.register(models.BillHead)
class BillHeadAdmin(admin.ModelAdmin):
    list_display = ("doc_no", "bill_type", "date", "customer", "supplier", "total_amount", "vat_amount")
    list_filter = ("bill_type", "date")
    search_fields = ("doc_no",)
    inlines = [BillDetailInline, PaymentInline]
