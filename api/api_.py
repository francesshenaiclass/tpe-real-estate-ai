import requests
import csv
import time  

url = "https://www.hbhousing.com.tw/proxy/api/HB/BuyHouseRelated/GetHouseDataCount"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Content-Type": "application/json"
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

target_keys = ["objName", "price", "salePrice", "style", "parking", 
               "lon", "lat", "landArea", "mainArea", "affiliatedArea", "zipCode"]

for district_name, zip_code in zip_codes.items():  
    page = 1
    district_results = []  # ← 每個區獨立的list

    while True:
        payload = {
            "vrType": 0,
            "page": page,           
            "pageRows": 10,
            "sort": None,
            "cityNo": 3,
            "zipCode": [zip_code],  
            "style": [],
            "type": [],
            "priceStart": None,
            "priceFinish": None,
            "areaType": "P",
            "areaStart": None,
            "areaFinish": None,
            "ageStart": None,
            "ageFinish": None,
            "roomStart": None,
            "roomFinish": None,
            "bathStart": None,
            "bathFinish": None,
            "hallStart": None,
            "hallFinish": None,
            "floorStart": None,
            "floorFinish": None,
            "location": None,
            "keyWord": None,
            "tag": [],
            "searchTopics": None,
            "theme": [],
            "storeID": None,
            "employeeID": None,
            "upriceStart": None,
            "upriceFinish": None,
            "schoolId": None,
            "partnerNo": None,
            "other": None,
            "parkingMethod": None
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()

        items = data["data"]["buyHouseListDatas"]
        if not items:
            print(f"{district_name} 第{page}頁無資料，結束")
            break

        for item in items:
            extracted = {key: item.get(key) for key in target_keys}
            district_results.append(extracted)  # ← 存進區獨立的list

        print(f"{district_name} 第{page}頁 抓取 {len(items)} 筆")
        page += 1
        time.sleep(3)

    filename = f"{district_name}.csv"
    with open(filename, "w", newline="", encoding="utf-8-sig") as f: 
        writer = csv.DictWriter(f, fieldnames=target_keys)
        writer.writeheader()
        writer.writerows(district_results)  

    print(f"✅ {district_name} 共 {len(district_results)} 筆，已儲存為 {filename}")