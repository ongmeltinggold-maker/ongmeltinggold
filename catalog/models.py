"""Master data / ตั้งค่า — อ้างอิงค่าจริงจากระบบเดิม + requirement ใหม่"""
from decimal import Decimal
from django.db import models


class Company(models.Model):
    """ข้อมูลบริษัท (หัวใบเสร็จ)"""
    name = models.CharField("ชื่อบริษัท", max_length=200)
    address = models.TextField("ที่อยู่", blank=True)
    tax_id = models.CharField("เลขผู้เสียภาษี", max_length=20, blank=True)
    tel = models.CharField("โทรศัพท์", max_length=40, blank=True)
    station = models.CharField("สาขา/สำนักงาน", max_length=100, blank=True)
    logo = models.ImageField("โลโก้", upload_to="company/", blank=True, null=True)

    class Meta:
        verbose_name = verbose_name_plural = "ข้อมูลบริษัท"

    def __str__(self):
        return self.name


class MetalType(models.Model):
    """ประเภทโลหะ: gold / silver / nak / platinum"""
    FORMULA_GOLD = "gold"
    FORMULA_FLAT = "flat"
    FORMULA_CHOICES = [(FORMULA_GOLD, "สูตรทอง (×factor×% + หักค่าบริการ<90%)"),
                       (FORMULA_FLAT, "ตั้งราคาเอง (×% ไม่หักค่าบริการ)")]
    SOURCE_GOLD_BAR = "gold_bar"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_GOLD_BAR, "อ้างอิงราคาทองแท่งรับซื้อ"),
                      (SOURCE_MANUAL, "ตั้งราคาเอง (MetalPriceSetting)")]

    code = models.SlugField("รหัส", unique=True)          # gold/silver/nak/platinum/...
    name_th = models.CharField("ชื่อไทย", max_length=50)
    formula = models.CharField("วิธีคำนวณ", max_length=10,
                               choices=FORMULA_CHOICES, default=FORMULA_GOLD,
                               help_text="gold = base×factor×% (ทอง/นาก) · flat = base×% (เงิน/ทองคำขาว)")
    # ---- พารามิเตอร์สูตร (ลูกค้าแก้เองได้ผ่าน Admin) ----
    factor = models.DecimalField("factor (สำหรับสูตร gold)", max_digits=8, decimal_places=6,
                                 default=Decimal("0.0656"), help_text="≈ 1/15.244")
    price_source = models.CharField("แหล่งราคาตั้งต้น", max_length=10,
                                    choices=SOURCE_CHOICES, default=SOURCE_GOLD_BAR)
    apply_service_fee = models.BooleanField("หักค่าบริการ", default=True,
                                            help_text="โลหะนี้หักค่าบริการเมื่อ %<เกณฑ์ (ทอง=ใช่, เงิน/ทองคำขาว=ไม่)")
    fee_threshold_percent = models.DecimalField("เกณฑ์ % ที่เริ่มหักค่าบริการ", max_digits=5,
                                                decimal_places=2, default=Decimal("90"))
    vat_exempt = models.BooleanField("ยกเว้น VAT ทั้งจำนวน", default=False,
                                     help_text="เช่น ทองคำแท่ง — ยกเว้น VAT; ทองรูปพรรณ = คิด VAT เฉพาะส่วนต่าง")
    order = models.PositiveIntegerField("ลำดับ", default=0)

    class Meta:
        verbose_name = verbose_name_plural = "ประเภทสินค้า (โลหะ)"
        ordering = ["order"]

    def __str__(self):
        return self.name_th


class GoldPrice(models.Model):
    """ราคาทองรายวัน (อ้างอิงทองแท่ง 96.5%)"""
    date = models.DateField("วันที่", unique=True)
    bar_sell = models.DecimalField("ทองแท่งขายออก", max_digits=12, decimal_places=2)
    bar_buy = models.DecimalField("ทองแท่งรับซื้อ", max_digits=12, decimal_places=2)
    jewelry_buy = models.DecimalField("ทองรูปพรรณรับซื้อ", max_digits=12, decimal_places=2,
                                      default=Decimal("0"))

    class Meta:
        verbose_name = verbose_name_plural = "ราคาทองรายวัน"
        ordering = ["-date"]

    def __str__(self):
        return f"{self.date} ขาย {self.bar_sell} / ซื้อ {self.bar_buy}"


class MetalPriceSetting(models.Model):
    """ราคาตั้งเองต่อกรัม (เงิน/แพลทตินั่ม — ไม่อิงสมาคม)"""
    metal = models.OneToOneField(MetalType, on_delete=models.CASCADE,
                                 verbose_name="โลหะ", related_name="price_setting")
    base_price_per_gram = models.DecimalField("ราคาตั้งต่อกรัม", max_digits=12, decimal_places=2)

    class Meta:
        verbose_name = verbose_name_plural = "ราคาตั้งเอง (เงิน/แพลทตินั่ม)"

    def __str__(self):
        return f"{self.metal} = {self.base_price_per_gram}/กรัม"


