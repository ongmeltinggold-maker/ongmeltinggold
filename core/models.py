"""System config — Feature Toggle (Super Admin เปิด/ปิดเมนู/ฟังก์ชัน)"""
from django.db import models


class Feature(models.Model):
    """เมนู/ฟังก์ชันที่ Super Admin เปิด-ปิดได้

    - หน้าเว็บ (Phase 1) จะแสดงเฉพาะรายการที่ is_enabled=True
    - view/endpoint จะตรวจ Feature.enabled(code) ก่อนทำงาน (กันเข้าตรงผ่าน URL)
    """
    GROUP_TRANSACTION = "transaction"
    GROUP_REPORT = "report"
    GROUP_DATA = "data"
    GROUP_SETTING = "setting"
    GROUP_CHOICES = [
        (GROUP_TRANSACTION, "ธุรกรรม"),
        (GROUP_REPORT, "รายงาน"),
        (GROUP_DATA, "ข้อมูล"),
        (GROUP_SETTING, "ตั้งค่า"),
    ]

    code = models.SlugField("รหัสฟังก์ชัน", unique=True)   # เช่น sell, buy, pawn, report_finance
    name_th = models.CharField("ชื่อเมนู", max_length=100)
    group = models.CharField("กลุ่ม", max_length=20, choices=GROUP_CHOICES, default=GROUP_TRANSACTION)
    icon = models.CharField("ไอคอน", max_length=20, blank=True)
    is_enabled = models.BooleanField("เปิดใช้งาน", default=True)
    order = models.PositiveIntegerField("ลำดับ", default=0)
    description = models.CharField("คำอธิบาย", max_length=200, blank=True)
    updated_at = models.DateTimeField("แก้ไขล่าสุด", auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "เมนู/ฟังก์ชัน (เปิด-ปิด)"
        ordering = ["group", "order"]

    def __str__(self):
        return f"{self.name_th} ({'เปิด' if self.is_enabled else 'ปิด'})"

    # ---- helpers สำหรับใช้ในหน้าเว็บ/วิว (Phase 1) ----
    @classmethod
    def enabled(cls, code) -> bool:
        """ฟังก์ชันนี้เปิดอยู่ไหม (ถ้าไม่มีในตาราง ถือว่าเปิด — safe default)"""
        row = cls.objects.filter(code=code).values_list("is_enabled", flat=True).first()
        return True if row is None else bool(row)

    @classmethod
    def menu(cls):
        """คืนเฉพาะเมนูที่เปิด สำหรับ render sidebar"""
        return cls.objects.filter(is_enabled=True)
