"""บัญชีผู้ใช้ + บทบาท (RBAC) + Audit log (PDPA)"""
from django.db import models
from django.conf import settings

# บทบาทหลัก (map กับ Django Groups ชื่อเดียวกัน)
ROLE_OWNER = "owner"
ROLE_MANAGER = "manager"
ROLE_SALES = "sales"
ROLE_ACCOUNT = "account"
ROLE_CHOICES = [
    (ROLE_OWNER, "เจ้าของร้าน"),
    (ROLE_MANAGER, "ผู้จัดการ"),
    (ROLE_SALES, "พนักงานขาย"),
    (ROLE_ACCOUNT, "บัญชี"),
]


class UserProfile(models.Model):
    """ข้อมูลเสริมผู้ใช้ + บทบาทหลัก"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="profile", verbose_name="ผู้ใช้")
    role = models.CharField("บทบาท", max_length=20, choices=ROLE_CHOICES, default=ROLE_SALES)
    tel = models.CharField("เบอร์โทร", max_length=40, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "โปรไฟล์ผู้ใช้ (บทบาท)"

    def __str__(self):
        return f"{self.user} — {self.get_role_display()}"


class AuditLog(models.Model):
    """บันทึกการกระทำที่สำคัญ (ดู/สร้าง/แก้ไข/ลบ/พิมพ์) เพื่อการตรวจสอบ + PDPA"""
    VIEW = "view"; CREATE = "create"; UPDATE = "update"; DELETE = "delete"; PRINT = "print"; LOGIN = "login"
    ACTION_CHOICES = [(VIEW, "เข้าดู"), (CREATE, "สร้าง"), (UPDATE, "แก้ไข"),
                      (DELETE, "ลบ"), (PRINT, "พิมพ์"), (LOGIN, "เข้าสู่ระบบ")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             verbose_name="ผู้ใช้", related_name="audit_logs")
    action = models.CharField("การกระทำ", max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField("โมเดล", max_length=100, blank=True)
    object_id = models.CharField("รหัสอ้างอิง", max_length=50, blank=True)
    detail = models.TextField("รายละเอียด", blank=True)
    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)
    created_at = models.DateTimeField("เวลา", auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "บันทึกการตรวจสอบ (Audit Log)"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.user} {self.get_action_display()} {self.model_name}"
