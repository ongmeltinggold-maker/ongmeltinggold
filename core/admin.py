from django.contrib import admin
from .models import Feature


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    """Super Admin เปิด/ปิดเมนูได้จากหน้ารายการนี้ (แก้ช่อง 'เปิดใช้งาน' ได้ทันที)"""
    list_display = ("name_th", "code", "group", "is_enabled", "order", "updated_at")
    list_editable = ("is_enabled", "order")
    list_filter = ("group", "is_enabled")
    search_fields = ("code", "name_th")
    ordering = ("group", "order")

    # จำกัดให้เฉพาะ superuser จัดการ toggle เมนู (ความปลอดภัย)
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser
