#!/usr/bin/env python3
"""
Scraper ดึงข้อมูลลูกค้าเดิมจากระบบ AGALIGOLD (console.onglomthong.com)
รันบน 'เครื่องที่เข้าเว็บเดิมได้' (มี credentials ของลูกค้า) — ไม่ใช่บนเซิร์ฟเวอร์ใหม่

ติดตั้ง:  pip install playwright && playwright install chromium
รัน:      python scrape_legacy.py --user admin --password '****' --out customers.json
จากนั้น:  python manage.py import_legacy customers.json   (ในโปรเจกต์ระบบใหม่)

* ดึงจากหน้า customer_list.php (ชื่อ/ที่อยู่/เบอร์/วันเกิด) + เปิด customer_edit เพื่ออ่านเลขบัตร
* ทำงานตามที่เว็บ AGALIGOLD แสดง (ยึดโครงสร้างหน้าเดิม) — ปรับ selector ได้ถ้าเว็บเปลี่ยน
"""
import argparse, json, time
from urllib.parse import urljoin

BASE = "https://console.onglomthong.com/"


def run(user, password, out, with_id=True, delay=0.3):
    from playwright.sync_api import sync_playwright
    data = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        pg = b.new_context().new_page()
        # login
        pg.goto(urljoin(BASE, "login.php"))
        pg.fill('input[name="username"]', user)
        pg.fill('input[name="password"]', password)
        pg.click('button:has-text("Login"), input[type=submit]')
        pg.wait_for_load_state("networkidle")

        page_no = 1
        while True:
            url = urljoin(BASE, f"customer/customer_list.php?txtSearch=&Page={page_no}")
            pg.goto(url); pg.wait_for_load_state("networkidle")
            rows = pg.query_selector_all("table tbody tr")
            if not rows:
                break
            found = 0
            for tr in rows:
                tds = tr.query_selector_all("td")
                if len(tds) < 5:
                    continue
                name = tds[1].inner_text().strip()
                addr = tds[2].inner_text().strip()
                tel = tds[3].inner_text().strip()
                dob = tds[4].inner_text().strip()
                if not name:
                    continue
                rec = {"name_th": name, "address": addr, "tel": tel, "birthday": dob,
                       "national_id": "", "name_en": "", "religion": "",
                       "card_issue_date": "", "card_expire_date": ""}
                # เปิดหน้าแก้ไขเพื่ออ่านเลขบัตร + ฟิลด์เต็ม (ถ้าเปิด with_id)
                if with_id:
                    link = tds[-1].query_selector("a")
                    if link:
                        href = link.get_attribute("href")
                        ep = b.new_page()
                        try:
                            ep.goto(urljoin(BASE, "customer/" + href)); ep.wait_for_load_state("networkidle")
                            def val(n):
                                el = ep.query_selector(f'[name="{n}"]')
                                return el.get_attribute("value") if el else ""
                            rec["national_id"] = (val("username") or "").strip()
                            rec["name_en"] = (val("eng_name") or "").strip()
                            rec["religion"] = (val("religion") or "").strip()
                            rec["card_issue_date"] = (val("date_transaction") or "").strip()
                            rec["card_expire_date"] = (val("date_expire") or "").strip()
                        except Exception:
                            pass
                        finally:
                            ep.close()
                        time.sleep(delay)
                data.append(rec); found += 1
            print(f"หน้า {page_no}: +{found} (รวม {len(data)})")
            page_no += 1
            if page_no > 50:   # กันลูปเกิน
                break
        b.close()
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"บันทึก {len(data)} รายการ → {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--user", required=True)
    ap.add_argument("--password", required=True)
    ap.add_argument("--out", default="customers.json")
    ap.add_argument("--no-id", action="store_true", help="ไม่เปิดหน้าแก้ไขเพื่ออ่านเลขบัตร (เร็วขึ้น)")
    a = ap.parse_args()
    run(a.user, a.password, a.out, with_id=not a.no_id)