class ServiceFeeSetting(models.Model):
    """ค่าบริการ (หัก%) — ปรับได้ 1–10%, factor, threshold"""
    fee_percent = models.DecimalField("ค่าบริการ (%)", max_digits=4, decimal_places=2,
                                      default=Decimal("3"))
    gold_factor = models.DecimalField("factor ทอง", max_digits=8, decimal_places=6,
                                      default=Decimal("0.0656"))
    fee_threshold_percent = models.DecimalField("เกณฑ์%ทองที่เริ่มหัก", max_digits=5,
                                                decimal_places=2, default=Decimal("90"))
    is_active = models.BooleanField("ใช้งาน", default=True)

    class Meta:
        verbose_name = verbose_name_plural = "ตั้งค่าค่าบริการ"

    def __str__(self):
        return f"ค่าบริการ {self.fee_percent}% (เกณฑ์ {self.fee_threshold_percent}%)"


class InterestRate(models.Model):
    """อัตราดอกเบี้ยขายฝาก (%/เดือน)"""
    rate = models.DecimalField("อัตรา (%/เดือน)", max_digits=5, decimal_places=2, unique=True)
    is_active = models.BooleanField("ใช้งาน", default=True)

    class Meta:
        verbose_name = verbose_name_plural = "อัตราดอกเบี้ยขายฝาก"
        ordering = ["-rate"]

    def __str__(self):
        return f"{self.rate}%"


class Duration(models.Model):
    """ระยะเวลาขายฝาก (เดือน)"""
    months = models.PositiveIntegerField("จำนวนเดือน", unique=True)
    is_active = models.BooleanField("ใช้งาน", default=True)

    class Meta:
        verbose_name = verbose_name_plural = "ระยะเวลาขายฝาก"
        ordering = ["months"]

    def __str__(self):
        return f"{self.months} เดือน"


class ProductItem(models.Model):
    """เมนูสินค้า (เช่น เครื่องประดับเพชร)"""
    metal = models.ForeignKey(MetalType, on_delete=models.CASCADE,
                              verbose_name="ประเภท", related_name="items")
    name = models.CharField("ชื่อสินค้า", max_length=100)
    diamond_profit_percent = models.DecimalField("%กำไรเพชร", max_digits=5, decimal_places=2,
                                                 default=Decimal("0"))

    class Meta:
        verbose_name = verbose_name_plural = "เมนูสินค้า"

    def __str__(self):
        return self.name


class VatSetting(models.Model):
    """ตั้งค่าภาษีมูลค่าเพิ่ม (VAT) — คิดจากส่วนต่าง/ค่ากำเหน็จตามกฎภาษีทองไทย"""
    rate_percent = models.DecimalField("อัตรา VAT (%)", max_digits=5, decimal_places=2,
                                       default=Decimal("7"))
    is_active = models.BooleanField("ใช้งาน", default=True)

    class Meta:
        verbose_name = verbose_name_plural = "ตั้งค่า VAT"

    def __str__(self):
        return f"VAT {self.rate_percent}%"

    @classmethod
    def current_rate(cls):
        obj = cls.objects.filter(is_active=True).first()
        return obj.rate_percent if obj else Decimal("7")


class Supplier(models.Model):
    """ร้านส่ง / คู่ค้า (สำหรับธุรกรรมค้าส่ง)"""
    name = models.CharField("ชื่อร้านส่ง", max_length=200)
    tax_id = models.CharField("เลขผู้เสียภาษี", max_length=20, blank=True)
    tel = models.CharField("โทรศัพท์", max_length=40, blank=True)
    address = models.TextField("ที่อยู่", blank=True)
    is_active = models.BooleanField("ใช้งาน", default=True)

    class Meta:
        verbose_name = verbose_name_plural = "ร้านส่ง / คู่ค้า"

    def __str__(self):
        return self.name


class DocumentNumber(models.Model):
    """ตัวออกเลขที่เอกสารแบบ running ต่อ prefix ต่อเดือน (เช่น RC6907-0001)

    prefix: RC(รับซื้อ) · IV(ขาย) · J(ขายฝาก) · RD(ไถ่ออก) · MS/MB(สรุปเดือน) ฯลฯ
    ym: ปีพุทธ 2 หลัก + เดือน 2 หลัก (เช่น 6907 = ก.ค. 2569/2026)
    """
    prefix = models.CharField("รหัสนำหน้า", max_length=6)
    ym = models.CharField("ปีเดือน (YYMM พ.ศ.)", max_length=4)
    last_number = models.PositiveIntegerField("เลขล่าสุด", default=0)

    class Meta:
        verbose_name = verbose_name_plural = "เลขที่เอกสาร (running)"
        unique_together = ("prefix", "ym")

    def __str__(self):
        return f"{self.prefix}{self.ym} = {self.last_number}"

    @staticmethod
    def ym_of(on_date):
        """คืนค่า YYMM แบบปีพุทธ (เช่น 2026-07 → '6907')"""
        be_year = (on_date.year + 543) % 100
        return f"{be_year:02d}{on_date.month:02d}"

    @classmethod
    def next(cls, prefix, on_date, width=4):
        """ออกเลขถัดไปแบบปลอดภัยต่อ race (ใช้ในทรานแซกชัน) → เช่น 'RC6907-0001'"""
        from django.db import transaction
        ym = cls.ym_of(on_date)
        with transaction.atomic():
            seq, _ = cls.objects.select_for_update().get_or_create(prefix=prefix, ym=ym)
            seq.last_number += 1
            seq.save(update_fields=["last_number"])
        return f"{prefix}{ym}-{seq.last_number:0{width}d}"
