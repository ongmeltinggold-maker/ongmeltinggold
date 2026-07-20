"""ตัวช่วยสร้าง PDF จาก template ด้วย WeasyPrint (รองรับ A4/A5)"""
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML


def render_pdf(request, template, context, filename="document", download=False):
    ctx = dict(context)
    # ขนาดกระดาษจาก query (?size=A4/A5) — ค่าเริ่มต้น A5
    size = (request.GET.get("size") or "A5").upper()
    ctx["page_size"] = "A4" if size == "A4" else "A5"
    html = render_to_string(template, ctx, request=request)
    pdf = HTML(string=html, base_url=request.build_absolute_uri("/")).write_pdf()
    resp = HttpResponse(pdf, content_type="application/pdf")
    want_download = download or request.GET.get("download") == "1"
    disp = "attachment" if want_download else "inline"
    resp["Content-Disposition"] = f'{disp}; filename="{filename}.pdf"'
    return resp
