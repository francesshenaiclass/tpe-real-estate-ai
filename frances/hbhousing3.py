import json
import csv
import time
import re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout


# ── 設定區 ──────────────────────────────────────────────
CITY        = "台北市"
MAX_PAGES   = 120
OUTPUT_CSV  = "hbhousing_all.csv"
HEADLESS    = True

DISTRICT_MAP = {
    "大同區": "103",
    "中山區": "104",
    "松山區": "105",
    "大安區": "106",
    "萬華區": "108",
    "信義區": "110",
    "士林區": "111",
    "北投區": "112",
    "內湖區": "114",
    "南港區": "115",
    "文山區": "116",
}
# ────────────────────────────────────────────────────────


def parse_listing(item: dict) -> dict:
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


def get_total_pages(raw: list) -> int | None:
    flat = {i: v for i, v in enumerate(raw)}
    keywords = {"totalPage", "pageCount", "lastPage", "totalPages"}
    for i, v in flat.items():
        if not isinstance(v, str):
            continue
        if v in keywords:
            ref = flat.get(i + 1)
            val = flat.get(ref, ref) if isinstance(ref, int) else ref
            try:
                return int(val)
            except (TypeError, ValueError):
                continue
    return None


def scrape_district(page, district_name: str, zip_code: str) -> list[dict]:
    base_url = f"https://www.hbhousing.com.tw/buyhouse/{CITY}/{zip_code}"
    district_rows = []
    seen_sns = set()  # ✅ 用來偵測重複物件編號，防止同一區被重複抓

    print(f"\n{'='*55}")
    print(f"📍 開始爬取：{district_name}（郵遞區號 {zip_code}）")
    print(f"{'='*55}")

    for page_num in range(1, MAX_PAGES + 1):
        url = base_url if page_num == 1 else f"{base_url}?page={page_num}"
        print(f"  📄 第 {page_num:>3} 頁：{url}")

        # ── 載入頁面 ──────────────────────────────────────────
        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
        except PlaywrightTimeout:
            print(f"       ⚠️  頁面載入逾時，嘗試繼續解析...")

        try:
            page.wait_for_selector("section.\\@container", timeout=10000)
        except PlaywrightTimeout:
            print(f"       ⚠️  找不到物件列表，視為末頁，結束 {district_name}")
            break  # ✅ 找不到元素直接結束此區，跳往下一區

        # ── 解析 __NUXT_DATA__ ────────────────────────────────
        nuxt_json = page.evaluate("""
            () => {
                const el = document.getElementById('__NUXT_DATA__');
                if (!el) return null;
                try { return JSON.parse(el.textContent); }
                catch(e) { return null; }
            }
        """)

        if not nuxt_json:
            print(f"       ❌ 無法取得 __NUXT_DATA__，結束 {district_name}")
            break  # ✅ 取不到資料直接結束此區

        items = resolve_nuxt_data(nuxt_json)

        if not items:
            items = parse_from_dom(page)

        if not items:
            print(f"       ℹ️  本頁無資料，{district_name} 爬取結束")
            break  # ✅ 無資料直接結束此區

        # ── 過濾重複物件（同一區翻頁時偶爾出現） ────────────────
        new_items = []
        for item in items:
            sn = item.get("sn", "")
            if sn and sn in seen_sns:
                continue  # ✅ 已抓過的物件跳過
            if sn:
                seen_sns.add(sn)
            new_items.append(item)

        if not new_items:
            print(f"       ℹ️  本頁全為重複資料，{district_name} 爬取結束")
            break  # ✅ 全是重複物件，表示已繞回第一頁，立即結束

        rows = [parse_listing(i) for i in new_items]
        district_rows.extend(rows)
        print(f"       ✅ 取得 {len(rows):>2} 筆（過濾後），{district_name} 累計 {len(district_rows)} 筆")

        # ── 判斷是否還有下一頁（三層防護） ──────────────────────

        # 【第一層】從 __NUXT_DATA__ 讀總頁數（最準確）
        total_pages = get_total_pages(nuxt_json)
        if total_pages is not None:
            if page_num >= total_pages:
                print(f"       ℹ️  已達總頁數 {total_pages}，{district_name} 爬取結束")
                break  # ✅ 到達最後一頁，結束此區，自動進入下一區
            else:
                time.sleep(1.5)
                continue

        # 【第二層】偵測「下一頁」按鈕
        has_next = page.evaluate("""
            () => {
                const byAria = document.querySelector(
                    'button[aria-label="下一頁"], a[aria-label="下一頁"]'
                );
                if (byAria) return !byAria.disabled && !byAria.hasAttribute('disabled');

                const navBtns = [...document.querySelectorAll('nav button')];
                if (navBtns.length === 0) return false;
                const last = navBtns[navBtns.length - 1];
                return !last.disabled && !last.hasAttribute('disabled');
            }
        """)
        if not has_next:
            print(f"       ℹ️  下一頁按鈕不可用，{district_name} 爬取結束")
            break  # ✅ 沒有下一頁，結束此區，自動進入下一區

        # 【第三層】本頁筆數偏少
        if len(rows) < 5:
            print(f"       ℹ️  本頁僅 {len(rows)} 筆，判斷為末頁，{district_name} 爬取結束")
            break  # ✅ 筆數太少，結束此區

        time.sleep(1.5)

    return district_rows


