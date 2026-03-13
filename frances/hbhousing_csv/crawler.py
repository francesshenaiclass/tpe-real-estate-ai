import json
import csv
import time
import math
import random
import os

from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth


# ─────────────────────────────
# 基本設定
# ─────────────────────────────

CITY = "台北市"
MAX_PAGES = 120
PER_PAGE = 10
HEADLESS = False

OUTPUT_DIR = "hbhousing_csv"

DISTRICT_MAP = {
    "中正區": "100",
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

USER_AGENTS = [
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122 Safari/537.36",
"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121 Safari/537.36",
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
]


# ─────────────────────────────
# 人類行為模擬
# ─────────────────────────────

def human_sleep(a=1.2, b=3.5):
    time.sleep(random.uniform(a, b))


def random_mouse_move(page):

    width = random.randint(200, 1200)
    height = random.randint(200, 800)

    page.mouse.move(width, height, steps=random.randint(5, 20))


def human_scroll(page):

    scroll_times = random.randint(2, 5)

    for _ in range(scroll_times):

        distance = random.randint(300, 900)

        page.mouse.wheel(0, distance)

        time.sleep(random.uniform(0.3, 1.0))


def reading_pause():

    if random.random() < 0.3:
        time.sleep(random.uniform(3, 6))


# ─────────────────────────────
# Nuxt資料解析
# ─────────────────────────────

def get_meta(data_list):

    meta_dict = None

    for v in data_list:
        if isinstance(v, dict) and "buyHouseListDatas" in v:
            meta_dict = v
            break

    if not meta_dict:
        return 1, []

    cnts_ptr = meta_dict.get("cnts")

    total_count = data_list[cnts_ptr] if isinstance(cnts_ptr, int) else 0

    total_pages = math.ceil(total_count / PER_PAGE)

    list_ptr = meta_dict.get("buyHouseListDatas")

    item_indices = data_list[list_ptr] if isinstance(list_ptr, int) else []

    return total_pages, item_indices


def resolve_item(data_list, item_idx):

    raw = data_list[item_idx] if item_idx < len(data_list) else None

    if not isinstance(raw, dict):
        return {}

    result = {}

    for k, v in raw.items():

        if isinstance(v, int) and v < len(data_list):

            pointed = data_list[v]

            if isinstance(pointed, (str, dict, list)):
                result[k] = pointed
            else:
                result[k] = v
        else:
            result[k] = v

    return result


def format_item(item):

    f = str(item.get("floor", ""))
    ft = str(item.get("floorTotal", ""))

    return {

        "物件編號": item.get("sn", ""),
        "物件名稱": item.get("objName", ""),
        "地址": item.get("doorplate", ""),
        "格局": item.get("special", ""),
        "坪數": f"{item.get('mainArea','')}坪",
        "樓層": f"{f}/{ft}樓" if f and ft else f,
        "屋齡": f"{item.get('age','')}年",
        "類型": item.get("type", ""),
        "價格": f"{item.get('price','')}萬",
    }


# ─────────────────────────────
# CSV存檔
# ─────────────────────────────

def save_csv(district, data):

    if not data:
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    path = f"{OUTPUT_DIR}/{district}.csv"

    with open(path, "w", newline="", encoding="utf-8-sig") as f:

        writer = csv.DictWriter(f, fieldnames=data[0].keys())

        writer.writeheader()

        writer.writerows(data)

    print(f" {district} 完成，{len(data)}筆 → {path}")


# ─────────────────────────────
# 主爬蟲
# ─────────────────────────────

def scrape():

    print(" 爬蟲啟動")

    with sync_playwright() as p:

        browser = p.chromium.launch(headless=HEADLESS)

        for district, zip_code in DISTRICT_MAP.items():

            print(f"\n開始抓取 {district}")

            context = browser.new_context(

                user_agent=random.choice(USER_AGENTS),

                viewport={
                    "width": random.randint(1100, 1600),
                    "height": random.randint(700, 1000)
                },

                locale="zh-TW",
                timezone_id="Asia/Taipei"

            )

            page = context.new_page()

            stealth = Stealth()
            stealth.apply_stealth_sync(page)

            district_results = []
            seen = set()

            for p_num in range(1, MAX_PAGES + 1):

                url = f"https://www.hbhousing.com.tw/buyhouse/{CITY}/{zip_code}/{p_num}-page"

                try:

                    page.goto(url, wait_until="networkidle", timeout=60000)

                    human_sleep()

                    random_mouse_move(page)

                    human_scroll(page)

                    nuxt_el = page.locator("#__NUXT_DATA__")

                    if nuxt_el.count() == 0:
                        print(" 找不到資料")
                        break

                    data_list = json.loads(nuxt_el.inner_text())

                    total_p, item_indices = get_meta(data_list)

                    total_p = min(total_p, MAX_PAGES)

                    added = 0

                    for idx in item_indices:

                        item = resolve_item(data_list, idx)

                        data = format_item(item)

                        sn = data["物件編號"]

                        if sn and sn not in seen:

                            district_results.append(data)

                            seen.add(sn)

                            added += 1

                    print(f"📄 {district} 頁 {p_num}/{total_p} +{added} (總 {len(district_results)})")

                    reading_pause()

                    if p_num >= total_p:
                        break

                except Exception as e:

                    print("⚠️ 錯誤:", e)

                    time.sleep(random.uniform(3, 6))

            save_csv(district, district_results)

            context.close()

        browser.close()

    print("\n 全部完成")


if __name__ == "__main__":
    scrape()