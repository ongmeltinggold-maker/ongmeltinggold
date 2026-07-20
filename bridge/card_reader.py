#!/usr/bin/env python3
"""
ONG Card Reader Bridge — อ่านบัตรประชาชนไทยผ่านเครื่องอ่าน (PC/SC) แล้วให้เว็บดึงข้อมูล

รันบนเครื่องหน้าร้านที่ต่อเครื่องอ่านบัตร:
    pip install pyscard
    python card_reader.py
เปิดพอร์ต http://127.0.0.1:8765/read → คืน JSON ข้อมูลบัตร (ให้หน้าเว็บ fetch มาเติมฟอร์ม)

* ต้องมี PC/SC: Windows มีในตัว · Linux: apt install pcscd libpcsclite-dev · macOS มีในตัว
* แทน keyboard-emulation ของ Siam ID เดิม — ปลอดภัยกว่า (ส่ง JSON ตรง + ทำ audit ได้)
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8765
MOCK = "--mock" in sys.argv   # โหมดทดสอบ: ไม่ต้องมีเครื่องอ่าน (คืนข้อมูลตัวอย่าง)

MOCK_DATA = {
    "national_id": "1234567890123",
    "name_th": "นาย ทดสอบ ระบบบัตร",
    "name_en": "Mr. Test Card",
    "birthday": "1 มกราคม 2540",
    "gender": "1",
    "address": "99/9 หมู่ 1 ต.ตลาดใหญ่ อ.เมืองภูเก็ต จ.ภูเก็ต",
    "card_issue_date": "1 มกราคม 2560",
    "card_expire_date": "1 มกราคม 2570",
}

# ---- APDU มาตรฐานสำหรับบัตรประชาชนไทย ----
SELECT = [0x00, 0xA4, 0x04, 0x00, 0x08, 0xA0, 0x00, 0x00, 0x00, 0x54, 0x48, 0x00, 0x01]
CMD = {
    "cid":     [0x80, 0x00, 0x04, 0x02, 0x00, 0x0D],
    "th_name": [0x80, 0x01, 0x01, 0x02, 0x00, 0x64],
    "en_name": [0x80, 0x02, 0x01, 0x02, 0x00, 0x64],
    "birth":   [0x80, 0x03, 0x01, 0x02, 0x00, 0x08],
    "gender":  [0x80, 0x04, 0x01, 0x02, 0x00, 0x01],
    "issuer":  [0x80, 0x05, 0x01, 0x02, 0x00, 0x64],
    "issue":   [0x80, 0x06, 0x01, 0x02, 0x00, 0x08],
    "expire":  [0x80, 0x07, 0x01, 0x02, 0x00, 0x08],
    "address": [0x80, 0x08, 0x01, 0x02, 0x00, 0x64],
}


def _thai(data):
    return bytes(data).decode("tis-620", "ignore").strip().replace("#", " ").strip()


def _thdate(s):
    # YYYYMMDD (พ.ศ.) → "D M YYYY" (ไทย)
    s = s.strip()
    if len(s) == 8 and s.isdigit():
        return f"{int(s[6:8])} {int(s[4:6])} {s[0:4]}"
    return s


def read_card():
    if MOCK:
        return dict(MOCK_DATA)
    from smartcard.System import readers
    from smartcard.util import toHexString  # noqa

    rlist = readers()
    if not rlist:
        raise RuntimeError("ไม่พบเครื่องอ่านบัตร (ตรวจสอบการเสียบ USB / บริการ PC/SC)")
    conn = rlist[0].createConnection()
    conn.connect()

    # เลือก applet บัตรประชาชน
    conn.transmit(SELECT)

    def read(cmd):
        # ส่งคำสั่ง แล้ว GET RESPONSE ตามความยาว (Le อยู่ท้าย apdu)
        le = cmd[-1]
        data, sw1, sw2 = conn.transmit(cmd)
        resp, sw1, sw2 = conn.transmit([0x00, 0xC0, 0x00, 0x00, le])
        return resp

    out = {
        "national_id": _thai(read(CMD["cid"])),
        "name_th":     _thai(read(CMD["th_name"])),
        "name_en":     _thai(read(CMD["en_name"])),
        "birthday":    _thdate(_thai(read(CMD["birth"]))),
        "gender":      _thai(read(CMD["gender"])),
        "address":     _thai(read(CMD["address"])),
        "card_issue_date":  _thdate(_thai(read(CMD["issue"]))),
        "card_expire_date": _thdate(_thai(read(CMD["expire"]))),
    }
    return out


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Type", "application/json; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path.startswith("/read"):
            try:
                payload = {"ok": True, "data": read_card()}
                code = 200
            except Exception as e:
                payload = {"ok": False, "error": str(e)}
                code = 200  # ให้เว็บอ่าน error ได้
            self.send_response(code); self._cors(); self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_response(404); self._cors(); self.end_headers()
            self.wfile.write(b'{"ok":false,"error":"not found"}')

    def log_message(self, *a):  # เงียบ
        pass


if __name__ == "__main__":
    mode = "MOCK (ข้อมูลตัวอย่าง)" if MOCK else "PC/SC (เครื่องอ่านจริง)"
    print(f"ONG Card Reader Bridge [{mode}] — http://127.0.0.1:{PORT}/read  (Ctrl+C เพื่อหยุด)")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