def scrape():
    fieldnames = ["物件編號", "物件名稱", "地區", "地址", "格局", "坪數", "樓層", "屋齡", "類型", "價格"]
    all_rows = []

    print(f"🏠 住商不動產爬蟲啟動（分區模式）")
    print(f"   城市：{CITY}")
    print(f"   爬取區域：{', '.join(DISTRICT_MAP.keys())}")
    print(f"   每區最多 {MAX_PAGES} 頁\n")

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

        for district_name, zip_code in DISTRICT_MAP.items():
            rows = scrape_district(page, district_name, zip_code)
            all_rows.extend(rows)

            district_csv = f"{district_name}_listings.csv"
            with open(district_csv, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            print(f"  💾 {district_name} 已儲存 → {district_csv}（{len(rows)} 筆）")

            time.sleep(2)  # 區與區之間的間隔

        browser.close()

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{'='*55}")
    print(f"🎉 全部完成！共 {len(all_rows)} 筆")
    print(f"   合併總檔 → {OUTPUT_CSV}")
    print(f"   各區分檔 → 各區名_listings.csv")
    print(f"{'='*55}")


def parse_from_dom(page) -> list[dict]:
    items = page.evaluate("""
        () => {
            const results = [];
            const sections = document.querySelectorAll('section.\\\\@container');

            sections.forEach(sec => {
                const obj = {};

                const snEl = sec.querySelector('p.font-montserrat');
                if (snEl) {
                    const m = snEl.textContent.match(/[A-Z]{2}\\d+/);
                    obj.sn = m ? m[0] : '';
                }

                const nameEl = sec.querySelector('h3 a');
                obj.objName = nameEl ? nameEl.textContent.trim() : '';

                const addrEl = [...sec.querySelectorAll('p.attribute span')]
                    .find(el => el.textContent.includes('區'));
                obj.doorplate = addrEl ? addrEl.textContent.trim() : '';

                const infoEl = [...sec.querySelectorAll('p.attribute span')]
                    .find(el => el.textContent.includes('年') || el.textContent.includes('坪'));
                if (infoEl) {
                    const text = infoEl.textContent;
                    const typeM = text.match(/^([大樓公寓華廈透天店面]+)/);
                    obj.type = typeM ? typeM[1] : '';
                    const roomM = text.match(/(\\d+房\\(室\\)[^|]+)/);
                    obj.special = roomM ? roomM[1].trim() : '';
                    const ageM = text.match(/(\\d+\\.?\\d*)年/);
                    obj.age = ageM ? ageM[1] : '';
                    const floorM = text.match(/(\\d+)樓\\/(\\d+)樓/);
                    if (floorM) { obj.floor = floorM[1]; obj.floorTotal = floorM[2]; }
                    const areaM = text.match(/(\\d+\\.?\\d*)坪/g);
                    if (areaM) obj.mainArea = areaM[areaM.length - 1].replace('坪', '');
                }

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