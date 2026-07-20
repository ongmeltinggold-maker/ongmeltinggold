"""e-Tax Invoice groundwork — เตรียมออกใบกำกับภาษีอิเล็กทรอนิกส์ + ส่งสรรพากร"""
from django.db import models
from sales.models import BillHead


class ETaxConfig(models.Model):
    """ตั้งค่าผู้ขายสำหรับ e-Tax (กรอกก่อนใช้งานจริง)"""
    PROVIDER_DIRECT = "direct"
    PROVIDER_SP = "service_provider"
    seller_name = models.CharField("ชื่อผู้ขาย", max_length=200, blank=True)
    seller_tax_id = models.CharField("เลขผู้เสียภาษี 13 หลัก", max_length=13, blank=True)
    branch_code = models.CharField("รหัสสาขา", max_length=5, default="00000")
    address = models.TextField("ที่อยู่", blank=True)
    mode = models.CharField("ช่องทางยื่น", max_length=20,
                            choices=[(PROVIDER_SP, "ผ่าน Service Provider"),
                                     (PROVIDER_DIRECT, "เชื่อมตรงกับสรรพากร")],
                            default=PROVIDER_SP)
    cert_note = models.CharField("หมายเหตุใบรับรอง (CA)", max_length=200, blank=True)
    enabled = models.BooleanField("เปิดใช้งาน", default=False)

    class Meta:
        verbose_name = verbose_name_plural = "ตั้งค่า e-Tax"

    def __str__(self):
        return f"e-Tax ({'เปิด' if self.enabled else 'ปิด'})"


class ETaxDocument(models.Model):
    """เอกสาร e-Tax ที่สร้าง/ส่งจากบิล"""
    DRAFT = "draft"; SIGNED = "signed"; SUBMITTED = "submitted"; ACCEPTED = "accepted"; FAILED = "failed"
    STATUS = [(DRAFT, "ร่าง"), (SIGNED, "ลงลายเซ็นแล้ว"), (SUBMITTED, "ส่งแล้ว"),
              (ACCEPTED, "สรรพากรรับแล้ว"), (FAILED, "ล้มเหลว")]
    bill = models.OneToOneField(BillHead, on_delete=models.CASCADE, related_name="etax",
                                verbose_name="บิล")
    doc_type = models.CharField("ประเภทเอกสาร", max_length=20, default="T02")  # T02=ใบกำกับภาษี
    xml = models.TextField("XML", blank=True)
    status = models.CharField("สถานะ", max_length=12, choices=STATUS, default=DRAFT)
    rd_reference = models.CharField("เลขอ้างอิงสรรพากร", max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "เอกสาร e-Tax"

    def __str__(self):
        return f"e-Tax {self.bill.doc_no} ({self.get_status_display()})"
