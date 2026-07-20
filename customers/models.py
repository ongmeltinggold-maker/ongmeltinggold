"""ลูกค้า / KYC + ระบบสมาชิก (VIP) + รูปหลายรูป"""
from django.db import models


class MemberRank(models.Model):
    """ยศ/ระดับสมาชิก (เช่น ทั่วไป, VIP)"""
    name = models.CharField("ชื่อยศ", max_length=50, unique=True)
    no_service_fee = models.BooleanField("ยกเว้นค่าบริการ (ไม่หัก%)", default=False)
    order = models.PositiveIntegerField("ลำดับ", default=0)

    class Meta:
        verbose_name = verbose_name_plural = "ยศสมาชิก"
        ordering = ["order"]

    def __str__(self):
        return self.name


class Customer(models.Model):
    """ทะเบียนลูกค้า/KYC — ฟิลด์รองรับ auto-fill จากบัตร (Siam ID/Card Reader)"""
    national_id = models.CharField("เลขบัตรประชาชน", max_length=13, unique=True)
    name_th = models.CharField("ชื่อ-นามสกุล (ไทย)", max_length=150)
    name_en = models.CharField("ชื่อ-นามสกุล (อังกฤษ)", max_length=150, blank=True)
    birthday = models.CharField("วันเดือนปีเกิด", max_length=40, blank=True)
    religion = models.CharField("ศาสนา", max_length=40, blank=True)
    address = models.TextField("ที่อยู่")
    card_issue_date = models.CharField("วันที่ออกบัตร", max_length=40, blank=True)
    card_expire_date = models.CharField("วันที่บัตรหมดอายุ", max_length=40, blank=True)
    tel = models.CharField("เบอร์โทร", max_length=40, blank=True)

    member_rank = models.ForeignKey(MemberRank, on_delete=models.SET_NULL, null=True,
                                    blank=True, verbose_name="ยศสมาชิก", related_name="customers")
    is_vip = models.BooleanField("เป็น VIP", default=False)

    created_at = models.DateTimeField("สร้างเมื่อ", auto_now_add=True)
    updated_at = models.DateTimeField("แก้ไขเมื่อ", auto_now=True)

    class Meta:
        verbose_name = verbose_name_plural = "ลูกค้า"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name_th} ({self.national_id})"

    @property
    def vip(self) -> bool:
        """ถือเป็น VIP ถ้า flag VIP หรือยศยกเว้นค่าบริการ"""
        return self.is_vip or bool(self.member_rank and self.member_rank.no_service_fee)

    @property
    def masked_national_id(self) -> str:
        """เลขบัตรแบบปิดบัง สำหรับรายงานบัญชี (โชว์ 4 ตัวท้าย)"""
        if not self.national_id:
            return ""
        return "X" * (len(self.national_id) - 4) + self.national_id[-4:]


class CustomerImage(models.Model):
    """รูปของลูกค้า (บัตรประชาชน/อื่น ๆ) — ได้หลายรูปต่อคน"""
    KIND_CHOICES = [("id_card", "รูปบัตรประชาชน"), ("other", "อื่น ๆ")]
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE,
                                 verbose_name="ลูกค้า", related_name="images")
    image = models.ImageField("รูป", upload_to="customers/%Y/%m/")
    kind = models.CharField("ประเภทรูป", max_length=20, choices=KIND_CHOICES, default="id_card")
    uploaded_at = models.DateTimeField("อัปโหลดเมื่อ", auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "รูปลูกค้า"

    def __str__(self):
        return f"{self.customer.name_th} — {self.get_kind_display()}"
