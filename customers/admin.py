from django.contrib import admin
from . import models


class CustomerImageInline(admin.TabularInline):
    model = models.CustomerImage
    extra = 1


@admin.register(models.MemberRank)
class MemberRankAdmin(admin.ModelAdmin):
    list_display = ("name", "no_service_fee", "order")
    list_editable = ("no_service_fee", "order")


@admin.register(models.Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name_th", "national_id", "tel", "member_rank", "is_vip", "created_at")
    list_filter = ("is_vip", "member_rank")
    search_fields = ("name_th", "national_id", "tel")
    inlines = [CustomerImageInline]
