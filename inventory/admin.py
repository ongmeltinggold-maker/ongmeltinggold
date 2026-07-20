from django.contrib import admin
from . import models


@admin.register(models.StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("date", "metal", "direction", "weight_gram", "note")
    list_filter = ("metal", "direction", "date")


@admin.register(models.StockLot)
class StockLotAdmin(admin.ModelAdmin):
    list_display = ("id", "metal", "received_date", "weight_gram", "remaining_gram", "unit_cost")
    list_filter = ("metal", "received_date")


@admin.register(models.LotConsumption)
class LotConsumptionAdmin(admin.ModelAdmin):
    list_display = ("id", "sale_detail", "lot", "weight_gram", "cost")
