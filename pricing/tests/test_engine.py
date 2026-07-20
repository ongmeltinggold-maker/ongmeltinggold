"""
Unit tests สำหรับ Pricing Engine — เทียบกับตัวอย่างที่ลูกค้าให้มาโดยตรง
รันด้วย: pytest pricing/tests/test_engine.py -v
"""
from decimal import Decimal
import pytest

from pricing.engine import calc_gold, calc_flat_metal, calc_price, floor_decimal, calc


# ---------- ทอง ----------
def test_gold_75_percent_deducts_fee():
    """65,300 × 0.0656 × 75% = 3,212 → ×15.16 = 48,693 → −3% = 47,232"""
    r = calc_gold(65300, 75, "15.16")
    assert r.price_per_gram == Decimal("3212")
    assert r.subtotal == Decimal("48693")
    assert r.fee_applied is True
    assert r.final == Decimal("47232")


def test_gold_91_percent_no_fee():
    """65,300 × 0.0656 × 91% = 3,898 → ×15.16 = 59,093 → ไม่หัก (≥90%)"""
    r = calc_gold(65300, 91, "15.16")
    assert r.price_per_gram == Decimal("3898")
    assert r.subtotal == Decimal("59093")
    assert r.fee_applied is False
    assert r.final == Decimal("59093")


def test_gold_vip_never_deducts_even_below_90():
    """ลูกค้า VIP: ทองต่ำกว่า 90% ก็ไม่หักค่าบริการ"""
    r = calc_gold(65300, 75, "15.16", is_vip=True)
    assert r.fee_applied is False
    assert r.final == r.subtotal == Decimal("48693")


def test_gold_exactly_90_percent_no_fee():
    """ขอบเขต: ทอง 90% พอดี = ไม่หัก (90 ขึ้นไปไม่หัก)"""
    r = calc_gold(65300, 90, "15.16")
    assert r.fee_applied is False


def test_gold_fee_percent_adjustable():
    """ค่าบริการปรับได้ (เช่น 5%) — หัก 5% แทน 3%"""
    r = calc_gold(65300, 75, "15.16", fee_percent=5)
    # subtotal 48,693 → ×0.95 = 46,258.35 → floor 46,258
    assert r.subtotal == Decimal("48693")
    assert r.final == Decimal("46258")


# ---------- เงิน / แพลทตินั่ม ----------
def test_silver():
    """46 × 95% = 43 → ×10.02 = 430"""
    r = calc_flat_metal(46, 95, "10.02", metal_type="silver")
    assert r.price_per_gram == Decimal("43")
    assert r.final == Decimal("430")
    assert r.fee_applied is False


def test_platinum():
    """700 × 90% = 630 → ×10.02 = 6,312"""
    r = calc_flat_metal(700, 90, "10.02", metal_type="platinum")
    assert r.price_per_gram == Decimal("630")
    assert r.final == Decimal("6312")


# ---------- ตัวเลือกกลาง calc_price ----------
@pytest.mark.parametrize("metal,base,purity,weight,expected_final", [
    ("gold", 65300, 75, "15.16", "47232"),
    ("gold", 65300, 91, "15.16", "59093"),
    ("silver", 46, 95, "10.02", "430"),
    ("platinum", 700, 90, "10.02", "6312"),
    ("nak", 65300, 75, "15.16", "47232"),   # นาก = สูตรทอง (default)
])
def test_calc_price_dispatch(metal, base, purity, weight, expected_final):
    r = calc_price(metal, base, purity, weight)
    assert r.final == Decimal(expected_final)


def test_unknown_metal_raises():
    with pytest.raises(ValueError):
        calc_price("wood", 100, 90, 10)


# ---------- generic calc() (สูตรกำหนดเอง) ----------
def test_calc_generic_gold_matches_legacy():
    r = calc("gold", 65300, 75, "15.16", apply_service_fee=True)
    assert r.final == Decimal("47232")


def test_calc_generic_flat_matches_legacy():
    r = calc("flat", 46, 95, "10.02", apply_service_fee=False)
    assert r.final == Decimal("430")


def test_calc_custom_factor_and_threshold():
    """โลหะที่ตั้ง factor/threshold เอง — เช่น นาก หักเฉพาะ <80%"""
    # 65300 × 0.0656 × 85% = 3641 → ×10 = 36410 → 85<80? ไม่ → ไม่หัก
    r = calc("gold", 65300, 85, "10", apply_service_fee=True, fee_threshold_percent=80)
    assert r.fee_applied is False
    # 75<80 → หัก
    r2 = calc("gold", 65300, 75, "10", apply_service_fee=True, fee_threshold_percent=80)
    assert r2.fee_applied is True


def test_calc_apply_fee_false_never_deducts():
    r = calc("gold", 65300, 50, "10", apply_service_fee=False)
    assert r.fee_applied is False


# ---------- floor helper ----------
def test_floor_truncates_not_rounds():
    assert floor_decimal("3212.99") == Decimal("3212")
    assert floor_decimal("430.86") == Decimal("430")
