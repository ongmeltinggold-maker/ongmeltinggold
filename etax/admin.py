from django.contrib import admin
from . import models


@admin.register(models.ETaxConfig)
class ETaxConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "seller_tax_id", "mode", "enabled")


@admin.register(models.ETaxDocument)
class ETaxDocumentAdmin(admin.ModelAdmin):
    list_display = ("bill", "doc_type", "status", "rd_reference", "created_at")
    list_filter = ("status", "doc_type")
    readonly_fields = ("xml",)
