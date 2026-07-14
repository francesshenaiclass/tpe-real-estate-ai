import requests
import csv
import time

# 住商不動產 API URL
url = "https://www.hbhousing.com.tw/proxy/api/HB/RealPriceRelated/GetSearchRPListDatas"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    "Referer": "https://www.hbhousing.com.tw/deal-search/",
    "Origin": "https://www.hbhousing.com.tw"
}

# 區域與代碼
zip_codes = {
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

# 根據截圖定義：原始 Key 對應 中文欄位名
# 這裡包含拆解後的 房、廳、衛
field_map = {
    "dealYearMonth": "成交年月",
    "style": "型式",
    "doorplate": "地址",
    "dealMoney": "成交總價(萬)",
    "uprice": "單價(萬/坪)",
    "area": "建物坪數",
    "landArea": "土地坪數",
    "age": "屋齡",
    "floor": "樓層",
    "totalFloor": "總樓層",
    "parkingSpace": "車位",
    "room": "房",
    "hall": "廳",
    "bath": "衛",
    "lat": "lat",  # 補上這行
    "lon": "lon",  # 補上這行
    "remark": "備註"
}

for district, zip_code in zip_codes.items():
    page = 1
    final_results = []
    print(f"🚀 開始爬取：{district}...")

    while True:
        payload = {
            "zipCode": zip_code,
            "style": ["1","2","3","4"],  
            "ageStart": None,
            "ageFinish": None,
            "source": 1,
            "distance": 1000,
            "dealtime": 2,  # 1年內
            "page": page,
            "pageRows": 10,
            "sort": None,
            "address": "",
            "priceStart": None,
            "priceFinish": None,
            "roomStart": None,
            "roomFinish": None,
            "upriceStart": None,
            "upriceFinish": None,
            "parking": None,
            "areaStart": None,
            "areaFinish": None,
            "exclude": None
        }

        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code != 200:
                break
            
            data = r.json()
            items = data.get("data", [])

            if not items:
                print(f"   第 {page} 頁無資料，該區抓取完畢。")
                break

            for item in items:
                # --- 核心邏輯：拆解格局 pattern (例如 "4/2/2") ---
                pattern = item.get("pattern", "")
                parts = pattern.split("/") if pattern else []
                
                # 建立一筆乾淨的資料
                row = {}
                for raw_key, chi_name in field_map.items():
                    if raw_key == "room":
                        row[chi_name] = parts[0] if len(parts) > 0 else "0"
                    elif raw_key == "hall":
                        row[chi_name] = parts[1] if len(parts) > 1 else "0"
                    elif raw_key == "bath":
                        row[chi_name] = parts[2] if len(parts) > 2 else "0"
                    else:
                        row[chi_name] = item.get(raw_key, "")
                
                final_results.append(row)

            print(f"   第 {page} 頁抓到 {len(items)} 筆")
            page += 1
            time.sleep(1.2) # 禮貌性延遲

        except Exception as e:
            print(f"   ❌ 發生錯誤: {e}")
            break

    # 儲存該區資料
    if final_results:
        filename = f"{district}_實價登錄.csv"
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=field_map.values())
            writer.writeheader()
            writer.writerows(final_results)
        print(f"✅ {district} 儲存成功！共 {len(final_results)} 筆\n")

print("✨ 全部任務完成！")