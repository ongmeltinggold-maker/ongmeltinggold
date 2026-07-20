"""สต็อก — เคลื่อนไหวและคงเหลือ แยกตามวัสดุ (กรัม)"""
from decimal import Decimal
from django.db import models
from django.db.models import Sum

from catalog.models import MetalType


class StockMovement(models.Model):
    """รายการเข้า-ออกสต็อก (+ = เข้า, − = ออก)"""
    IN = "in"; OUT = "out"
    metal = models.ForeignKey(MetalType, on_delete=models.PROTECT, verbose_name="ประเภทโลหะ",
                              related_name="movements")
    date = models.DateField("วันที่")
    direction = models.CharField("ทิศทาง", max_length=3, choices=[(IN, "เข้า"), (OUT, "ออก")])
    weight_gram = models.DecimalField("น้ำหนัก (กรัม)", max_digits=12, decimal_places=3)
    note = models.CharField("หมายเหตุ", max_length=200, blank=True)

    class Meta:
        verbose_name = verbose_name_plural = "การเคลื่อนไหวสต็อก"
        ordering = ["-date", "-id"]

    def signed_weight(self) -> Decimal:
        w = self.weight_gram
        return w if self.direction == self.IN else -w

    def __str__(self):
        return f"{self.metal} {self.direction} {self.weight_gram}g"

    @staticmethod
    def balance_for(metal) -> Decimal:
        agg = StockMovement.objects.filter(metal=metal)
        total_in = agg.filter(direction=StockMovement.IN).aggregate(s=Sum("weight_gram"))["s"] or Decimal("0")
        total_out = agg.filter(direction=StockMovement.OUT).aggregate(s=Sum("weight_gram"))["s"] or Decimal("0")
        return total_in - total_out


class StockLot(models.Model):
    """ล็อตต้นทุน (สร้างตอนรับซื้อ) — ใช้คิดต้นทุน-กำไรแบบ FIFO"""
    metal = models.ForeignKey(MetalType, on_delete=models.PROTECT, verbose_name="ประเภทโลหะ",
                              related_name="lots")
    received_date = models.DateField("วันที่รับเข้า")
    source_detail = models.ForeignKey("sales.BillDetail", on_delete=models.SET_NULL, null=True, blank=True,
                                      verbose_name="รายการรับซื้อต้นทาง", related_name="produced_lots")
    weight_gram = models.DecimalField("น้ำหนักรับเข้า (กรัม)", max_digits=12, decimal_places=3)
    remaining_gram = models.DecimalField("คงเหลือ (กรัม)", max_digits=12, decimal_places=3)
    unit_cost = models.DecimalField("ต้นทุนต่อกรัม", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = verbose_name_plural = "ล็อตต้นทุน (FIFO)"
        ordering = ["received_date", "id"]

    def __str__(self):
        return f"Lot#{self.pk} {self.metal} คงเหลือ {self.remaining_gram}g @ {self.unit_cost}"


class LotConsumption(models.Model):
    """การตัดล็อตเมื่อขายออก (ผูกรายการขาย → ล็อตต้นทุน)"""
    sale_detail = models.ForeignKey("sales.BillDetail", on_delete=models.CASCADE,
                                    verbose_name="รายการขาย", related_name="lot_consumptions")
    lot = models.ForeignKey(StockLot, on_delete=models.PROTECT, verbose_name="ล็อตต้นทุน",
                            related_name="consumptions")
    weight_gram = models.DecimalField("น้ำหนักที่ตัด (กรัม)", max_digits=12, decimal_places=3)
    cost = models.DecimalField("ต้นทุนส่วนนี้", max_digits=14, decimal_places=2)

    class Meta:
        verbose_name = verbose_name_plural = "การตัดล็อตต้นทุน"

    def __str__(self):
        return f"ตัด {self.weight_gram}g จาก Lot#{self.lot_id}"
