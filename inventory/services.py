"""บริการสต็อก — ตัดล็อตต้นทุนแบบ FIFO เมื่อขายออก"""
from decimal import Decimal
from .models import StockLot, LotConsumption


def consume_fifo(sale_detail, metal, weight):
    """
    ตัดสต็อกแบบ FIFO ตามล็อตที่รับเข้าก่อน คืน (cost_basis, shortfall_gram)
    - สร้าง LotConsumption ผูกรายการขาย ↔ ล็อต
    - ลด remaining_gram ของแต่ละล็อต
    - shortfall_gram > 0 = สต็อก(ที่มีล็อต)ไม่พอ (เตือนได้)
    """
    needed = Decimal(str(weight))
    cost = Decimal("0")
    lots = StockLot.objects.select_for_update().filter(
        metal=metal, remaining_gram__gt=0).order_by("received_date", "id")
    for lot in lots:
        if needed <= 0:
            break
        take = lot.remaining_gram if lot.remaining_gram < needed else needed
        c = (take * lot.unit_cost).quantize(Decimal("0.01"))
        LotConsumption.objects.create(sale_detail=sale_detail, lot=lot, weight_gram=take, cost=c)
        lot.remaining_gram -= take
        lot.save(update_fields=["remaining_gram"])
        cost += c
        needed -= take
    return cost, (needed if needed > 0 else Decimal("0"))
