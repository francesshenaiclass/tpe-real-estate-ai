import json
import csv
import time
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ── 設定區 ──────────────────────────────────────────────
CITY        = "台北市"
ZIP_CODES   = "100-103-104-105-106-108-110-111-112-114-115-116"
MAX_PAGES   = 150          # 要爬幾頁（每頁約 10 筆）
OUTPUT_CSV  = "hbhousing_listings.csv"
HEADLESS    = True       # False = 看見瀏覽器視窗（方便除錯）
# ────────────────────────────────────────────────────────


def parse_listing(item: dict) -> dict:
    """將單筆物件原始資料整理成輸出欄位"""

    doorplate = item.get("doorplate", "") or ""
    district  = re.match(r"^(\w+區)", doorplate)
    district  = district.group(1) if district else ""

    special      = item.get("special", "") or ""
    main_area    = item.get("mainArea",  "") or ""
    land_area    = item.get("landArea",  "") or ""
    floor        = str(item.get("floor",       "") or "")
    floor_total  = str(item.get("floorTotal",  "") or "")
    age          = item.get("age", "") or ""
    price        = item.get("price", "") or ""
    orig_price   = item.get("originalPrice", "") or ""
    obj_type     = item.get("type", "") or ""
    obj_name     = item.get("objName", "") or ""
    sn           = item.get("sn", "") or ""

    area_str  = f"{main_area}坪" if main_area else (f"{land_area}坪(地坪)" if land_area else "")
    floor_str = f"{floor}樓/{floor_total}樓" if floor and floor_total else (floor or floor_total)
    age_str   = f"{age}年" if age else ""

    if orig_price and orig_price != price:
        price_str = f"{orig_price}萬 → {price}萬"
    else:
        price_str = f"{price}萬" if price else ""

    return {
        "物件編號": sn,
        "物件名稱": obj_name,
        "地區":     district,
        "地址":     doorplate,
        "格局":     special,
        "坪數":     area_str,
        "樓層":     floor_str,
        "屋齡":     age_str,
        "類型":     obj_type,
        "價格":     price_str,
    }


def resolve_nuxt_data(raw: list) -> list[dict]:
    """
    把 __NUXT_DATA__ 的扁平陣列還原成物件列表。
    住商網站把資料打包在 buyHouseListDatas 這個 key 後面。
    """
    flat = {i: v for i, v in enumerate(raw)}

    for i, v in flat.items():
        if v == "buyHouseListDatas":
            list_ref = flat.get(i + 1)
            if not isinstance(list_ref, int):
                continue
            item_indices = flat.get(list_ref, [])
            if not isinstance(item_indices, list):
                continue

            listings = []
            for item_idx in item_indices:
                item_dict = flat.get(item_idx)
                if not isinstance(item_dict, dict):
                    continue
                resolved = {}
                for k, ref in item_dict.items():
                    resolved[k] = flat.get(ref, ref)
                listings.append(resolved)
            return listings

    return []


