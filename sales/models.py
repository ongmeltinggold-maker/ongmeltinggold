"""บิลซื้อ/ขาย + รายการ + การชำระเงิน + รูปชิ้นงาน"""
from decimal import Decimal
from django.db import models
from django.conf import settings

from customers.models import Customer
from catalog.models import MetalType, ProductItem, Supplier


class BillHead(models.Model):
    """หัวบิล (ครอบคลุมทุกชนิดธุรกรรม)"""
    SELL = "sell"; BUY = "buy"; SELL_WS = "sell_ws"; BUY_WS = "buy_ws"
    TYPE_CHOICES = [(SELL, "ขายออกหน้าร้าน"), (BUY, "ซื้อเข้าหน้าร้าน"),
                    (SELL_WS, "ขายของเก่าให้ร้านส่ง"), (BUY_WS, "ซื้อของใหม่จากร้านส่ง")]

    bill_type = models.CharField("ชนิดบิล", max_length=10, choices=TYPE_CHOICES)
    doc_no = models.CharField("เลขที่เอกสาร", max_length=30, blank=True)
    date = models.DateField("วันที่")
    time = models.TimeField("เวลา", null=True, blank=True)

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name="ลูกค้า", related_name="bills")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, null=True, blank=True,
                                 verbose_name="ร้านส่ง/คู่ค้า", related_name="bills",
                                 help_text="ใช้เมื่อเป็นธุรกรรมค้าส่ง (sell_ws/buy_ws)")
    gold_price_ref = models.DecimalField("ราคาทองอ้างอิง", max_digits=12, decimal_places=2,
                                         default=Decimal("0"))

    total_amount = models.DecimalField("ยอดรวม", max_digits=14, decimal_places=2, default=Decimal("0"))
    vat_amount = models.DecimalField("ภาษีมูลค่าเพิ่ม", max_digits=14, decimal_places=2, default=Decimal("0"))
    full_tax_invoice = models.BooleanField("ใบกำกับภาษีเต็มรูปแบบ", default=False)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                                   null=True, blank=True, verbose_name="ผู้บันทึก")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = verbose_name_plural = "บิล (ซื้อ/ขาย)"
        ordering = ["-date", "-id"]

    def __str__(self):
        return f"{self.get_bill_type_display()} {self.doc_no or self.pk}"


class BillDetail(models.Model):
    """รายการในบิล + เก็บผลคำนวณจาก Pricing Engine"""
    bill = models.ForeignKey(BillHead, on_delete=models.CASCADE, related_name="details",
                             verbose_name="บิล")
    metal = models.ForeignKey(MetalType, on_delete=models.PROTECT, verbose_name="ประเภทโลหะ")
    product_item = models.ForeignKey(ProductItem, on_delete=models.SET_NULL, null=True, blank=True,
                                     verbose_name="สินค้า")
    purity_percent = models.DecimalField("% เนื้อโลหะ", max_digits=5, decimal_places=2, default=Decimal("96.5"))
    weight_gram = models.DecimalField("น้ำหนัก (กรัม)", max_digits=12, decimal_places=3)
    price_per_gram = models.DecimalField("ราคาต่อกรัม", max_digits=12, decimal_places=2, default=Decimal("0"))
    labor_cost = models.DecimalField("ค่ากำเหน็จ", max_digits=12, decimal_places=2, default=Decimal("0"))

    fee_applied = models.BooleanField("หักค่าบริการ", default=False)
    fee_percent = models.DecimalField("ค่าบริการ (%)", max_digits=4, decimal_places=2, default=Decimal("0"))
    subtotal = models.DecimalField("ยอดก่อนหัก", max_digits=14, decimal_places=2, default=Decimal("0"))
    amount = models.DecimalField("ยอดสุทธิ", max_digits=14, decimal_places=2, default=Decimal("0"))

    # VAT (คิดจากส่วนต่าง/ค่ากำเหน็จ ตามกฎภาษีทองไทย)
    vat_base = models.DecimalField("ฐานภาษี (ส่วนต่าง)", max_digits=14, decimal_places=2, default=Decimal("0"))
    vat_amount = models.DecimalField("VAT", max_digits=14, decimal_places=2, default=Decimal("0"))

    # สำหรับคิดต้นทุน-กำไร (ผูกล็อตที่รับซื้อ — ดู inventory.LotConsumption)
    cost_basis = models.DecimalField("ต้นทุน", max_digits=14, decimal_places=2, default=Decimal("0"))
    profit = models.DecimalField("กำไร", max_digits=14, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name = verbose_name_plural = "รายการบิล"

    def __str__(self):
        return f"{self.metal} {self.weight_gram}g = {self.amount}"


class BillItemImage(models.Model):
    """รูปชิ้นงาน (หลายรูปต่อรายการ)"""
    detail = models.ForeignKey(BillDetail, on_delete=models.CASCADE, related_name="images",
                               verbose_name="รายการ")
    image = models.ImageField("รูปชิ้นงาน", upload_to="items/%Y/%m/")

    class Meta:
        verbose_name = verbose_name_plural = "รูปชิ้นงาน"


class Payment(models.Model):
    """การชำระเงิน (เงินสด/โอน/EDC + ค่าธรรมเนียม)"""
    CASH = "cash"; TRANSFER = "transfer"; AEON = "aeon"; FIRSTCHOICE = "firstchoice"; CREDIT = "credit"
    METHOD_CHOICES = [(CASH, "เงินสด"), (TRANSFER, "เงินโอน"), (AEON, "อิออน"),
                      (FIRSTCHOICE, "เฟิร์สช้อยส์"), (CREDIT, "บัตรเครดิต")]
    bill = models.ForeignKey(BillHead, on_delete=models.CASCADE, related_name="payments",
                             verbose_name="บิล")
    method = models.CharField("วิธีชำระ", max_length=15, choices=METHOD_CHOICES, default=CASH)
    amount = models.DecimalField("จำนวนเงิน", max_digits=14, decimal_places=2, default=Decimal("0"))
    fee = models.DecimalField("ค่าธรรมเนียม", max_digits=12, decimal_places=2, default=Decimal("0"))

    class Meta:
        verbose_name = verbose_name_plural = "การชำระเงิน"

    def __str__(self):
        return f"{self.get_method_display()} {self.amount}"
