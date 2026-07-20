"""ขายฝาก (สัญญาจำนำทอง) + ไถ่ออก"""
from decimal import Decimal
from django.db import models

from customers.models import Customer
from catalog.models import MetalType, InterestRate, Duration


class ConsignmentContract(models.Model):
    """สัญญาขายฝาก"""
    ACTIVE = "active"; REDEEMED = "redeemed"; FORFEITED = "forfeited"
    STATUS_CHOICES = [(ACTIVE, "อยู่ระหว่างสัญญา"), (REDEEMED, "ไถ่ถอนแล้ว"),
                      (FORFEITED, "หลุดจำนำ")]

    doc_no = models.CharField("เลขที่สัญญา", max_length=30, blank=True)
    date = models.DateField("วันที่ทำสัญญา")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name="ลูกค้า",
                                 related_name="contracts")
    metal = models.ForeignKey(MetalType, on_delete=models.PROTECT, verbose_name="ประเภทโลหะ")
    weight_gram = models.DecimalField("น้ำหนัก (กรัม)", max_digits=12, decimal_places=3)
    cost_assessment = models.DecimalField("ราคาประเมิน", max_digits=14, decimal_places=2)
    principal = models.DecimalField("เงินต้นขายฝาก", max_digits=14, decimal_places=2)

    interest = models.ForeignKey(InterestRate, on_delete=models.PROTECT, verbose_name="อัตราดอกเบี้ย")
    duration = models.ForeignKey(Duration, on_delete=models.PROTECT, verbose_name="ระยะเวลา")
    due_date = models.DateField("วันครบกำหนด", null=True, blank=True)
    status = models.CharField("สถานะ", max_length=10, choices=STATUS_CHOICES, default=ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "สัญญาขายฝาก"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.doc_no or self.pk} — {self.customer.name_th}"

    def interest_amount(self) -> Decimal:
        """ดอกเบี้ยรวม = เงินต้น × อัตรา% × จำนวนเดือน (ปัดลง)"""
        from pricing.engine import floor_decimal
        rate = self.interest.rate / Decimal("100")
        return floor_decimal(self.principal * rate * self.duration.months)

    def redeem_total(self) -> Decimal:
        """ยอดไถ่ถอน = เงินต้น + ดอกเบี้ย"""
        return self.principal + self.interest_amount()


class Redeem(models.Model):
    """การไถ่ออก"""
    doc_no = models.CharField("เลขที่ใบไถ่ถอน", max_length=30, blank=True)
    date = models.DateField("วันที่ไถ่")
    contract = models.ForeignKey(ConsignmentContract, on_delete=models.PROTECT,
                                 verbose_name="สัญญาขายฝาก", related_name="redeems")
    principal = models.DecimalField("เงินต้น", max_digits=14, decimal_places=2)
    interest_received = models.DecimalField("ดอกเบี้ยรับ", max_digits=14, decimal_places=2, default=Decimal("0"))
    fee_received = models.DecimalField("ค่าธรรมเนียมรับ", max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name = verbose_name_plural = "การไถ่ออก"

    def total(self) -> Decimal:
        return self.principal + self.interest_received + self.fee_received

    def __str__(self):
        return f"ไถ่ {self.doc_no or self.pk}"
