from django.contrib import admin
from . import models


@admin.register(models.BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ("name", "is_cash")


@admin.register(models.FinanceLedger)
class FinanceLedgerAdmin(admin.ModelAdmin):
    list_display = ("date", "account", "ref_no", "description", "amount_in", "amount_out", "fee")
    list_filter = ("account", "date")
