"""สร้าง XML e-Tax (โครงร่างตามแนวทาง ETDA/สรรพากร — เติมรายละเอียดตอน onboarding จริง)"""
from xml.sax.saxutils import escape
from .models import ETaxConfig, ETaxDocument


def build_xml(bill):
    """สร้าง XML ใบกำกับภาษีอิเล็กทรอนิกส์แบบย่อจากบิล (skeleton)

    หมายเหตุ: โครงสร้างจริงต้องตาม schema ETDA (TaxInvoice_CrossIndustryInvoice)
    + ลงลายเซ็นดิจิทัลด้วยใบรับรอง CA ก่อนส่ง — ส่วนนั้นทำตอน onboarding
    """
    cfg = ETaxConfig.objects.first()
    seller_name = (cfg.seller_name if cfg and cfg.seller_name else "")
    seller_tax = (cfg.seller_tax_id if cfg and cfg.seller_tax_id else "")
    cust = bill.customer
    lines = []
    for i, d in enumerate(bill.details.all(), 1):
        lines.append(
            f'    <Line num="{i}">'
            f'<Item>{escape(d.metal.name_th)}</Item>'
            f'<Qty unit="gram">{d.weight_gram}</Qty>'
            f'<Amount>{d.amount:.2f}</Amount>'
            f'<VAT>{d.vat_amount:.2f}</VAT></Line>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TaxInvoice>\n'
        f'  <DocNo>{escape(bill.doc_no or "")}</DocNo>\n'
        f'  <Date>{bill.date}</Date>\n'
        f'  <Seller><Name>{escape(seller_name)}</Name><TaxId>{seller_tax}</TaxId></Seller>\n'
        f'  <Buyer><Name>{escape(cust.name_th if cust else "ลูกค้าทั่วไป")}</Name>'
        f'<TaxId>{escape(cust.national_id if cust else "")}</TaxId></Buyer>\n'
        '  <Lines>\n' + "\n".join(lines) + '\n  </Lines>\n'
        f'  <VatTotal>{bill.vat_amount:.2f}</VatTotal>\n'
        f'  <GrandTotal>{bill.total_amount:.2f}</GrandTotal>\n'
        '</TaxInvoice>')


def create_etax_document(bill):
    """สร้าง/อัปเดตเอกสาร e-Tax สถานะ draft (ยังไม่ลงลายเซ็น/ส่ง)"""
    xml = build_xml(bill)
    doc, _ = ETaxDocument.objects.update_or_create(
        bill=bill, defaults=dict(xml=xml, status=ETaxDocument.DRAFT))
    return doc
