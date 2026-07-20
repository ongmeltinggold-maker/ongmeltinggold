"""ส่งข้อความ LINE (Messaging API) — ทำงานจริงเมื่อกรอก token แล้ว"""
import json
import urllib.request
from .models import LineConfig, CustomerLine, NotificationLog


def get_config():
    return LineConfig.objects.first()


def push_line(customer, message):
    """ส่ง push ไป LINE ของลูกค้า · คืนสถานะ (sent/skipped/failed) + บันทึก log"""
    cfg = get_config()
    line = CustomerLine.objects.filter(customer=customer).first()
    status = "skipped"
    if cfg and cfg.enabled and cfg.channel_access_token and line:
        try:
            req = urllib.request.Request(
                "https://api.line.me/v2/bot/message/push",
                data=json.dumps({"to": line.line_user_id,
                                 "messages": [{"type": "text", "text": message}]}).encode("utf-8"),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {cfg.channel_access_token}"})
            urllib.request.urlopen(req, timeout=10)
            status = "sent"
        except Exception:
            status = "failed"
    NotificationLog.objects.create(customer=customer, channel="line",
                                   message=message, status=status)
    return status
