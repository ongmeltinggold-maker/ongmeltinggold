"""สร้างกลุ่มสิทธิ์ (RBAC) 4 บทบาท + กำหนดสิทธิ์เบื้องต้นตามแอป"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


# แอปที่แต่ละบทบาทเข้าถึงได้ (จัดสิทธิ์เบื้องต้น — ปรับละเอียดใน Phase 1)
ROLE_APPS = {
    "owner":   ["customers", "catalog", "sales", "consignment", "inventory", "finance", "reports", "accounts"],
    "manager": ["customers", "catalog", "sales", "consignment", "inventory", "finance", "reports"],
    "sales":   ["customers", "sales", "consignment"],
    "account": ["finance", "reports"],
}
ROLE_TH = {"owner": "เจ้าของร้าน", "manager": "ผู้จัดการ", "sales": "พนักงานขาย", "account": "บัญชี"}


class Command(BaseCommand):
    help = "สร้างกลุ่มสิทธิ์ (Groups) ตามบทบาท + กำหนดสิทธิ์เบื้องต้น"

    def handle(self, *args, **opts):
        for role, apps in ROLE_APPS.items():
            group, _ = Group.objects.get_or_create(name=role)
            perms = Permission.objects.filter(content_type__app_label__in=apps)
            # เจ้าของ = ทุกสิทธิ์ในแอป, พนักงานขาย = ไม่ให้ลบ
            if role == "sales":
                perms = perms.exclude(codename__startswith="delete_")
            if role == "account":
                # บัญชี = ดูอย่างเดียว (view) เพื่อความปลอดภัยข้อมูล
                perms = perms.filter(codename__startswith="view_")
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(
                f"✔ กลุ่ม '{role}' ({ROLE_TH[role]}) — {group.permissions.count()} สิทธิ์"))
        self.stdout.write(self.style.SUCCESS("เสร็จสิ้น: สร้างบทบาทครบ 4 กลุ่ม"))
