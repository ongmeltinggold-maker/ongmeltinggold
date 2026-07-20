"""
Pricing Engine — โมดูลคำนวณราคากลางของระบบร้านทอง ONG หลอมทอง

ยึดสูตรที่ลูกค้ายืนยัน (ตรวจสอบกับตัวอย่างจริงแล้วตรงทุกตัว):

ทอง:
    ราคาต่อกรัม = floor( ราคาทองแท่งรับซื้อ × FACTOR × (%ทอง/100) )
    ยอดรวม      = floor( ราคาต่อกรัม × น้ำหนักกรัม )
    ค่าบริการ   : ถ้า (ไม่ใช่ VIP) และ %ทอง < 90  → final = floor(ยอดรวม × (1 − fee))
                  อื่น ๆ (VIP หรือ ≥90%)          → final = ยอดรวม

เงิน / แพลทตินั่ม (ราคาตั้งเอง, ไม่หักค่าบริการ):
    ราคาต่อกรัม = floor( ราคาตั้ง × (%โลหะ/100) )
    ยอดรวม      = floor( ราคาต่อกรัม × น้ำหนักกรัม )

สำคัญ: ใช้ Decimal ทุกจุด และ "ตัดทศนิยม" = ปัดลง (ROUND_FLOOR)
"""
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_FLOOR

# --- ค่าคงที่ (default; ปรับได้ผ่านตั้งค่าในระบบ) ---
GOLD_FACTOR = Decimal("0.0656")          # ≈ 1/15.244 แปลงราคาต่อบาททองเป็นต่อกรัมบริสุทธิ์
FEE_THRESHOLD_PERCENT = Decimal("90")    # ทองต่ำกว่านี้จึงหักค่าบริการ
DEFAULT_FEE_PERCENT = Decimal("3")       # ค่าบริการเริ่มต้น (ปรับได้ 1–10%)

# ประเภทโลหะที่ใช้สูตร "ทอง" (× FACTOR × % + เงื่อนไขค่าบริการ)
GOLD_LIKE = {"gold", "nak"}              # นาก = สูตรทอง (รอลูกค้ายืนยัน; ปรับได้)
# ประเภทโลหะที่ใช้สูตร "ตั้งราคาเอง" (× % ไม่หักค่าบริการ)
FLAT_LIKE = {"silver", "platinum"}


def _D(x) -> Decimal:
    """แปลงเป็น Decimal อย่างปลอดภัย (ผ่าน str กัน float error)"""
    return x if isinstance(x, Decimal) else Decimal(str(x))


def floor_decimal(x) -> Decimal:
    """ตัดทศนิยมแบบปัดลงเป็นจำนวนเต็ม (ตามสเปก 'ไม่นับหลังจุดทศนิยม')"""
    return _D(x).to_integral_value(rounding=ROUND_FLOOR)


@dataclass
class PriceResult:
    metal_type: str
    price_per_gram: Decimal      # ราคาต่อกรัม (หลังตัดทศนิยม)
    subtotal: Decimal            # ยอดรวมก่อนหักค่าบริการ
    fee_applied: bool            # หักค่าบริการหรือไม่
    fee_percent: Decimal         # อัตราค่าบริการที่ใช้ (%)
    fee_amount: Decimal          # จำนวนเงินค่าบริการที่หัก
    final: Decimal               # ยอดสุทธิ

    def as_dict(self):
        d = asdict(self)
        # ให้ค่าเป็น str อ่านง่ายเวลา serialize
        return {k: (str(v) if isinstance(v, Decimal) else v) for k, v in d.items()}


def calc_gold(bar_buy_price, purity_percent, weight_gram, *,
              is_vip=False,
              fee_percent=DEFAULT_FEE_PERCENT,
              factor=GOLD_FACTOR,
              fee_threshold_percent=FEE_THRESHOLD_PERCENT,
              metal_type="gold") -> PriceResult:
    """คำนวณราคาทอง (หรือนาก) ตามสูตรทอง"""
    bar = _D(bar_buy_price)
    purity = _D(purity_percent)
    weight = _D(weight_gram)
    fee = _D(fee_percent)

    price_per_gram = floor_decimal(bar * _D(factor) * (purity / 100))
    subtotal = floor_decimal(price_per_gram * weight)

    fee_applied = (not is_vip) and (purity < _D(fee_threshold_percent))
    if fee_applied:
        final = floor_decimal(subtotal * (1 - fee / 100))
        fee_amount = subtotal - final
    else:
        final = subtotal
        fee_amount = Decimal("0")

    return PriceResult(metal_type, price_per_gram, subtotal,
                       fee_applied, fee if fee_applied else Decimal("0"),
                       fee_amount, final)


