"""การเงิน — สมุดเงินสด/บัญชีธนาคาร (ledger)"""
from decimal import Decimal
from django.db import models
from django.conf import settings


class BankAccount(models.Model):
    """แหล่งการเงิน (เงินสด/บัญชีธนาคาร)"""
    name = models.CharField("ชื่อแหล่งการเงิน", max_length=100)   # เงินสด, ธนาคารกสิกร ฯลฯ
    is_cash = models.BooleanField("เป็นเงินสด", default=False)

    class Meta:
        verbose_name = verbose_name_plural = "บัญชีการเงิน"

    def __str__(self):
        return self.name


class FinanceLedger(models.Model):
    """รายการเดินบัญชี (เข้า-ออก) + ยอดปรับปรุง"""
    account = models.ForeignKey(BankAccount, on_delete=models.PROTECT, verbose_name="แหล่งการเงิน",
                                related_name="entries")
    date = models.DateField("วันที่")
    ref_no = models.CharField("เลขที่รายการ", max_length=40, blank=True)
    description = models.CharField("รายการ", max_length=200, blank=True)
    amount_in = models.DecimalField("เงินเข้า", max_digits=14, decimal_places=2, default=Decimal("0"))
    amount_out = models.DecimalField("เงินออก", max_digits=14, decimal_places=2, default=Decimal("0"))
    fee = models.DecimalField("ค่าธรรมเนียม", max_digits=12, decimal_places=2, default=Decimal("0"))
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                    null=True, blank=True, verbose_name="ผู้บันทึก")

    class Meta:
        verbose_name = verbose_name_plural = "สมุดบัญชีการเงิน"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.account} {self.date} +{self.amount_in}/-{self.amount_out}"
