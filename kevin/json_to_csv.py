import json
import os
from csv_writer import write_header_csv
from csv_writer import write_info_csv

# 建立資料夾存放csv
if not os.path.exists("house_csv"):
    os.makedirs("house_csv")

# 輸入各縣市資料
with open("cities.json", "r", encoding="utf-8") as f:
    cities = json.load(f)

title = ['路段', '緯度', '經度', '屋齡', '建坪','房屋總價(萬)', '車位', '格局','有加蓋', '總樓層', '樓層', '房屋類型']

for city in cities.keys():# 取出每一個縣市
    for district, zipcode in cities[city].items():# 取出每個縣市的行政區及郵遞區號

        file_path = f"house_csv/{district}.csv"
        write_header_csv(file_path, title)# 建立該行政區的csv並寫入標題

        with open(f"./taipei_json/{district}.json", "r", encoding="utf-8")as f:
            data = json.load(f)
        content_rows = []

        totalCnt = data["content"]["totalCnt"]# 資料筆數

        for i in range(totalCnt):

            # 定義要保留的房屋類型代碼
            valid_types = {"A", "L", "M", "C", "D"}
            houselandtype = data["content"]["object"][i]["houselandtype"]
            if len(houselandtype)>1:
                continue
            else:
                type = set(houselandtype)
                if type & valid_types:
                    pass
                else:
                    continue

            address= data["content"]["object"][i]["address"]#路段
            latitude= data["content"]["object"][i]["latitude"]#緯度
            longitude= data["content"]["object"][i]["longitude"]#經度
            age= data["content"]["object"][i]["age"]#屋齡  
            areaBuilding= data["content"]["object"][i]["areaBuilding"]#建坪
            totalPrice= data["content"]["object"][i]["totalPrice"]#房屋總價(萬)

            parking=0
            try:
                if data["content"]["object"][i]["isParking"]==True:
                    parking = len(data["content"]["object"][i]["parking"])#車位
                
            except Exception as e:
                parking=0
                print(f"解析車位數量異常: {e}")

            totalLayout = data["content"]["object"][i]["totalLayout"]#格局

            addLayout = data["content"]["object"][i]["addLayout"] # 加蓋 
            if addLayout:
                addLayout=1
            else:
                addLayout=0

            totalfloor = data["content"]["object"][i]["totalfloor"] #總樓層

            floor = data["content"]["object"][i]["floor"] #樓層

            content_rows.append([address, latitude, longitude, age, areaBuilding,totalPrice, parking, totalLayout,addLayout, totalfloor, floor, houselandtype])
        write_info_csv(file_path, content_rows)# 資料加入csv檔案   