def calc_flat_metal(base_price, purity_percent, weight_gram, *,
                    metal_type="silver") -> PriceResult:
    """คำนวณราคาเงิน/แพลทตินั่ม (ราคาตั้งเอง, ไม่หักค่าบริการ)"""
    base = _D(base_price)
    purity = _D(purity_percent)
    weight = _D(weight_gram)

    price_per_gram = floor_decimal(base * (purity / 100))
    total = floor_decimal(price_per_gram * weight)

    return PriceResult(metal_type, price_per_gram, total,
                       False, Decimal("0"), Decimal("0"), total)


METHOD_PER_BAHT = "gold"   # ราคาต่อกรัม = base × factor × %  (ทอง/นาก)
METHOD_PER_GRAM = "flat"   # ราคาต่อกรัม = base × %            (เงิน/แพลทตินั่ม)


def calc(method, price_base, purity_percent, weight_gram, *,
         is_vip=False,
         apply_service_fee=False,
         fee_percent=DEFAULT_FEE_PERCENT,
         factor=GOLD_FACTOR,
         fee_threshold_percent=FEE_THRESHOLD_PERCENT,
         metal_type="") -> PriceResult:
    """
    เครื่องคำนวณกลาง (ขับด้วยพารามิเตอร์ — ให้ลูกค้ากำหนดสูตรเองต่อโลหะได้)

    method:
      - 'gold' (METHOD_PER_BAHT): ราคาต่อกรัม = floor(base × factor × %/100)
      - 'flat' (METHOD_PER_GRAM): ราคาต่อกรัม = floor(base × %/100)
    apply_service_fee: โลหะนี้หักค่าบริการไหม
    fee_threshold_percent: หักค่าบริการเฉพาะเมื่อ % < ค่านี้ (VIP ไม่หักเสมอ)
    """
    base = _D(price_base); purity = _D(purity_percent); weight = _D(weight_gram); fee = _D(fee_percent)
    if method == METHOD_PER_GRAM:
        price_per_gram = floor_decimal(base * (purity / 100))
    else:  # METHOD_PER_BAHT (ทอง/นาก)
        price_per_gram = floor_decimal(base * _D(factor) * (purity / 100))
    subtotal = floor_decimal(price_per_gram * weight)

    fee_applied = bool(apply_service_fee) and (not is_vip) and (purity < _D(fee_threshold_percent))
    if fee_applied:
        final = floor_decimal(subtotal * (1 - fee / 100))
        fee_amount = subtotal - final
    else:
        final = subtotal
        fee_amount = Decimal("0")
    return PriceResult(metal_type, price_per_gram, subtotal,
                       fee_applied, fee if fee_applied else Decimal("0"), fee_amount, final)


def calc_price(metal_type, price_base, purity_percent, weight_gram, *,
               is_vip=False, fee_percent=DEFAULT_FEE_PERCENT,
               factor=GOLD_FACTOR,
               fee_threshold_percent=FEE_THRESHOLD_PERCENT) -> PriceResult:
    """
    ตัวเลือกกลาง: เลือกสูตรตามประเภทโลหะ
    - gold/nak  : price_base = ราคาทองแท่งรับซื้อ 96.5%
    - silver/pt : price_base = ราคาตั้งเองต่อกรัม
    """
    mt = (metal_type or "").strip().lower()
    if mt in GOLD_LIKE:
        return calc_gold(price_base, purity_percent, weight_gram,
                         is_vip=is_vip, fee_percent=fee_percent, factor=factor,
                         fee_threshold_percent=fee_threshold_percent, metal_type=mt)
    if mt in FLAT_LIKE:
        return calc_flat_metal(price_base, purity_percent, weight_gram, metal_type=mt)
    raise ValueError(f"ไม่รู้จักประเภทโลหะ: {metal_type!r} (รองรับ: {GOLD_LIKE | FLAT_LIKE})")
