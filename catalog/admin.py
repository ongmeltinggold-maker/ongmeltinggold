from django.contrib import admin
from . import models


@admin.register(models.Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_id", "tel", "station")


@admin.register(models.MetalType)
class MetalTypeAdmin(admin.ModelAdmin):
    """ลูกค้ากำหนดสูตรคำนวณเองได้ต่อโลหะ (เพิ่มโลหะ/เครื่องประดับใหม่ได้)"""
    list_display = ("name_th", "code", "formula", "factor", "price_source",
                    "apply_service_fee", "fee_threshold_percent", "vat_exempt", "order")
    list_editable = ("formula", "factor", "price_source", "apply_service_fee",
                     "fee_threshold_percent", "vat_exempt", "order")
    list_filter = ("formula", "price_source", "apply_service_fee")


@admin.register(models.GoldPrice)
class GoldPriceAdmin(admin.ModelAdmin):
    list_display = ("date", "bar_sell", "bar_buy", "jewelry_buy")


@admin.register(models.MetalPriceSetting)
class MetalPriceSettingAdmin(admin.ModelAdmin):
    list_display = ("metal", "base_price_per_gram")


@admin.register(models.ServiceFeeSetting)
class ServiceFeeSettingAdmin(admin.ModelAdmin):
    list_display = ("fee_percent", "fee_threshold_percent", "gold_factor", "is_active")


@admin.register(models.InterestRate)
class InterestRateAdmin(admin.ModelAdmin):
    list_display = ("rate", "is_active")


@admin.register(models.Duration)
class DurationAdmin(admin.ModelAdmin):
    list_display = ("months", "is_active")


@admin.register(models.ProductItem)
class ProductItemAdmin(admin.ModelAdmin):
    list_display = ("name", "metal", "diamond_profit_percent")
    list_filter = ("metal",)


@admin.register(models.VatSetting)
class VatSettingAdmin(admin.ModelAdmin):
    list_display = ("rate_percent", "is_active")


@admin.register(models.Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "tax_id", "tel", "is_active")
    search_fields = ("name", "tax_id")


@admin.register(models.DocumentNumber)
class DocumentNumberAdmin(admin.ModelAdmin):
    list_display = ("prefix", "ym", "last_number")
    list_filter = ("prefix", "ym")