def scrape():
    base_url = f"https://www.hbhousing.com.tw/buyhouse/{CITY}/{ZIP_CODES}"
    fieldnames = ["物件編號", "物件名稱", "地區", "地址", "格局", "坪數", "樓層", "屋齡", "類型", "價格"]
    all_rows = []

    print(f"🏠 住商不動產爬蟲啟動")
    print(f"   城市：{CITY}　區域碼：{ZIP_CODES}")
    print(f"   最多爬取 {MAX_PAGES} 頁\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-TW",
        )
        page = context.new_page()

        for page_num in range(51, MAX_PAGES + 1):
            url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
            print(f"📄 爬取第 {page_num} 頁：{url}")

            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeout:
                print(f"   ⚠️  頁面載入逾時，嘗試繼續解析...")

            # 等待物件列表出現
            try:
                page.wait_for_selector("section.\\@container", timeout=10000)
            except PlaywrightTimeout:
                print(f"   ⚠️  找不到物件列表元素，可能是最後一頁")

            # 從 __NUXT_DATA__ 解析資料
            nuxt_json = page.evaluate("""
                () => {
                    const el = document.getElementById('__NUXT_DATA__');
                    if (!el) return null;
                    try { return JSON.parse(el.textContent); }
                    catch(e) { return null; }
                }
            """)

            if not nuxt_json:
                print(f"   ❌ 無法取得 __NUXT_DATA__，停止爬取")
                break

            items = resolve_nuxt_data(nuxt_json)

            if not items:
                # 備援：直接從 DOM 解析
                items = parse_from_dom(page)

            if not items:
                print(f"   ℹ️  本頁無資料，停止爬取")
                break

            rows = [parse_listing(i) for i in items]
            all_rows.extend(rows)
            print(f"   ✅ 取得 {len(rows)} 筆，累計 {len(all_rows)} 筆")

            # 確認是否還有下一頁
            has_next = page.evaluate("""
                () => {
                    const btns = document.querySelectorAll('nav button i');
                    for (const b of btns) {
                        if (b.className.includes('caret-right') && !b.className.includes('double')) {
                            const btn = b.closest('button');
                            return btn && !btn.disabled;
                        }
                    }
                    return false;
                }
            """)
            if not has_next and page_num < MAX_PAGES:
                print(f"   ℹ️  沒有下一頁，爬取結束")
                break

            time.sleep(1.5)

        browser.close()

    # 儲存 CSV
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n🎉 完成！共 {len(all_rows)} 筆，已儲存至 {OUTPUT_CSV}")


def parse_from_dom(page) -> list[dict]:
    """
    備援方案：直接從 DOM 元素抓取資料
    當 __NUXT_DATA__ 解析失敗時使用
    """
    items = page.evaluate("""
        () => {
            const results = [];
            const sections = document.querySelectorAll('section.\\\\@container');

            sections.forEach(sec => {
                const obj = {};

                // 物件編號
                const snEl = sec.querySelector('p.font-montserrat');
                if (snEl) {
                    const m = snEl.textContent.match(/[A-Z]{2}\\d+/);
                    obj.sn = m ? m[0] : '';
                }

                // 物件名稱
                const nameEl = sec.querySelector('h3 a');
                obj.objName = nameEl ? nameEl.textContent.trim() : '';

                // 地址
                const addrEl = [...sec.querySelectorAll('p.attribute span')]
                    .find(el => el.textContent.includes('區'));
                obj.doorplate = addrEl ? addrEl.textContent.trim() : '';

                // 房屋資訊
                const infoEl = [...sec.querySelectorAll('p.attribute span')]
                    .find(el => el.textContent.includes('年') || el.textContent.includes('坪'));
                if (infoEl) {
                    const text = infoEl.textContent;
                    // 類型
                    const typeM = text.match(/^([大樓公寓華廈透天店面]+)/);
                    obj.type = typeM ? typeM[1] : '';
                    // 格局
                    const roomM = text.match(/(\\d+房\\(室\\)[^|]+)/);
                    obj.special = roomM ? roomM[1].trim() : '';
                    // 屋齡
                    const ageM = text.match(/(\\d+\\.?\\d*)年/);
                    obj.age = ageM ? ageM[1] : '';
                    // 樓層
                    const floorM = text.match(/(\\d+)樓\\/(\\d+)樓/);
                    if (floorM) { obj.floor = floorM[1]; obj.floorTotal = floorM[2]; }
                    // 坪數
                    const areaM = text.match(/(\\d+\\.?\\d*)坪/g);
                    if (areaM) obj.mainArea = areaM[areaM.length - 1].replace('坪', '');
                }

                // 價格
                const priceEl = sec.querySelector('span.text-error span');
                obj.price = priceEl ? priceEl.textContent.replace(/[^\\d]/g, '') : '';

                const strikeEl = sec.querySelector('span.line-through');
                obj.originalPrice = strikeEl ? strikeEl.textContent.replace(/[^\\d]/g, '') : '';

                if (obj.objName) results.push(obj);
            });

            return results;
        }
    """)
    return items or []


if __name__ == "__main__":
    # 安裝提示
    try:
        from playwright.sync_api import sync_playwright
        scrape()
    except ImportError:
        print("❌ 請先安裝 Playwright：")
        print("   pip install playwright")
        print("   playwright install chromium")
    except Exception as e:
        print(f"❌ 執行錯誤：{e}")
        import traceback
        traceback.print_exc()