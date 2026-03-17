import requests
import csv
import time

url = "https://www.hbhousing.com.tw/proxy/api/HB/RealPriceRelated/GetSearchRPListDatas"

headers = {
    "User-Agent": "Mozilla/5.0",
    "Content-Type": "application/json",
    "Referer": "https://www.hbhousing.com.tw/",
    "Origin": "https://www.hbhousing.com.tw"
}

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

target_keys = ["address", "price", "uprice", "style", "parking",
               "room", "bath", "hall", "floor", "landArea", "mainArea", "affiliatedArea","dealYearMonth"]

for district, zip_code in zip_codes.items():
    page = 1
    results = []

    while True:
        payload = {
            "zipCode": zip_code,
            "style": ["1","2","3","4"],
            "ageStart": None,
            "ageFinish": None,
            "source": 1,
            "distance": 1000,
            "dealtime": 2,
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

        r = requests.post(url, headers=headers, json=payload)
        data = r.json()
        items = data.get("data", [])

        if not items:
            print(f"{district} 第{page}頁無資料，結束")
            break

        results.extend(items)
        print(f"{district} 第{page}頁抓到 {len(items)} 筆")
        page += 1
        time.sleep(1)

    if results:
        keys = results[0].keys()
        filename = f"{district}_realprice.csv"
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"✅ {district} 共 {len(results)} 筆")
    else:
        print(f"⚠️ {district} 沒資料")