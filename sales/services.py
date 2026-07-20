"""บริการคำนวณราคา — เชื่อม Pricing Engine กับค่าตั้งค่าในระบบ (สูตรกำหนดเองต่อโลหะ)"""
from decimal import Decimal
from pricing import engine
from pricing.engine import floor_decimal
from catalog.models import (ServiceFeeSetting, MetalType, MetalPriceSetting,
                            GoldPrice, VatSetting)


def fee_setting():
    """ค่าบริการ % เริ่มต้น (global, ปรับ 1–10%)"""
    s = ServiceFeeSetting.objects.filter(is_active=True).first()
    if s:
        return s.fee_percent, s.gold_factor, s.fee_threshold_percent
    return Decimal("3"), Decimal("0.0656"), Decimal("90")


def base_price_for(metal: MetalType):
    """ราคาตั้งต้นตาม price_source ของโลหะ (อ้างอิงทองแท่ง หรือ ตั้งเอง)"""
    if metal.price_source == MetalType.SOURCE_MANUAL:
        ps = MetalPriceSetting.objects.filter(metal=metal).first()
        return ps.base_price_per_gram if ps else Decimal("0")
    g = GoldPrice.objects.order_by("-date").first()
    return g.bar_buy if g else Decimal("0")


def compute_buy(metal: MetalType, purity, weight, is_vip=False, base_price=None, fee_percent=None):
    """คำนวณราคารับซื้อ ตาม 'สูตรที่ตั้งไว้ต่อโลหะ' (method/factor/fee/threshold/source)"""
    fee_default, _, _ = fee_setting()
    fee = Decimal(str(fee_percent)) if fee_percent not in (None, "") else fee_default
    base = Decimal(str(base_price)) if base_price not in (None, "") else base_price_for(metal)
    result = engine.calc(
        metal.formula, base, purity, weight,
        is_vip=is_vip,
        apply_service_fee=metal.apply_service_fee,
        fee_percent=fee,
        factor=metal.factor,
        fee_threshold_percent=metal.fee_threshold_percent,
        metal_type=metal.code)
    return result, base, fee


def compute_sell(bar_sell_price, weight_gram, labor_cost):
    """ขายออก: มูลค่าเนื้อทอง (ยกเว้น VAT) + ค่ากำเหน็จ + VAT 7% เฉพาะค่ากำเหน็จ/ส่วนต่าง"""
    BAHT = Decimal("15.244")
    price = Decimal(str(bar_sell_price)); weight = Decimal(str(weight_gram)); labor = Decimal(str(labor_cost or 0))
    gold_value = floor_decimal(weight / BAHT * price)
    vat_rate = VatSetting.current_rate() / Decimal("100")
    vat = floor_decimal(labor * vat_rate)
    total = gold_value + labor + vat
    return {"gold_value": gold_value, "labor": labor, "vat_base": labor, "vat": vat, "total": total}
