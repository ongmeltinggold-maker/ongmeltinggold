from django.contrib import admin
from . import models


@admin.register(models.ConsignmentContract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("doc_no", "date", "customer", "principal", "interest", "duration", "status")
    list_filter = ("status", "date")


@admin.register(models.Redeem)
class RedeemAdmin(admin.ModelAdmin):
    list_display = ("doc_no", "date", "contract", "principal", "interest_received")
