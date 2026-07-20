"""LINE OA groundwork — เตรียมแจ้งเตือนขายฝากครบกำหนด (ใช้ LINE Messaging API)"""
from django.db import models
from customers.models import Customer


class LineConfig(models.Model):
    """ตั้งค่า LINE Official Account (กรอกเมื่อได้ token จาก LINE)"""
    channel_access_token = models.CharField("Channel Access Token", max_length=300, blank=True)
    channel_secret = models.CharField("Channel Secret", max_length=100, blank=True)
    reminder_days_before = models.PositiveIntegerField("แจ้งเตือนล่วงหน้า (วัน)", default=3)
    enabled = models.BooleanField("เปิดใช้งาน", default=False)

    class Meta:
        verbose_name = verbose_name_plural = "ตั้งค่า LINE OA"

    def __str__(self):
        return f"LINE OA ({'เปิด' if self.enabled else 'ปิด'})"


class CustomerLine(models.Model):
    """จับคู่ลูกค้า ↔ LINE userId (ได้จาก LIFF/เพิ่มเพื่อน + ยืนยันเบอร์)"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE,
                                    related_name="line", verbose_name="ลูกค้า")
    line_user_id = models.CharField("LINE userId", max_length=100, unique=True)
    linked_at = models.DateTimeField("เชื่อมเมื่อ", auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "ลูกค้า ↔ LINE"

    def __str__(self):
        return f"{self.customer.name_th} ↔ {self.line_user_id[:10]}…"


class NotificationLog(models.Model):
    """บันทึกการส่งแจ้งเตือน (audit)"""
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True,
                                 verbose_name="ลูกค้า")
    channel = models.CharField("ช่องทาง", max_length=20, default="line")
    message = models.TextField("ข้อความ")
    status = models.CharField("สถานะ", max_length=20, default="queued")  # queued/sent/failed/skipped
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "ประวัติแจ้งเตือน"
        ordering = ["-created_at"]
