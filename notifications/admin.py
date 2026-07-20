from django.contrib import admin
from . import models


@admin.register(models.LineConfig)
class LineConfigAdmin(admin.ModelAdmin):
    list_display = ("__str__", "reminder_days_before", "enabled")


@admin.register(models.CustomerLine)
class CustomerLineAdmin(admin.ModelAdmin):
    list_display = ("customer", "line_user_id", "linked_at")
    search_fields = ("customer__name_th", "line_user_id")


@admin.register(models.NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "customer", "channel", "status")
    list_filter = ("channel", "status")
